from pydantic import BaseModel,Field
from starlette import status
from fastapi import APIRouter, Depends, Path, HTTPException
from sqlalchemy.orm import Session
from typing import Annotated
from models import Base, Todo
from database import engine, SessionLocal
from routers.auth import router as auth_router

router = APIRouter(prefix="/todo",
                   tags=["Todo"])




class ToDoRequest(BaseModel):
    title: str = Field( min_length=3, max_length=50)
    description: str = Field( min_length=3, max_length=255)
    complete: bool
    priority: int = Field( gt=0, lt=6)

# Veritabanı bağlantısını yöneten fonksiyon
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Bağımlılık tanımlaması
db_dependency = Annotated[Session, Depends(get_db)]

# Tüm Todo'ları getir
@router.get("/read_all")
async def read_all(db : db_dependency):
    return db.query(Todo).all()

# Belirli bir Todo'yu ID'ye göre getir
@router.get("/get_by_id/{todo_id}",status_code=status.HTTP_200_OK)
async def read_by_id(db: db_dependency, todo_id: int = Path(gt=0)):
    todo = db.query(Todo).filter(Todo.id == todo_id).first()
    if todo is not None:
        return todo
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ID not found")

@router.post("/create",status_code=status.HTTP_201_CREATED)
async def create_todo(db : db_dependency, todo_request : ToDoRequest):
    todo = Todo(**todo_request.dict())
    db.add(todo)
    db.commit()

@router.put("/update_todo/{todo_id}",status_code=status.HTTP_204_NO_CONTENT)
async def update_todo(db: db_dependency,todo_request: ToDoRequest,todo_id : int = Path(gt=0),):
    todo  = db.query(Todo).filter(Todo.id == todo_id).first()
    if todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")
    todo.title = todo_request.title
    todo.complete = todo_request.complete
    todo.description = todo_request.description
    todo.priority = todo_request.priority

    db.add(todo)
    db.commit()

@router.delete("/delete_todo/{todo_id}",status_code=status.HTTP_204_NO_CONTENT)
async def update_todo(db: db_dependency,todo_request: ToDoRequest,todo_id : int = Path(gt=0),):
    todo  = db.query(Todo).filter(Todo.id == todo_id).first()
    if todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")


    db.delete(todo)
    db.commit()

