from pydantic import BaseModel, EmailStr
from uuid import UUID
from typing import List, Optional
from datetime import datetime

class LoginForm(BaseModel):
	email: str
	password: str

class UserCreate(BaseModel):
	username: str
	email: EmailStr
	password: str
	role: str

class UserResponse(BaseModel):
	username: str
	email: EmailStr
	role: str
	id: str

	class Config:
		from_attributes = True

class FileMetadata(BaseModel):
	patient_id: str
	original_format: str
	storage_location: str
	original_path: str
	status: str
	
class Notification(BaseModel):
	event: str
	patient_id: str
	file_id: str
	message: str
	timestamp: datetime
	class Config:
		json_encoders = {
			datetime: lambda v: v.isoformat()
		}

class DPPermissionCreateResponse(BaseModel):
	doctor_id: str
	patient_id: str
	granted_at: str
	message: str

class FileMetadatacreate(FileMetadata):
	pass

class FileMetadataUploadresponse(FileMetadata):
	file_id: UUID
	source_file_id: Optional[UUID] = None
	message: Optional[str] = None

	class Config:
		from_attributes = True

class FileMetadataRetrivalresponse(BaseModel):
	message: str
	data: List[FileMetadataUploadresponse]
	class Config:
		from_attributes = True