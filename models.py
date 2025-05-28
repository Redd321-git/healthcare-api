from sqlalchemy import Column, Integer, String, Enum, Text, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from database import Base
import enum,uuid

class Roles(enum.Enum):
	admin ="admin"
	doctor ="doctor"
	patient ="patient"

class User(Base):
	__tablename__ = "users"
    
	id = Column(Text, primary_key=True, index=True)
	username = Column(String, unique=True, index=True,nullable=False)
	email = Column(String, unique=True, index=True, nullable=False)
	hashed_password = Column(String, nullable=False)
	role= Column(Enum(Roles),default=Roles.patient)

class FileMetadataModel(Base):
	__tablename__ = "files"
	
	file_id= Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	patient_id= Column(String, nullable=False)
	original_format= Column(Text, nullable=False)
	original_path= Column(Text, nullable=False)
	storage_location= Column(Text, nullable=False,default="local")
	upload_date= Column(TIMESTAMP, server_default=func.now())
	status= Column(Text, nullable=False, default="original")
	source_file_id = Column(UUID(as_uuid=True), nullable=False)

class DPPermissionModel(Base):
	__tablename__ = "dp_permissions"
	
	doctor_id=Column(Text,ForeignKey("users.id"),primary_key=True)
	patient_id=Column(Text,ForeignKey("users.id"),primary_key=True)
	granted_at=Column(TIMESTAMP,server_default=func.now())
	
class FileConversionEntryModel(Base):
	__tablename__ = "file_conversions"
	
	conversion_id= Column(UUID(as_uuid=True), primary_key=True, nullable=False)
	file_id= Column(UUID(as_uuid=True), ForeignKey("files.file_id"), nullable=False)
	target_format= Column(Text, nullable=False)
	converted_path= Column(Text)
	conversion_status=Column(Text, default='Pending')
	start_time= Column(TIMESTAMP,server_default=func.now())
	end_time= Column(TIMESTAMP)
	error_log= Column(Text)

class ConversionQueueEntryModel(Base):
	__tablename__ = "conversion_queue"

	queue_id= Column(UUID(as_uuid=True), nullable=False, primary_key=True)
	conversion_id= Column(UUID(as_uuid=True), ForeignKey("file_conversions.conversion_id"), nullable=False)
	worker_node= Column(Text)
	status= Column(Text, default='pending')
	created_at= Column(TIMESTAMP, server_default=func.now())
	updated_at= Column(TIMESTAMP)
	original_path= Column(Text)













