from fastapi.responses import FileResponse
from fastapi import HTTPException
from handlers import S3FileStorage, LocalFileStorage, File_meta_RetrivalbyfileId, File_meta_RetrivalbyPatientId, File_meta_RetriveAllAccessable, FileRetrivelocal_view, FileRetrivelocal_download, FileRetriveS3, LightweightConverter, HeavyweightConverter

class userfactory:
	@staticmethod
	def create_user(role: str,email: str,password:str):
		if role=="admin":
			return User(email=email, hashed_password=password, role=Roles.admin)
		elif role=="doctor":
			return User(email=email, hashed_password=password, role=Roles.doctor)
		else:
			return User(email=email, hashed_password=password, role=Roles.patient)


class FileStoragefactory:
	@staticmethod
	def create_storage(storage_type: str, **kwargs):
		if storage_type =="s3":
			return S3FileStorage(bucket_name=kwargs["bucket_name"],region=kwargs["region"])
		elif storage_type == "local":
			return LocalFileStorage(upload_dir=kwargs["upload_dir"])
		else:
			raise ValueError(f"Invalid storage type: {storage_type}")


class File_meta_RetrivalFactory:
	@staticmethod
	def get_strategy(method: str):
		if method == "by_file_id":
			return File_meta_RetrivalbyfileId()
		elif method == "by_patient_id":
			print("strategy allocated")
			return File_meta_RetrivalbyPatientId()
		elif method == "all":
			return File_meta_RetriveAllAccessable()
		else:
			raise ValueError(f"unknown file retrival method: {method}")

class FileRetrivalFactory:
	@staticmethod
	def get_strategy(storage_location: str,option: str):
		if storage_location == "local" and option == "view":
			return FileRetrivelocal_view()
		if storage_location == "local" and option == "download":
			return FileRetrivelocal_download()
		elif storage_location == "s3":
			return FileRetriveS3()
		else:
			raise ValueError(f"unknown file retrival location: {location}")


class ConverterFactory:
	ltw_pairs={
			".csv": [".pdf", ".xlsx"],
			".docx": [".html", ".pdf", ".txt"],
			".html": [".pdf"],
			".json": [".pdf", ".xml"],
			".pdf": [".docx", ".txt"],
			".txt": [".docx", ".html", ".pdf"],
			".xlsx": [".csv"],
			".xml": [".json"],
			".png": [".pdf"]
	}
	@staticmethod
	def get_converter(original_format: str,requested_format: str):
		original_format=original_format.lower()
		requested_format=requested_format.lower()
		if requested_format in ConverterFactory.ltw_pairs.get(original_format, []):
			return LightweightConverter()
		return HeavyweightConverter()

		