from pwdlib import PasswordHash
import jwt
from datetime import datetime, timedelta, timezone
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException
from database import get_db
from sqlalchemy.orm import Session
from sqlalchemy import select
from models import User
from dotenv import load_dotenv
import os

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()

pwd_context = PasswordHash.recommended()

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed: str):
    return pwd_context.verify(plain_password, hashed)

def create_access_token(user_id: int):
    expiry = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "exp": expiry
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token

def verify_token(token:str, db:Session):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))

        if not user_id:
            return None
        
        user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
        if not user:
            return None

        return user
    
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db:Session = Depends(get_db)):
    token = credentials.credentials
    user = verify_token(token, db)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")

    return user

def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

