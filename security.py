from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime,timedelta
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext
from database import get_db
from models import Roles, User
from starlette.status import WS_1008_POLICY_VIOLATION
import uuid

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
pwd_context = CryptContext(schemes=["bcrypt"],deprecated="auto")
credentials_exception = HTTPException(
	status_code=status.HTTP_401_UNAUTHORIZED,
	detail="Could not validate credentials",
	headers={"WWW-Authenticate": "Bearer"},
)
secret_key = "healthcare_api_auth"
Algorithm = "HS256"
access_token_expire_minutes = 30

role_prefix={
	Roles.admin.value : "ADM",
	Roles.doctor.value : "DOC",
	Roles.patient.value : "PAT"
}

def generate_unique_id(role: str):
	if role not in role_prefix:
		role="patient"
	return f"{role_prefix[role]}-{uuid.uuid4()}"

def give_upload_access(user: User):
	if user.role==Roles.admin:
		return True
	else:
		raise HTTPException(status_code=403, detail="Access Denied. user role not enough")

def get_password_hash(password :str):
	return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
	return pwd_context.verify(plain_password,hashed_password)

def create_access_token(data: dict, expires_delta: timedelta =None):
	to_encode =data.copy()
	if expires_delta:
		expire = datetime.utcnow() +expires_delta
	else:
		expire = datetime.utcnow() + timedelta(minutes=access_token_expire_minutes)
	to_encode.update({"exp": expire})
	encoded_jwt=jwt.encode(to_encode,secret_key,algorithm=Algorithm)
	return encoded_jwt

def get_current_user(token: str =Depends(oauth2_scheme),db: Session = Depends(get_db)) -> User:
	from crud import get_user_by_email
	#print("DEBUG: Inside get_current_user")
	#print(f"DEBUG: Received token: {token}")
	try:	
		payload=jwt.decode(token,secret_key,algorithms=[Algorithm])
		#print(f"DEBUG: Decoded JWT payload: {payload}")
		email: str =payload.get("sub")
		if email is None:
			#print("DEBUG: Email not found in token payload")
			raise credentials_exception
		user = get_user_by_email(db,email)
		if user is None:
			#print("DEBUG: User not found in database")
			raise credentials_exception
		#print(f"DEBUG: Authenticated user: {user.email}")
		return user
	except JWTError as e:
		if "Signature has expired" in str(e):
        		raise HTTPException(status_code=401, detail="Token has expired. Please log in again.")
		raise credentials_exception

def websocket_get_current_user(websocket,token: str):
	from crud import get_user_by_email
	if not token:
		return websocket.close(code=WS_1008_POLICY_VIOLATION)
	try:
		
		payload=jwt.decode(token,secret_key,algorithms=[Algorithm])
		print(f"DEBUG: Decoded JWT payload: {payload}")
		email: str =payload.get("sub")
		if email is None:
			print("DEBUG: Email not found in token payload")
			raise ValueError("invalid token")
		db_gen = get_db()
		db: Session = next(db_gen)
		user = get_user_by_email(db,email)
		db.close()
		if user is None:
			print("DEBUG: User not found in database")
			raise ValueError("user not found")
		print(f"DEBUG: Authenticated user: {user.email}")
		return user
	except (JWTError, ValueError) as e:
		return websocket.close(code=WS_1008_POLICY_VIOLATION)

def valid_file_id(id: str) -> bool:
	try:
		uuid.UUID(id.strip())
		return True
	except ValueError:
		raise HTTPException(status_code=400, detail="Invalid file ID")
	
def valid_patient_id(id: str) -> bool:
	try:	
		if id[:3] not in role_prefix.values():
			raise HTTPException(status_code=400, detail="Invalid patient ID")
		uuid.UUID(id[4:].strip())
		return True
	except ValueError:
		raise HTTPException(status_code=400, detail="Invalid patient ID")

def create_conversion_id():
	conversion_id=uuid.uuid4()
	return conversion_id
		