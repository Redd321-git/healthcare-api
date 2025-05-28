from fastapi import FastAPI, Depends, HTTPException, status, Form, File, UploadFile, Security, Body, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import timedelta
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from database import SessionLocal, get_db										
from schemas import UserCreate, UserResponse, LoginForm, FileMetadatacreate, FileMetadataUploadresponse, FileMetadataRetrivalresponse		
from crud import create_user, get_user_by_email,get_user_by_username, upload_patient_filemetadata, save_to_file_conversions, update_file_conversions, queue_for_conversion, give_dp_permissions
from factory import FileStoragefactory, File_meta_RetrivalFactory, FileRetrivalFactory, ConverterFactory						
from models import User	,Roles
from pubsub import create_user_stream, publish, consume, should_stop									
from security import verify_password, access_token_expire_minutes, create_access_token, get_current_user, valid_file_id, valid_patient_id, give_upload_access , websocket_get_current_user

import uuid, os, re, queue, asyncio
from typing import List

storage_config={
	"upload_dir":r"C:\Users\rites\healthcare-api\healthcare-api\healthcare_file_storage",
	#"upload_bucket":""
}

templates = Jinja2Templates(directory="templates")


app =FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],  # Allows all origins
	allow_credentials=True,
	allow_methods=["*"],  # Allows all methods
	allow_headers=["*"],  # Allows all headers
)

@app.post("/register",response_model=UserResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)):
	existing_user =get_user_by_email(db,user.email)
	if existing_user:
		raise HTTPException(status_code=400,detail="Email already registered")
	user=create_user(db, user)
	create_user_stream(user.id)
	return user

@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session= Depends(get_db)):
	user=get_user_by_username(db,form_data.username)
	
	if not user or not verify_password(form_data.password, user.hashed_password):
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
	
	access_token = create_access_token(
		data={"sub":user.email}, expires_delta=timedelta(minutes=access_token_expire_minutes)
	)
	return {"access_token": access_token, "token_type": "bearer","message":"login successfull"}

@app.get("/me",response_model=UserResponse)
async def read_me(current_user= Depends(get_current_user)):
	return current_user

@app.post("/upload-file/",response_model=FileMetadataUploadresponse)
async def upload_file(patient_id: str = Form(...), file: UploadFile = File(...),storage_type: str = Form("local"),db : Session = Depends(get_db),current_user: User = Depends(get_current_user)):
	try: 	
		print(file)
		if give_upload_access(current_user):
			print("access permited")
			pass
		if valid_patient_id(patient_id):
			print("patient_id valid")
			pass

		file_id=str(uuid.uuid4())
		file_extension=os.path.splitext(file.filename)[1]
		print(file_extension)
		storage=FileStoragefactory.create_storage(storage_type,**storage_config)
		file_path=storage.upload(file,file_id,file_extension)
		print(file_path)
		db_entry=FileMetadatacreate(
			patient_id=patient_id,
			original_format=file_extension,
			original_path=file_path,
			storage_location=storage_type,
			status="pending"
		)
		publish(patient_id,file_id=file_id,event="new file uploaded",db=db)
		return upload_patient_filemetadata(db,db_entry,file_id)
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))

@app.post("/file/",response_model=FileMetadataRetrivalresponse)
async def get_file_metadata(file_id: str = None, patient_id: str = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	try:
		if file_id is not None:
			strategy=File_meta_RetrivalFactory.get_strategy("by_file_id")
			if valid_file_id(file_id):
				metadata=strategy.retrieve(db, current_user, file_id=file_id)
		elif patient_id is not None:
			#print("trying with patient id")
			strategy=File_meta_RetrivalFactory.get_strategy("by_patient_id")
			#print(strategy)
			if valid_patient_id(patient_id):
				#print("patient_id is valid")
				metadata=strategy.retrieve(db, current_user, patient_id=patient_id)
		else:
			strategy=File_meta_RetrivalFactory.get_strategy("all")
			metadata=strategy.retrieve(db, current_user)
		if metadata is None:
			return FileMetadataRetrivalresponse(message="File metadata retrieved successfully.",data=[])
		return metadata

	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))

@app.post("/file/view/")
async def view_file(metadata: FileMetadataRetrivalresponse = Body(...), current_user: User = Security(get_current_user)):
	from fastapi import HTTPException
	data=metadata.data[0]
	try:	
		print("trying to retrive strategy")
		strategy=FileRetrivalFactory.get_strategy(data.storage_location,"view")
		print(strategy)
		return strategy.retrive(file_path=data.original_path, file_type=data.original_format,current_user= current_user)	
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))	

@app.post("/file/download/")
async def download_file( metadata: FileMetadataRetrivalresponse = Body(...), current_user: User = Security(get_current_user)):
	data=metadata.data[0]
	try:	
		print("trying to retrive strategy")
		strategy=FileRetrivalFactory.get_strategy(data.storage_location,"download")
		print(strategy)
		return strategy.retrive(file_path=data.original_path, file_type=data.original_format, current_user= current_user)	
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))	

@app.post("/convert/")
async def convert_file_format(requested_format: str,metadata: FileMetadataRetrivalresponse = Body(...), db: Session = Depends(get_db)):
	data=metadata.data[0]
	try:		
		conversion_id=save_to_file_conversions(db, data.file_id, requested_format)
		print(data.original_format)
		print(requested_format)
		converter=ConverterFactory.get_converter(data.original_format, requested_format)
		print(converter)
		outcome, converted_path = converter.convert(data, requested_format, upload_dir=storage_config["upload_dir"])
		print(converted_path)
		if outcome["status"]=="completed":
			update_file_conversions(db, conversion_id=conversion_id,converted_path=converted_path)
			publish(patient_id=data.patient_id,file_id=str(data.file_id),event="file converted",db=db,file_format=data.original_format,target_format=requested_format)
			return {"message":"conversion completed","path": converted_path}
		else:
			#queue_for_conversion(db, conversion_id=conversion_id, original_path=data.original_path, worker_node=worker)
			return {"message":"queued for conversion"}
	except Exception as e:
		raise HTTPException(status_code=500,detail=str(e))

@app.post("/give_permission/")
async def give_patient_file_access( doctor_id :str, current_user: User = Security(get_current_user), db: Session = Depends(get_db)):
	try:
		if current_user.role == Roles.patient:
			return give_dp_permissions(db,doctor_id=doctor_id,patient_id=current_user.id)
		else:
			raise HTTPException(status_code=403, detail="Only patients can grant access to doctors.")
	except Exception as e:
		raise HTTPException(status_code=500,detail=str(e))
	 

@app.get("/notifications/")
async def get_notifications(current_user: User = Security(get_current_user)):
	try:
		consume(current_user.id)
	except Exception as e:
		raise HTTPException(status_code=500,detail=str(e))


@app.websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket):
	await websocket.accept()
	token=websocket.query_params.get("token")
	current_user=websocket_get_current_user(websocket,token)
	consume_task = asyncio.create_task(consume(current_user.id, websocket))	
	try :
		await consume_task
	except WebSocketDisconnect:
		should_stop.set()
		consume_task.cancel()
	except Exception as e:
		print("error : ", e)
		consume_task.cancel()
	
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})



if __name__=="__main__" :
	import uvicorn
	
	uvicorn.run("main:app",host="127.0.0.1",port=8000,reload=True)