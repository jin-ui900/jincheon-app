"""
database.py — PostgreSQL 연결 (Railway)
환경변수 DATABASE_URL 사용
SQLite 없이 PostgreSQL만 사용
"""
import os
import asyncpg
from contextlib import asynccontextmanager

DATABASE_URL = os.environ.get("DATABASE_URL", "")

# Railway PostgreSQL URL은 postgres:// 로 시작하는 경우가 있어서 변환
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

_pool = None

async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
    return _pool

async def get_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn

async def init_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        # 회원 테이블
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id         SERIAL PRIMARY KEY,
                name       TEXT    NOT NULL,
                email      TEXT    UNIQUE NOT NULL,
                password   TEXT    NOT NULL,
                phone      TEXT,
                region     TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        # 상품 테이블
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id          SERIAL PRIMARY KEY,
                user_id     INTEGER NOT NULL REFERENCES users(id),
                title       TEXT    NOT NULL,
                description TEXT,
                price       INTEGER NOT NULL,
                category    TEXT,
                condition   TEXT,
                deal_type   TEXT,
                region      TEXT,
                status      TEXT    DEFAULT '판매중',
                image_path  TEXT,
                allow_offer INTEGER DEFAULT 0,
                is_free     INTEGER DEFAULT 0,
                view_count  INTEGER DEFAULT 0,
                like_count  INTEGER DEFAULT 0,
                created_at  TIMESTAMP DEFAULT NOW()
            )
        """)
        # 관심상품 테이블
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS likes (
                id         SERIAL PRIMARY KEY,
                user_id    INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(user_id, product_id)
            )
        """)
        # 후기 테이블
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id         SERIAL PRIMARY KEY,
                product_id INTEGER NOT NULL REFERENCES products(id),
                seller_id  INTEGER NOT NULL,
                buyer_id   INTEGER NOT NULL,
                rating     INTEGER NOT NULL,
                content    TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        # 거래 테이블
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id          SERIAL PRIMARY KEY,
                product_id  INTEGER NOT NULL REFERENCES products(id),
                seller_id   INTEGER NOT NULL,
                buyer_id    INTEGER NOT NULL,
                price       INTEGER NOT NULL,
                deal_type   TEXT,
                deal_place  TEXT,
                deal_time   TEXT,
                pay_method  TEXT,
                status      TEXT    DEFAULT '진행중',
                created_at  TIMESTAMP DEFAULT NOW()
            )
        """)
        print("✅ PostgreSQL DB 초기화 완료")
