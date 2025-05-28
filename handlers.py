from models import User, Roles
from fastapi.responses import FileResponse
from abc import ABC, abstractmethod
from sqlalchemy.orm import Session
from fastapi import HTTPException
from crud import get_file_metadata_by_patient_id, get_file_metadata_by_file_id, get_doctor_accessable_filemetadata, check_dp_permissions
from PIL import Image
import boto3
import os
import mimetypes
import fitz
import xmltodict
import json




class FileStorage(ABC):
	@abstractmethod
	def upload(self, file, file_id, file_extension):
		pass

class S3FileStorage(FileStorage):
	def __init__(self,upload_bucket:str):
		self.s3_client =boto3.client('s3', region_name="")
		self.upload_bucket = upload_bucket

	def upload(self, file, file_id, file_extension):
        	file_key = f"uploads/{file_id}{file_extension}"
        	self.s3_client.upload_fileobj(file.file, self.upload_bucket, file_key)
        	return f"s3://{self.upload_bucket}/{file_key}"

class LocalFileStorage(FileStorage):
	def __init__(self, upload_dir: str):
        	self.upload_dir = upload_dir

	def upload(self, file, file_id, file_extension):
        	file_path = os.path.join(self.upload_dir, f"{file_id}{file_extension}")
        	with open(file_path, 'wb') as f:
            		f.write(file.file.read())
        	return file_path





class File_meta_Retrival(ABC):
	@abstractmethod
	def retrieve(self,db: Session,user: User,**kwargs):
		pass


class File_meta_RetrivalbyfileId(File_meta_Retrival):
	def retrieve(self,db: Session,user: User,file_id: str): 
		return get_file_metadata_by_file_id(db,user,file_id=file_id)


class File_meta_RetrivalbyPatientId(File_meta_Retrival):
	def retrieve(self,db: Session,user: User,patient_id: str):
		if user.role== Roles.doctor:
			return get_file_metadata_by_patient_id(db,user,patient_id=patient_id)
		elif user.role == Roles.patient and patient_id==user_id:
			return get_file_metadata_by_patient_id(db,user,patient_id=patient_id)

class File_meta_RetriveAllAccessable(File_meta_Retrival):
	def retrieve(self,db: Session,user: User):
		if user.role == Roles.doctor:
			return get_doctor_accessable_filemetadata(db,user.id)
		elif user.role == Roles.patient:
			return get_file_metadata_by_patient_id(db,user,patient_id=user.id)	
		


class FileRetrive(ABC):
	@abstractmethod
	def retrive(self,file_path: str, file_type: str, current_user: User):
		pass
		
class FileRetrivelocal_download(FileRetrive):
	def retrive(self,file_path: str, file_type: str, current_user: User):
		print(file_path)
		if os.path.exists(file_path):
			if file_type.startswith("."):
				file_type = file_type.lower()
				mime_type, _ = mimetypes.guess_type(file_path)
			if mime_type is None:
				mime_type = "application/octet-stream"
			print(mime_type)
			print("path exists")
			return FileResponse(file_path, filename=os.path.basename(file_path), media_type=mime_type, headers={"Content-Disposition":"attachment"})
		else:
			raise HTTPException(status_code=400, detail="path does not exists")

class FileRetrivelocal_view(FileRetrive):
	def retrive(self, file_path: str, file_type: str, current_user: User):
		print(file_path)
		if os.path.exists(file_path):
			print("path exists")
			if file_type.startswith("."):
				file_type = file_type.lower()
				mime_type, _ = mimetypes.guess_type(file_path)
			if mime_type is None:
				mime_type = "application/octet-stream"
			print(mime_type)
			return FileResponse(file_path, filename=os.path.basename(file_path),media_type=mime_type, headers={"Content-Disposition":"inline"})
		else:
			raise HTTPException(status_code=400, detail="path does not exists")

class FileRetriveS3(FileRetrive):
	def retrive(self, file_path: str, file_type: str, current_user: User):
		pass


class HeavyweightConverter:
	def convert(self, data, requested_format: str, upload_dir: str):
		return {"status":"queued"},None

class LightweightConverter:
	def __init__(self):
		self.registry={
			(".pdf",".txt"): pdf_to_text(),
			(".xml",".json"): xml_to_json(),
			(".png",".pdf"): png_to_pdf() 
		}
	def convert(self,data: list, requested_format: str, upload_dir: str):
		handler=self.registry.get((data.original_format, requested_format))
		if not handler:	
			raise ValueError("no handler found")
		else:
			return handler.handle(data,upload_dir)

class format_handler(ABC):
	@abstractmethod
	def handle(self,data: list,upload_dir: str):
		pass

class pdf_to_text(format_handler):
	def __init__(self):
		self.file_extension=".txt"
	def handle(self,data: list, upload_dir: str):
		doc=fitz.open(data.original_path)
		file_path = os.path.join(upload_dir, f"{data.file_id}{self.file_extension}")
		with open(file_path,"w",encoding="utf-8") as f:
			for page in doc:
				f.write(page.get_text())
		doc.close()
		return {"status":"completed"},file_path

class xml_to_json(format_handler):
	def __init__(self):
		self.file_extension=".json"
	def handle(self,data: list, upload_dir: str):
		with open(data.original_path,"r",encoding="utf-8") as x:
			x_dict=xmltodict.parse(x.read())
		file_path = os.path.join(upload_dir, f"{data.file_id}{self.file_extension}")
		with open(file_path,"w",encoding="utf-8") as f:
			json.dump(x_dict,f,indent=4)
		return {"status":"completed"},file_path

class png_to_pdf(format_handler):
	def __init__(self):
		self.file_extension=".pdf"
	def handle(self,data: list, upload_dir: str):
		file_path = os.path.join(upload_dir, f"{data.file_id}{self.file_extension}")
		image = Image.open(data.original_path)
		if image.mode=="RGBA":
			image.convert("RGB")
		image.save(file_path,"PDF",resolution=100.0)
		print(file_path)
		return {"status":"completed"},file_path
