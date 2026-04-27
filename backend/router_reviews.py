"""
router_reviews.py — 후기 등록 / 조회 / 거래 완료 처리
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from database import get_db
from auth import get_current_user

router = APIRouter(tags=["reviews"])


# ── 후기 등록 ─────────────────────────────────────────────────

class ReviewRequest(BaseModel):
    product_id: int
    rating: int        # 1~5
    content: str = ""


@router.post("/api/reviews")
async def create_review(
    body: ReviewRequest,
    current_user=Depends(get_current_user),
    db=Depends(get_db)
):
    if not 1 <= body.rating <= 5:
        raise HTTPException(400, "별점은 1~5 사이로 입력해주세요")

    # 상품/판매자 확인
    async with db.execute("SELECT user_id, status FROM products WHERE id=?", (body.product_id,)) as cur:
        product = await cur.fetchone()
    if not product:
        raise HTTPException(404, "상품을 찾을 수 없어요")
    if product["status"] != "거래완료":
        raise HTTPException(400, "거래 완료된 상품에만 후기를 남길 수 있어요")
    if product["user_id"] == current_user["id"]:
        raise HTTPException(400, "내 상품엔 후기를 남길 수 없어요")

    # 중복 후기 확인
    async with db.execute(
        "SELECT id FROM reviews WHERE product_id=? AND buyer_id=?",
        (body.product_id, current_user["id"])
    ) as cur:
        if await cur.fetchone():
            raise HTTPException(400, "이미 후기를 남겼어요")

    await db.execute("""
        INSERT INTO reviews (product_id, seller_id, buyer_id, rating, content)
        VALUES (?,?,?,?,?)
    """, (body.product_id, product["user_id"], current_user["id"], body.rating, body.content))
    await db.commit()
    return {"message": "후기가 등록됐어요 😊"}


# ── 판매자 후기 목록 ──────────────────────────────────────────

@router.get("/api/reviews/seller/{seller_id}")
async def get_seller_reviews(seller_id: int, db=Depends(get_db)):
    async with db.execute("""
        SELECT r.*, u.name as buyer_name, p.title as product_title
        FROM reviews r
        JOIN users u ON r.buyer_id=u.id
        JOIN products p ON r.product_id=p.id
        WHERE r.seller_id=?
        ORDER BY r.created_at DESC
    """, (seller_id,)) as cur:
        rows = await cur.fetchall()

    async with db.execute(
        "SELECT AVG(rating) as avg, COUNT(*) as cnt FROM reviews WHERE seller_id=?",
        (seller_id,)
    ) as cur:
        stat = await cur.fetchone()

    return {
        "avg": round(stat["avg"] or 0, 1),
        "count": stat["cnt"],
        "items": [dict(r) for r in rows]
    }


# ── 거래 완료 처리 ────────────────────────────────────────────

class TradeRequest(BaseModel):
    product_id: int
    deal_type:  str = "직거래"
    deal_place: str = ""
    deal_time:  str = ""
    pay_method: str = "계좌이체"


@router.post("/api/trades")
async def create_trade(
    body: TradeRequest,
    current_user=Depends(get_current_user),
    db=Depends(get_db)
):
    async with db.execute(
        "SELECT user_id, price, status FROM products WHERE id=?", (body.product_id,)
    ) as cur:
        product = await cur.fetchone()

    if not product:
        raise HTTPException(404, "상품을 찾을 수 없어요")
    if product["status"] == "거래완료":
        raise HTTPException(400, "이미 거래 완료된 상품이에요")
    if product["user_id"] == current_user["id"]:
        raise HTTPException(400, "내 상품은 구매할 수 없어요")

    # 거래 생성
    await db.execute("""
        INSERT INTO trades (product_id, seller_id, buyer_id, price, deal_type, deal_place, deal_time, pay_method)
        VALUES (?,?,?,?,?,?,?,?)
    """, (body.product_id, product["user_id"], current_user["id"],
          product["price"], body.deal_type, body.deal_place, body.deal_time, body.pay_method))

    # 상품 상태 → 예약중
    await db.execute("UPDATE products SET status='예약중' WHERE id=?", (body.product_id,))
    await db.commit()
    return {"message": "거래 요청이 완료됐어요! 판매자와 약속 시간을 잡아보세요 😊"}


@router.post("/api/trades/{trade_id}/complete")
async def complete_trade(
    trade_id: int,
    current_user=Depends(get_current_user),
    db=Depends(get_db)
):
    async with db.execute(
        "SELECT * FROM trades WHERE id=?", (trade_id,)
    ) as cur:
        trade = await cur.fetchone()

    if not trade:
        raise HTTPException(404, "거래를 찾을 수 없어요")
    if trade["seller_id"] != current_user["id"] and trade["buyer_id"] != current_user["id"]:
        raise HTTPException(403, "해당 거래의 당사자만 완료 처리할 수 있어요")

    await db.execute("UPDATE trades SET status='완료' WHERE id=?", (trade_id,))
    await db.execute("UPDATE products SET status='거래완료' WHERE id=?", (trade["product_id"],))
    await db.commit()
    return {"message": "거래가 완료됐어요! 후기를 남겨보세요 🎉"}
