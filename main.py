# -*- coding: utf-8 -*-

from datetime import datetime

from fastapi import FastAPI, Depends, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from db import getDB, lifespan


app = FastAPI(lifespan=lifespan)

templates = Jinja2Templates(directory="templates")

app.mount(
    "/www",
    StaticFiles(directory="www"),
    name="www"
)


def row_to_dict(cursor, row):
    """將資料庫查詢結果轉成可供 Jinja 使用的 dictionary。"""
    if row is None:
        return None

    column_names = [
        getattr(column, "name", column[0])
        for column in cursor.description
    ]

    return dict(zip(column_names, row))


def rows_to_dicts(cursor, rows):
    return [
        row_to_dict(cursor, row)
        for row in rows
    ]


@app.get("/")
async def home():
    return RedirectResponse(
        url="/events",
        status_code=status.HTTP_303_SEE_OTHER
    )


# 活動清單
@app.get("/events", response_class=HTMLResponse)
async def show_event_list(
    request: Request,
    db=Depends(getDB)
):
    cursor = db.cursor()

    cursor.execute(
        """
        SELECT
            e.id,
            e.title,
            e.description,
            e.deadline,
            COUNT(r.id) AS registration_count
        FROM events AS e
        LEFT JOIN registrations AS r
            ON r.event_id = e.id
        GROUP BY
            e.id,
            e.title,
            e.description,
            e.deadline
        ORDER BY e.id DESC
        """
    )

    events = rows_to_dicts(cursor, cursor.fetchall())
    cursor.close()

    return templates.TemplateResponse(
        "activityList.html",
        {
            "request": request,
            "events": events
        }
    )


# 顯示新增活動表單
@app.get("/events/add", response_class=HTMLResponse)
async def show_add_event_form(request: Request):
    return templates.TemplateResponse(
        "activityAdd.html",
        {
            "request": request
        }
    )


# 儲存新活動
@app.post("/events/create")
async def create_event(
    title: str = Form(...),
    description: str = Form(""),
    deadline: datetime | None = Form(None),
    db=Depends(getDB)
):
    cursor = db.cursor()

    cursor.execute(
        """
        INSERT INTO events (
            title,
            description,
            deadline
        )
        VALUES (%s, %s, %s)
        """,
        (
            title.strip(),
            description.strip(),
            deadline
        )
    )

    db.commit()
    cursor.close()

    return RedirectResponse(
        url="/events",
        status_code=status.HTTP_303_SEE_OTHER
    )


# 顯示活動報名表
@app.get(
    "/events/{event_id}/register",
    response_class=HTMLResponse
)
async def show_registration_form(
    event_id: int,
    request: Request,
    db=Depends(getDB)
):
    cursor = db.cursor()

    cursor.execute(
        """
        SELECT id, title, description, deadline
        FROM events
        WHERE id = %s
        """,
        (event_id,)
    )

    event = row_to_dict(cursor, cursor.fetchone())
    cursor.close()

    if event is None:
        return HTMLResponse(
            content="<h1>找不到這個活動</h1>",
            status_code=404
        )

    return templates.TemplateResponse(
        "registrationAdd.html",
        {
            "request": request,
            "event": event,
            "error": None
        }
    )


# 儲存報名資料
@app.post("/events/{event_id}/register")
async def create_registration(
    event_id: int,
    request: Request,
    name: str = Form(...),
    phone: str = Form(...),
    db=Depends(getDB)
):
    cursor = db.cursor()

    # 取得活動資料
    cursor.execute(
        """
        SELECT id, title, description, deadline
        FROM events
        WHERE id = %s
        """,
        (event_id,)
    )

    event = row_to_dict(cursor, cursor.fetchone())

    if event is None:
        cursor.close()

        return HTMLResponse(
            content="<h1>找不到這個活動</h1>",
            status_code=404
        )

    # 檢查是否已超過截止時間
    if (
        event["deadline"] is not None
        and datetime.now() > event["deadline"]
    ):
        cursor.close()

        return templates.TemplateResponse(
            "registrationAdd.html",
            {
                "request": request,
                "event": event,
                "error": "這個活動已經截止報名。"
            },
            status_code=400
        )

    # 檢查相同活動、姓名及電話是否重複
    cursor.execute(
        """
        SELECT id
        FROM registrations
        WHERE event_id = %s
          AND name = %s
          AND phone = %s
        """,
        (
            event_id,
            name.strip(),
            phone.strip()
        )
    )

    duplicate_registration = cursor.fetchone()

    if duplicate_registration is not None:
        cursor.close()

        return templates.TemplateResponse(
            "registrationAdd.html",
            {
                "request": request,
                "event": event,
                "error": "相同姓名和電話已經報名過這個活動。"
            },
            status_code=400
        )

    cursor.execute(
        """
        INSERT INTO registrations (
            event_id,
            name,
            phone
        )
        VALUES (%s, %s, %s)
        """,
        (
            event_id,
            name.strip(),
            phone.strip()
        )
    )

    db.commit()
    cursor.close()

    return RedirectResponse(
        url=f"/events/{event_id}/registrations",
        status_code=status.HTTP_303_SEE_OTHER
    )


# 顯示活動報名名單
@app.get(
    "/events/{event_id}/registrations",
    response_class=HTMLResponse
)
async def show_registration_list(
    event_id: int,
    request: Request,
    db=Depends(getDB)
):
    cursor = db.cursor()

    cursor.execute(
        """
        SELECT id, title, description, deadline
        FROM events
        WHERE id = %s
        """,
        (event_id,)
    )

    event = row_to_dict(cursor, cursor.fetchone())

    if event is None:
        cursor.close()

        return HTMLResponse(
            content="<h1>找不到這個活動</h1>",
            status_code=404
        )

    cursor.execute(
        """
        SELECT id, event_id, name, phone, created_at
        FROM registrations
        WHERE event_id = %s
        ORDER BY created_at ASC
        """,
        (event_id,)
    )

    registrations = rows_to_dicts(
        cursor,
        cursor.fetchall()
    )

    cursor.close()

    return templates.TemplateResponse(
        "registrationList.html",
        {
            "request": request,
            "event": event,
            "registrations": registrations
        }
    )
