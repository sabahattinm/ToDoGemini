from pydantic import BaseModel,Field
from starlette import status
from starlette.responses import RedirectResponse
from fastapi import APIRouter, Depends, Path, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Annotated
from models import Base, Todo
from database import engine, SessionLocal
from routers.auth import get_current_user
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
import os
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage
import markdown
from bs4 import BeautifulSoup
router = APIRouter(prefix="/todo",tags=["Todo"])

templates = Jinja2Templates(directory="templates")


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
user_dependency = Annotated[dict, Depends(get_current_user)]

#def redirect_to_login(request : Request):
  #  return request.app.url_path_for("auth.render_login_page")
def redirect_to_login(request : Request):
    redirect_response = RedirectResponse(url="/auth/login-page",status_code=status.HTTP_302_FOUND)
    redirect_response.delete_cookie("access_token")
    return redirect_response

@router.get("/todo-page")
async def render_todo_page(request : Request, db : db_dependency):
    try:
       user = await get_current_user(request.cookies.get("access_token"))
       if user is None:
           return redirect_to_login(request)
       todos = db.query(Todo).filter(Todo.owner_id == user.get("role")).all()
       return templates.TemplateResponse("todo.html",{"request": request,"todos":todos,"user":user})

    except:
        return redirect_to_login(request)

@router.get("/add-todo-page")
async def render_add_todo_page(request : Request):
    try:
       user = await get_current_user(request.cookies.get("access_token"))
       if user is None:
           return redirect_to_login(request)

       return templates.TemplateResponse("add-todo.html",{"request": request,"user":user})

    except:
        return redirect_to_login(request)

@router.get("/edit-todo-page/{todo_id}")
async def render_todo_page(request : Request,todo_id: int, db : db_dependency):
    try:
       user = await get_current_user(request.cookies.get("access_token"))
       if user is None:
           return redirect_to_login(request)
       todo = db.query(Todo).filter(Todo.id == todo_id).first()
       return templates.TemplateResponse("edit-todo.html",{"request": request,"todo":todo,"user":user})

    except:
        return redirect_to_login(request)

# Tüm Todo'ları getir
@router.get("/")
async def read_all(user : user_dependency,db : db_dependency):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return db.query(Todo).filter(Todo.owner_id == user.get("role")).all()

# Belirli bir Todo'yu ID'ye göre getir
@router.get("/todo/{todo_id}",status_code=status.HTTP_200_OK)
async def read_by_id(user :user_dependency,db: db_dependency, todo_id: int = Path(gt=0)):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    todo = db.query(Todo).filter(Todo.id == todo_id).filter(Todo.owner_id == user.get("role")).first()
    if todo is not None:
        return todo
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ID not found")

@router.post("/todo",status_code=status.HTTP_201_CREATED)
async def create_todo(user : user_dependency,db : db_dependency, todo_request : ToDoRequest):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    todo = Todo(**todo_request.dict(), owner_id=user.get('role'))  # 'user_id' ile erişim
    todo.description = create_todo_with_gemini(todo.description)
    db.add(todo)
    db.commit()

@router.put("/todo/{todo_id}",status_code=status.HTTP_204_NO_CONTENT)
async def update_todo(user : user_dependency, db: db_dependency,todo_request: ToDoRequest,todo_id : int = Path(gt=0),):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    todo  = db.query(Todo).filter(Todo.id == todo_id).filter(Todo.owner_id == user.get("role")).first()
    if todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")
    todo.title = todo_request.title
    todo.complete = todo_request.complete
    todo.description = todo_request.description
    todo.priority = todo_request.priority

    db.add(todo)
    db.commit()

@router.delete("/todo/{todo_id}",status_code=status.HTTP_204_NO_CONTENT)
async def update_todo(user: user_dependency,db: db_dependency,todo_id : int = Path(gt=0),):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    todo  = db.query(Todo).filter(Todo.id == todo_id).filter(Todo.owner_id == user.get("role")).first()
    if todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")


    db.delete(todo)
    db.commit()

def markdown_to_html(markdown_string):
    html = markdown.markdown(markdown_string)
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()
    return text

def create_todo_with_gemini(todo_string : str):
    load_dotenv()
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    llm = ChatGoogleGenerativeAI(model="gemini-pro")
    response = llm.invoke(
        [
            HumanMessage(
                content="I will provide you a todo item to add my to do list. What i want you to do is to create a longer and more comprehensive description of that todo item, my next message will be my todo:"),
            HumanMessage(content=todo_string),
        ]
    )
    return markdown_to_html(response.content)

if __name__ == "__main__":
    print(create_todo_with_gemini("learn java"))

