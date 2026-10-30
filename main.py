from fastapi import FastAPI, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from db import getDB, lifespan
import psycopg  # 用來捕捉資料庫錯誤

app = FastAPI(lifespan=lifespan)

# 掛載靜態檔案與模板
app.mount("/www", StaticFiles(directory="www"), name="www")
templates = Jinja2Templates(directory="templates")

# 根目錄自動導向活動清單
@app.get("/")
async def root():
    return RedirectResponse(url="/events")

# 1. 顯示活動清單 (對應 activityList.html)
@app.get("/events", response_class=HTMLResponse)
async def list_events(request: Request, db=Depends(getDB)):
    # 撈取所有活動，並計算每個活動目前的報名人數
    query = """
        SELECT e.id, e.title, e.description, e.deadline, 
               COUNT(r.id) as registration_count
        FROM Events e
        LEFT JOIN Registrations r ON e.id = r.event_id
        GROUP BY e.id
        ORDER BY e.id DESC
    """
    cursor = await db.execute(query)
    events = await cursor.fetchall()
    
    return templates.TemplateResponse(request=request, name="activityList.html", context={"request": request, "events": events})

# 2-1. 顯示新增活動表單 (對應 activityAdd.html)
@app.get("/events/add", response_class=HTMLResponse)
async def show_add_event_form(request: Request):
    return templates.TemplateResponse(request=request, name="activityAdd.html", context={"request": request})

# 2-2. 處理新增活動資料
@app.post("/events/create")
async def create_event(
    title: str = Form(...),
    description: str = Form(None),
    deadline: str = Form(None),
    db=Depends(getDB)
):
    # 若截止時間為空字串，轉換為 None 以符合資料庫格式
    deadline_val = deadline if deadline else None
    
    await db.execute(
        "INSERT INTO Events (title, description, deadline) VALUES (%s, %s, %s)",
        (title, description, deadline_val)
    )
    await db.commit()
    return RedirectResponse(url="/events", status_code=303)

# 3-1. 顯示報名表單 (對應 registrationAdd.html)
@app.get("/events/{event_id}/register", response_class=HTMLResponse)
async def show_register_form(request: Request, event_id: int, db=Depends(getDB)):
    cursor = await db.execute("SELECT * FROM Events WHERE id = %s", (event_id,))
    event = await cursor.fetchone()
    
    if not event:
        return HTMLResponse("找不到該活動", status_code=404)
        
    return templates.TemplateResponse(request=request, name="registrationAdd.html", context={"request": request, "event": event})

# 3-2. 處理報名資料
@app.post("/events/{event_id}/register")
async def submit_registration(
    request: Request,
    event_id: int,
    name: str = Form(...),
    phone: str = Form(...),
    db=Depends(getDB)
):
    # 先抓取活動資料（為了萬一報名失敗時，重新渲染表單使用）
    cursor = await db.execute("SELECT * FROM Events WHERE id = %s", (event_id,))
    event = await cursor.fetchone()

    try:
        await db.execute(
            "INSERT INTO Registrations (event_id, name, phone) VALUES (%s, %s, %s)",
            (event_id, name, phone)
        )
        await db.commit()
        # 報名成功，導向查看名單頁面
        return RedirectResponse(url=f"/events/{event_id}/registrations", status_code=303)
        
    except psycopg.errors.UniqueViolation:
        # 捕捉重複報名的錯誤 (需要你的資料庫表格有設定 UNIQUE 限制)
        await db.rollback()
        return templates.TemplateResponse(
            request=request,
            name="registrationAdd.html", 
            context={"request": request, "event": event, "error": "此姓名與電話已經報名過該活動囉！"}
        )

# 4. 查看報名清單 (對應 registrationList.html)
@app.get("/events/{event_id}/registrations", response_class=HTMLResponse)
async def list_registrations(request: Request, event_id: int, db=Depends(getDB)):
    # 抓取活動本身資訊
    cursor_event = await db.execute("SELECT * FROM Events WHERE id = %s", (event_id,))
    event = await cursor_event.fetchone()
    
    if not event:
        return HTMLResponse("找不到該活動", status_code=404)

    # 抓取該活動的所有報名者資訊
    cursor_reg = await db.execute(
        "SELECT * FROM Registrations WHERE event_id = %s ORDER BY created_at ASC", 
        (event_id,)
    )
    registrations = await cursor_reg.fetchall()
    
    return templates.TemplateResponse(
        request=request,
        name="registrationList.html", 
        context={"request": request, "event": event, "registrations": registrations}
    )