import os
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row

# 載入 .env 檔案裡面的環境變數
load_dotenv()

# 讀取變數並組合 PostgreSQL 連線字串
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Lifespan context manager for FastAPI
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pool = AsyncConnectionPool(
        conninfo=DATABASE_URL,
        kwargs={"row_factory": dict_row},
        open=False,
        #min_size=1,
        #max_size=10,
        #timeout=10,
    )
    await app.state.pool.open()
    print("✅ Connected to DB")

    yield  # App runs here

    # Shutdown logic
    await app.state.pool.close()
    print("🛑 Disconnected from DB")

# a wrapper for fastAPI's Depends Injection
async def getDB(request: Request):
    async with request.app.state.pool.connection() as conn:
        # set current login user from session
        yield conn