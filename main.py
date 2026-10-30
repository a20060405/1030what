# -*- coding: utf-8 -*-
# main.py
from fastapi import FastAPI, Depends, Request, Form
from fastapi.responses import HTMLResponse,RedirectResponse
from fastapi.templating import Jinja2Templates
from .db import getDB, lifespan
from fastapi.staticfiles import StaticFiles

from starlette.middleware.sessions import SessionMiddleware
#from routes import router as all_routes
#from routes.upload import router as upload_router
#from routes import users


templates = Jinja2Templates(directory="templates")
app = FastAPI(lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key="your-secret-key",
	max_age=None, #86400,  # 1 day
    same_site="lax",  # Options: 'lax', 'strict', 'none'
    https_only=False,  # Set to True in production with HTTPS,
)
# Include the router
from .routes.login import router as loginRoute #取個別名避免同名變數衝突
app.include_router(loginRoute, prefix="/user") #mount every thing from ./routes/ to url under prefix

# 1. 處理 GET 請求：顯示新增活動的網頁
@app.get("/add_event", response_class=HTMLResponse)
async def show_add_event_form(request: Request):
    return templates.TemplateResponse("add_event.html", {"request": request})

# 2. 處理 POST 請求：接收表單送出的資料並存入資料庫
@app.post("/add_event")
async def submit_new_event(
    title: str = Form(...),          # 對應 HTML 表單的 name="title"
    description: str = Form(None),   # 對應 HTML 表單的 name="description"
    db = Depends(getDB)              # 使用你上課寫好的 db.py 來取得資料庫連線
):
    # 這裡的寫法取決於你 db.py 是怎麼寫的 (此為使用 cursor 的常見寫法)
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO Events (title, description) VALUES (%s, %s)", 
        (title, description)
    )
    db.commit()
    cursor.close()
    
    return HTMLResponse("<h3>活動新增成功！</h3><a href='/add_event'>繼續新增</a>")

#定義靜態網頁的目錄
app.mount("/w", StaticFiles(directory="www"))
