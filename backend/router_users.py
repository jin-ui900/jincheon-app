"""
router_users.py — 회원가입 / 로그인 / 내 정보 (PostgreSQL)
"""
import re
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from database import get_db
from auth import hash_password, verify_password, create_token, get_current_user

router = APIRouter(prefix="/api/users", tags=["users"])


class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: str = ""
    region: str = ""


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UpdateRequest(BaseModel):
    name: str = ""
    phone: str = ""
    region: str = ""

# 새롭게 추가된 비밀번호 재설정용 모델
class ResetPasswordRequest(BaseModel):
    email: EmailStr
    name: str
    region: str
    new_password: str


# ── 이메일 중복 확인 ──────────────────────────────────────────

@router.get("/check-email")
async def check_email(email: str, db=Depends(get_db)):
    if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email):
        raise HTTPException(400, "올바른 이메일 형식이 아니에요")
    row = await db.fetchrow("SELECT id FROM users WHERE email=$1", email)
    return {"available": row is None}


# ── 비밀번호 검증 ─────────────────────────────────────────────

def validate_password(pw: str):
    if len(pw) > 72:
        raise HTTPException(400, "비밀번호는 72자 이하로 입력해주세요")
    if len(pw) < 8:
        raise HTTPException(400, "비밀번호는 8자 이상이어야 해요")
    if not re.search(r"[A-Za-z]", pw):
        raise HTTPException(400, "비밀번호에 영문자를 포함해주세요")
    if not re.search(r"[0-9]", pw):
        raise HTTPException(400, "비밀번호에 숫자를 포함해주세요")


# ── 회원가입 ─────────────────────────────────────────────────

@router.post("/signup")
async def signup(body: SignupRequest, db=Depends(get_db)):
    validate_password(body.password)

    existing = await db.fetchrow("SELECT id FROM users WHERE email=$1", body.email)
    if existing:
        raise HTTPException(400, "이미 사용 중인 이메일이에요")

    hashed = hash_password(body.password)
    row = await db.fetchrow(
        "INSERT INTO users (name, email, password, phone, region) VALUES ($1,$2,$3,$4,$5) RETURNING id",
        body.name, body.email, hashed, body.phone, body.region
    )
    token = create_token(row["id"], body.email)
    return {"token": token, "name": body.name, "region": body.region}


# ── 로그인 ────────────────────────────────────────────────────

@router.post("/login")
async def login(body: LoginRequest, db=Depends(get_db)):
    user = await db.fetchrow(
        "SELECT id, name, password, region FROM users WHERE email=$1", body.email
    )
    if not user or not verify_password(body.password, user["password"]):
        raise HTTPException(401, "이메일 또는 비밀번호가 틀렸어요")

    token = create_token(user["id"], body.email)
    return {"token": token, "name": user["name"], "region": user["region"] or ""}


# ── 내 정보 ───────────────────────────────────────────────────

@router.get("/me")
async def get_me(current_user=Depends(get_current_user), db=Depends(get_db)):
    user = await db.fetchrow(
        "SELECT id, name, email, phone, region, created_at FROM users WHERE id=$1",
        current_user["id"]
    )
    if not user:
        raise HTTPException(404, "사용자를 찾을 수 없어요")

    stats_rows = await db.fetch(
        "SELECT status, COUNT(*) as cnt FROM products WHERE user_id=$1 GROUP BY status",
        current_user["id"]
    )
    stats = {r["status"]: r["cnt"] for r in stats_rows}

    review = await db.fetchrow(
        "SELECT AVG(rating) as avg, COUNT(*) as cnt FROM reviews WHERE seller_id=$1",
        current_user["id"]
    )

    return {
        "id":         user["id"],
        "name":       user["name"],
        "email":      user["email"],
        "phone":      user["phone"],
        "region":     user["region"],
        "created_at": str(user["created_at"]),
        "stats": {
            "selling":  stats.get("판매중", 0),
            "reserved": stats.get("예약중", 0),
            "done":     stats.get("거래완료", 0),
        },
        "review_avg": round(float(review["avg"] or 0), 1),
        "review_cnt": review["cnt"] or 0,
    }


# ── 프로필 수정 ───────────────────────────────────────────────

@router.put("/me")
async def update_me(
    body: UpdateRequest,
    current_user=Depends(get_current_user),
    db=Depends(get_db)
):
    await db.execute(
        """UPDATE users SET
           name   = CASE WHEN $1 != '' THEN $1 ELSE name END,
           phone  = CASE WHEN $2 != '' THEN $2 ELSE phone END,
           region = CASE WHEN $3 != '' THEN $3 ELSE region END
           WHERE id=$4""",
        body.name, body.phone, body.region, current_user["id"]
    )
    return {"message": "프로필이 수정됐어요"}


# ── 비밀번호 재설정 ─────────────────────────────────────────────

@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest, db=Depends(get_db)):
    user = await db.fetchrow(
        "SELECT id FROM users WHERE email=$1 AND name=$2 AND region=$3",
        body.email, body.name, body.region
    )
    if not user:
        raise HTTPException(400, "입력하신 정보와 일치하는 계정을 찾을 수 없어요.")

    validate_password(body.new_password)
    hashed = hash_password(body.new_password)
    await db.execute(
        "UPDATE users SET password=$1 WHERE id=$2",
        hashed, user["id"]
    )
    return {"message": "비밀번호가 성공적으로 변경됐어요."}