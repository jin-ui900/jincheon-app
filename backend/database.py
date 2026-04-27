"""
database.py — SQLite DB 연결 및 테이블 생성
"""
import aiosqlite
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "jincheon.db")


async def get_db():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # 회원 테이블
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT    NOT NULL,
                email      TEXT    UNIQUE NOT NULL,
                password   TEXT    NOT NULL,
                phone      TEXT,
                region     TEXT,
                created_at TEXT    DEFAULT (datetime('now', 'localtime'))
            )
        """)

        # 상품 테이블
        await db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                title       TEXT    NOT NULL,
                description TEXT,
                price       INTEGER NOT NULL,
                category    TEXT,
                condition   TEXT,   -- 새상품 / 중고
                deal_type   TEXT,   -- 직거래 / 택배
                region      TEXT,
                status      TEXT    DEFAULT '판매중',  -- 판매중 / 예약중 / 거래완료
                image_path  TEXT,
                allow_offer INTEGER DEFAULT 0,  -- 가격제안 여부
                is_free     INTEGER DEFAULT 0,  -- 나눔 여부
                view_count  INTEGER DEFAULT 0,
                like_count  INTEGER DEFAULT 0,
                created_at  TEXT    DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # 관심상품 테이블
        await db.execute("""
            CREATE TABLE IF NOT EXISTS likes (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                created_at TEXT    DEFAULT (datetime('now', 'localtime')),
                UNIQUE(user_id, product_id)
            )
        """)

        # 후기 테이블
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                seller_id  INTEGER NOT NULL,
                buyer_id   INTEGER NOT NULL,
                rating     INTEGER NOT NULL,  -- 1~5
                content    TEXT,
                created_at TEXT    DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)

        # 거래 테이블
        await db.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id  INTEGER NOT NULL,
                seller_id   INTEGER NOT NULL,
                buyer_id    INTEGER NOT NULL,
                price       INTEGER NOT NULL,
                deal_type   TEXT,
                deal_place  TEXT,
                deal_time   TEXT,
                pay_method  TEXT,
                status      TEXT    DEFAULT '진행중',  -- 진행중 / 완료
                created_at  TEXT    DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)

        await db.commit()
        print("✅ DB 초기화 완료")
