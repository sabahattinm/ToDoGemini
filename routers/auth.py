from fastapi import APIRouter,Depends,HTTPException,Request
from pydantic import BaseModel
from typing import Annotated
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from starlette import status
from database import SessionLocal
from models import User
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from jose import jwt,JWTError
from datetime import datetime,timedelta, timezone
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="/auth",
                   tags=["Authentication"])

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY  = "<KEY>"
ALGORITHM = "HS256"

templates = Jinja2Templates(directory="templates")

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
    phone_number: int


def create_access_token(username : str ,role : str,user_id : int ,expires_delta:timedelta):
    payload = {"sub": username,"role":role,"user_id":user_id}
    expire = datetime.now(timezone.utc) + expires_delta
    payload.update({"exp":expire})
    return jwt.encode(payload,SECRET_KEY,algorithm=ALGORITHM)

def authenticate_user(username:str,password:str,db):
    db = SessionLocal()
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return False
    if not bcrypt_context.verify(password,user.hashed_password):
        return False
    return user

async def get_current_user(token:str = Depends(OAuth2PasswordBearer(tokenUrl="/auth/token"))):
    try:
        payload = jwt.decode(token,SECRET_KEY,algorithms=[ALGORITHM])
        username = payload.get("sub")
        user_role = payload.get("role")
        user_id = payload.get("user_id")
        if username is None or user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Username or ID invalid")
        return {"username":username,"role":user_role,"user_id":user_id}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Token is invalid")

@router.get("/login-page",status_code=status.HTTP_200_OK)
def render_login_page(request:Request):
    return templates.TemplateResponse("login.html",{"request":request})

@router.get("/register-page",status_code=status.HTTP_200_OK)
def render_register_page(request:Request):
    return templates.TemplateResponse("register.html",{"request":request})


@router.post("/",status_code=status.HTTP_201_CREATED)
async def create_user(db:db_dependency ,create_user_request: CreateUserRequest):
    user = User(
        username=create_user_request.username,
        email=create_user_request.email,
        first_name=create_user_request.first_name,
        last_name=create_user_request.last_name,
        hashed_password=bcrypt_context.hash(create_user_request.hashed_password),
        role=create_user_request.role,
        phone_number=create_user_request.phone_number

    )
    db.add(user)
    db.commit()

@router.post("/token",status_code=status.HTTP_200_OK)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm,Depends()],db:db_dependency):
    user = authenticate_user(form_data.username,form_data.password,db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Incorrect username or password")
    token = create_access_token(user.username , user.id,user.role,timedelta(minutes=60))
    return {"access_token":token,"token_type":"bearer"}