import redis.asyncio as redis
import asyncio
import json
from datetime import datetime
from fastapi import Depends, HTTPException
from abc import ABC, abstractmethod
from sqlalchemy.orm import Session
from database import get_db
from schemas import Notification
from crud import check_dp_permissions, give_dp_permissions, get_permitted_users

r= redis.Redis(host='localhost',port=6379,db=0,decode_responses=True)
should_stop=asyncio.Event()

class PubSubNotifications(ABC):
	@abstractmethod
	def notification(self, patient_id, **kwargs):
		pass

class ConversionNotification(PubSubNotifications):
	def notification(self,patient_id: str,file_id: str,file_format: str,target_format: str):
		notification=Notification(
			event="file converted",
			patient_id=patient_id,
			file_id=file_id,
			message=f"patient {patient_id} file has been converted from {file_format} to {target_format}",
			timestamp=datetime.utcnow().isoformat()
		)
		return notification.dict()

class UploadNotification(PubSubNotifications):
	def notification(self,patient_id: str,file_id: str):
		notification=Notification(
			event="new file uploaded",
			patient_id=patient_id,
			file_id=file_id,
			message=f"there is new file avalable on patient {patient_id}",
			timestamp=datetime.utcnow().isoformat()
		)
		return notification.dict()

class NotifcationSelector:
	@staticmethod
	def select(event: str):
		if event=="file converted":
			return ConversionNotification()
		elif event=="new file uploaded":
			return UploadNotification()
		else:
			raise ValueError(f"Event '{event}' not defined for creating a notification.")

def create_user_stream(user_id: str):
	stream_key=f"notification:user:{user_id}"
	r.xadd(stream_key,{"event":"stream intialised"})
	if r.exists(stream_key):
		print("Stream exists")
	else:
		print("Stream does not exist")

async def publish( patient_id: str, event: str, db: Session, **kwargs):
	try:
		user_ids=get_permitted_users(db, patient_id)
		notification_builder=NotifcationSelector.select(event=event)
		raw_notification=notification_builder.notification(patient_id, **kwargs)
		notification = {k: str(v) for k, v in raw_notification.items()}
		stream_key=f"notification:user:{patient_id}"
		await r.xadd(stream_key,notification)
		for user_id in user_ids:
			stream_key=f"notification:user:{user_id}"
			r.xadd(stream_key,notification)
			print(f"notification sent to {user_id}")
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))

async def consume(user_id: str, websocket):
	stream_key=f"notification:user:{user_id}"
	last_id_key = f"notification:user:{user_id}:last_id"

	last_id= await r.get(last_id_key)
	stream_len = await r.xlen(stream_key)
	if last_id is None:
		if stream_len > 0:
			last_id = '0-0'
		else:
			last_id = '$'	
	try:
		while not should_stop.is_set():
			messages = await r.xread({stream_key: last_id}, block=5000, count=10)
			for stream, events in messages:
				for message_id, data in events:
					await asyncio.sleep(1)
					#print(f"Message ID: {message_id}, Data: {data}")
					last_id = message_id
					await websocket.send_text(json.dumps(data))
					await r.set(last_id_key, last_id)
	except Exception as e:
		print("error: ",e)
		await websocket.close()
		