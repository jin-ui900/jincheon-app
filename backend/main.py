"""
main.py — FastAPI 앱 진입점
실행: uvicorn main:app --reload
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from router_users import router as users_router
from router_products import router as products_router
from router_reviews import router as reviews_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="진천 자급자족 API",
    description="진천군 주민 전용 마켓플레이스",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(users_router)
app.include_router(products_router)
app.include_router(reviews_router)

# 프론트엔드 정적 파일 서빙
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
static_dir   = os.path.join(frontend_dir, "static")

if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

if os.path.exists(frontend_dir):
    app.mount("/app", StaticFiles(directory=frontend_dir, html=True), name="frontend")

@app.get("/")
async def root():
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "진천 자급자족 API 정상 작동 중 🌿"}

@app.get("/health")
async def health():
    return {"status": "ok"}
