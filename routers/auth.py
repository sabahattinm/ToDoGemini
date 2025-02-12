from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel
from typing import Annotated
from database import SessionLocal
from models import User
from passlib.context import CryptContext
from sqlalchemy.orm import Session

router = APIRouter(prefix="/auth",
                   tags=["Authentication"])

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Bağımlılık tanımlaması
db_dependency = Annotated[Session, Depends(get_db)]


class CreateUserRequest(BaseModel):
    username: str
    email: str
    first_name: str
    last_name: str
    hashed_password : str
    role: str

@router.post("/auth")
async def create_user(db:db_dependency ,create_user_request: CreateUserRequest):
    user = User(
        username=create_user_request.username,
        email=create_user_request.email,
        first_name=create_user_request.first_name,
        last_name=create_user_request.last_name,
        hashed_password=bcrypt_context.hash(create_user_request.hashed_password),
        role=create_user_request.role
    )
    db.add(user)
    db.commit()