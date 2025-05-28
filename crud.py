from fastapi import HTTPException,status,Depends
from sqlalchemy.orm import Session
from models import User, Roles, FileMetadataModel, DPPermissionModel, FileConversionEntryModel, FileConversionEntryModel,ConversionQueueEntryModel
from schemas import UserCreate, FileMetadatacreate, FileMetadataUploadresponse,FileMetadataRetrivalresponse, DPPermissionCreateResponse
from security import get_password_hash, generate_unique_id, create_conversion_id
from datetime import datetime
import os


def create_user(db: Session, user: UserCreate):
	existing_user =db.query(User).filter((User.username == user.username )).first()
	if existing_user:
		raise HTTPException(status_code=400,detail="username already exists")
	if user.role not in Roles.__members__:
		user.role="patient"
	hashed_password=get_password_hash(user.password)
	db_user=User(
		username=user.username,
		email=user.email,
		hashed_password=hashed_password,
		role= user.role,
		id= generate_unique_id(user.role)
	)

	db.add(db_user)
	db.commit()
	db.refresh(db_user)
	return db_user
def get_user_by_email(db: Session, email: str):
	return db.query(User).filter(User.email == email).first()
def get_user_by_username(db: Session, username: str):
	return db.query(User).filter(User.username == username).first()


def upload_patient_filemetadata(db: Session, filemetadata: FileMetadatacreate, file_id: str):
	try:
		patient_file_metadata=FileMetadataModel(
			file_id=file_id,
			patient_id=filemetadata.patient_id,
			original_format=filemetadata.original_format,
			original_path=filemetadata.original_path,
			storage_location=filemetadata.storage_location,
			status=filemetadata.status,
			source_file_id=None
		)
		
		db.add(patient_file_metadata)
		db.commit()
		db.refresh(patient_file_metadata)
	
		return FileMetadataUploadresponse(**patient_file_metadata.__dict__,message="upload successful")

	except Exception as e:
		db.rollback()
		raise HTTPException(status_code=500,detail=str(e))

def give_dp_permissions(db: Session,doctor_id,patient_id):
	try: 	
		dp_permissions_entry=DPPermissionModel(
			doctor_id =doctor_id,
			patient_id =patient_id,
			granted_at =datetime.utcnow()
		)
		db.add(dp_permissions_entry)
		db.commit()
		response = DPPermissionCreateResponse(
			doctor_id=dp_permissions_entry.doctor_id,
			patient_id=dp_permissions_entry.patient_id,
			granted_at=dp_permissions_entry.granted_at.isoformat(),  # Convert to ISO string
			message="Permission granted"
		)
		return response

	except Exception as e:
		db.rollback()
		raise HTTPException(status_code=500,detail=str(e))


def check_dp_permissions(db : Session,doctor_id,patient_id):
	has_permission =db.query(DPPermissionModel).filter_by(
		doctor_id=doctor_id,
		patient_id=patient_id
	).first()

	if not has_permission:
		raise HTTPException(status_code=403,detail="Access Denied : Patient permission required")
	print("access authorised")
	return True
	
def get_permitted_users(db : Session, patient_id):
	has_permission =db.query(DPPermissionModel).filter_by(patient_id=patient_id).all()
	return [permission.doctor_id for permission in has_permission]

def get_doctor_accessable_filemetadata(db: Session,doctor_id):
	patients=db.query(DPPermissionModel).filter(DPPermissionModel.doctor_id==doctor_id).all()
	patients_id=[p.patient_id for p in patients]
	patient_files_metadata=db.query(FileMetadataModel).filter(FileMetadataModel.patient_id.in_(patients_id)).all()
	print(patient_files_metadata)
	if not patient_files_metadata:
		raise HTTPException(status_code=404,detail="file not found.")
	return FileMetadataRetrivalresponse(data=[FileMetadataUploadresponse.from_orm(file) for file in patient_files_metadata],message="Retrived successful")

def get_file_metadata_by_file_id(db: Session,current_user: User,file_id):
	patient_files_metadata=db.query(FileMetadataModel).filter(FileMetadataModel.file_id==file_id).all()
	if not patient_files_metadata:
		raise HTTPException(status_code=404,detail="file not found.")
	if current_user.role=="Doctor" and check_dp_permissions(db,current_user.id,patient_file_metadata.patient_id):
		return FileMetadataRetrivalresponse(data=[FileMetadataUploadresponse.from_orm(file) for file in patient_files_metadata],message="Retrived successful")
	 
def get_file_metadata_by_patient_id(db: Session,current_user: User,patient_id):
	#print("checking permissions")
	if current_user.id==patient_id or check_dp_permissions(db,current_user.id,patient_id):
		patient_files_metadata=db.query(FileMetadataModel).filter(FileMetadataModel.patient_id==patient_id).all()
		#print(patient_files_metadata)

		if not patient_files_metadata:
			raise HTTPException(status_code=404,detail="file not found.")
		return FileMetadataRetrivalresponse(data=[FileMetadataUploadresponse.from_orm(file) for file in patient_files_metadata],message="Retrived successful")

def save_to_file_conversions(db: Session, file_id , requested_format):
	try:
		conversion_id=create_conversion_id()
		db_entry=FileConversionEntryModel(
			conversion_id=conversion_id,
			file_id=file_id,
			target_format=requested_format,
			conversion_status="pending",
			start_time= datetime.utcnow()
		)
		db.add(db_entry)
		db.commit()
		db.refresh(db_entry)
		return conversion_id
	except Exception as e:
		db.rollback()
		raise HTTPException(status_code=500,detail=str(e))
	
def update_file_conversions(db: Session,conversion_id,converted_path):
	try:
		entry=db.query(FileConversionEntryModel).filter_by(conversion_id=conversion_id).first()
		if entry:
			entry.converted_path= converted_path
			entry.conversion_status= "completed"
			entry.end_time= datetime.utcnow()
			entry.error_log= None
			db.commit()
			db.refresh(entry)
		else:	
			raise HTTPException(status_code=404,detail="conversion not found")
	except Exception as e:
		db.rollback()
		raise HTTPException(status_code=500,detail=str(e))
	

def queue_for_conversion(db: Session, conversion_id, original_path, worker_node):
	pass
		
