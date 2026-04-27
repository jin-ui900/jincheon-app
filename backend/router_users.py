"""
router_users.py — 회원가입 / 로그인 / 내 정보
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from database import get_db
from auth import hash_password, verify_password, create_token, get_current_user

router = APIRouter(prefix="/api/users", tags=["users"])


# ── 요청 스키마 ──────────────────────────────────────────────

class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: str = ""
    region: str = ""


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ── 회원가입 ─────────────────────────────────────────────────

@router.post("/signup")
async def signup(body: SignupRequest, db=Depends(get_db)):
    if len(body.password) < 8:
        raise HTTPException(400, "비밀번호는 8자 이상이어야 해요")

    # 이메일 중복 확인
    async with db.execute("SELECT id FROM users WHERE email=?", (body.email,)) as cur:
        if await cur.fetchone():
            raise HTTPException(400, "이미 사용 중인 이메일이에요")

    hashed = hash_password(body.password)
    await db.execute(
        "INSERT INTO users (name, email, password, phone, region) VALUES (?,?,?,?,?)",
        (body.name, body.email, hashed, body.phone, body.region)
    )
    await db.commit()

    async with db.execute("SELECT id FROM users WHERE email=?", (body.email,)) as cur:
        user = await cur.fetchone()

    token = create_token(user["id"], body.email)
    return {"token": token, "name": body.name, "region": body.region}


# ── 로그인 ────────────────────────────────────────────────────

@router.post("/login")
async def login(body: LoginRequest, db=Depends(get_db)):
    async with db.execute(
        "SELECT id, name, password, region FROM users WHERE email=?", (body.email,)
    ) as cur:
        user = await cur.fetchone()

    if not user or not verify_password(body.password, user["password"]):
        raise HTTPException(401, "이메일 또는 비밀번호가 틀렸어요")

    token = create_token(user["id"], body.email)
    return {
        "token": token,
        "name": user["name"],
        "region": user["region"] or ""
    }


# ── 내 정보 ───────────────────────────────────────────────────

@router.get("/me")
async def get_me(current_user=Depends(get_current_user), db=Depends(get_db)):
    async with db.execute(
        "SELECT id, name, email, phone, region, created_at FROM users WHERE id=?",
        (current_user["id"],)
    ) as cur:
        user = await cur.fetchone()
    if not user:
        raise HTTPException(404, "사용자를 찾을 수 없어요")

    # 판매 통계
    async with db.execute(
        "SELECT status, COUNT(*) as cnt FROM products WHERE user_id=? GROUP BY status",
        (current_user["id"],)
    ) as cur:
        rows = await cur.fetchall()
    stats = {r["status"]: r["cnt"] for r in rows}

    # 후기 평균
    async with db.execute(
        "SELECT AVG(rating) as avg, COUNT(*) as cnt FROM reviews WHERE seller_id=?",
        (current_user["id"],)
    ) as cur:
        review = await cur.fetchone()

    return {
        "id":         user["id"],
        "name":       user["name"],
        "email":      user["email"],
        "phone":      user["phone"],
        "region":     user["region"],
        "created_at": user["created_at"],
        "stats": {
            "selling":  stats.get("판매중", 0),
            "reserved": stats.get("예약중", 0),
            "done":     stats.get("거래완료", 0),
        },
        "review_avg": round(review["avg"] or 0, 1),
        "review_cnt": review["cnt"] or 0,
    }


# ── 프로필 수정 ───────────────────────────────────────────────

class UpdateRequest(BaseModel):
    name: str = ""
    phone: str = ""
    region: str = ""


@router.put("/me")
async def update_me(
    body: UpdateRequest,
    current_user=Depends(get_current_user),
    db=Depends(get_db)
):
    await db.execute(
        "UPDATE users SET name=COALESCE(NULLIF(?,\"\"),name), phone=COALESCE(NULLIF(?,\"\"),phone), region=COALESCE(NULLIF(?,\"\"),region) WHERE id=?",
        (body.name, body.phone, body.region, current_user["id"])
    )
    await db.commit()
    return {"message": "프로필이 수정됐어요"}
