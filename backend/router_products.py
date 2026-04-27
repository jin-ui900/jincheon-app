"""
router_products.py — 상품 등록 / 조회 / 수정 / 삭제 / 검색 / 관심
"""
import os, shutil, uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import Optional
from database import get_db
from auth import get_current_user, get_optional_user

router = APIRouter(prefix="/api/products", tags=["products"])

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def save_image(file: UploadFile) -> str:
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, "jpg, png, webp 파일만 올릴 수 있어요")
    filename = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return f"/static/uploads/{filename}"


# ── 상품 등록 ─────────────────────────────────────────────────

@router.post("")
async def create_product(
    title:       str      = Form(...),
    description: str      = Form(""),
    price:       int      = Form(...),
    category:    str      = Form("기타"),
    condition:   str      = Form("중고"),
    deal_type:   str      = Form("직거래"),
    region:      str      = Form(""),
    allow_offer: int      = Form(0),
    is_free:     int      = Form(0),
    image:       Optional[UploadFile] = File(None),
    current_user=Depends(get_current_user),
    db=Depends(get_db)
):
    image_path = save_image(image) if image and image.filename else None

    await db.execute("""
        INSERT INTO products
            (user_id, title, description, price, category, condition,
             deal_type, region, allow_offer, is_free, image_path)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (current_user["id"], title, description, price, category,
          condition, deal_type, region, allow_offer, is_free, image_path))
    await db.commit()
    return {"message": "상품이 등록됐어요 🎉"}


# ── 상품 목록 조회 ────────────────────────────────────────────

@router.get("")
async def list_products(
    category:  str = "",
    condition: str = "",
    region:    str = "",
    min_price: int = 0,
    max_price: int = 99999999,
    deal_type: str = "",
    keyword:   str = "",
    sort:      str = "latest",   # latest / price_asc / price_desc
    page:      int = 1,
    limit:     int = 20,
    db=Depends(get_db)
):
    where = ["status != '거래완료'"]
    params = []

    if category:
        where.append("category=?"); params.append(category)
    if condition:
        where.append("condition=?"); params.append(condition)
    if region:
        where.append("region=?"); params.append(region)
    if deal_type:
        where.append("deal_type=?"); params.append(deal_type)
    if keyword:
        where.append("(title LIKE ? OR description LIKE ?)")
        params += [f"%{keyword}%", f"%{keyword}%"]
    where.append("price BETWEEN ? AND ?"); params += [min_price, max_price]

    order = {"latest": "created_at DESC", "price_asc": "price ASC", "price_desc": "price DESC"}.get(sort, "created_at DESC")
    sql = f"SELECT p.*, u.name as seller_name, u.region as seller_region FROM products p JOIN users u ON p.user_id=u.id WHERE {' AND '.join(where)} ORDER BY {order} LIMIT ? OFFSET ?"
    params += [limit, (page - 1) * limit]

    async with db.execute(sql, params) as cur:
        rows = await cur.fetchall()

    # 전체 개수
    count_sql = f"SELECT COUNT(*) as cnt FROM products p WHERE {' AND '.join(where[:-1])}"
    async with db.execute(count_sql, params[:-2]) as cur:
        total = (await cur.fetchone())["cnt"]

    return {
        "total": total,
        "page": page,
        "items": [dict(r) for r in rows]
    }


# ── 상품 상세 ─────────────────────────────────────────────────

@router.get("/{product_id}")
async def get_product(
    product_id: int,
    current_user=Depends(get_optional_user),
    db=Depends(get_db)
):
    # 조회수 +1
    await db.execute("UPDATE products SET view_count=view_count+1 WHERE id=?", (product_id,))
    await db.commit()

    async with db.execute("""
        SELECT p.*, u.name as seller_name, u.region as seller_region
        FROM products p JOIN users u ON p.user_id=u.id
        WHERE p.id=?
    """, (product_id,)) as cur:
        product = await cur.fetchone()

    if not product:
        raise HTTPException(404, "상품을 찾을 수 없어요")

    # 관심 여부
    liked = False
    if current_user:
        async with db.execute(
            "SELECT id FROM likes WHERE user_id=? AND product_id=?",
            (current_user["id"], product_id)
        ) as cur:
            liked = bool(await cur.fetchone())

    return {**dict(product), "liked": liked}


# ── 상품 수정 ─────────────────────────────────────────────────

@router.put("/{product_id}")
async def update_product(
    product_id:  int,
    title:       str = Form(""),
    description: str = Form(""),
    price:       int = Form(0),
    status:      str = Form(""),
    image:       Optional[UploadFile] = File(None),
    current_user=Depends(get_current_user),
    db=Depends(get_db)
):
    async with db.execute("SELECT user_id FROM products WHERE id=?", (product_id,)) as cur:
        product = await cur.fetchone()
    if not product:
        raise HTTPException(404, "상품을 찾을 수 없어요")
    if product["user_id"] != current_user["id"]:
        raise HTTPException(403, "내 상품만 수정할 수 있어요")

    image_path = save_image(image) if image and image.filename else None

    fields, params = [], []
    if title:       fields.append("title=?");       params.append(title)
    if description: fields.append("description=?"); params.append(description)
    if price:       fields.append("price=?");       params.append(price)
    if status:      fields.append("status=?");      params.append(status)
    if image_path:  fields.append("image_path=?");  params.append(image_path)

    if fields:
        params.append(product_id)
        await db.execute(f"UPDATE products SET {', '.join(fields)} WHERE id=?", params)
        await db.commit()

    return {"message": "수정됐어요"}


# ── 상품 삭제 ─────────────────────────────────────────────────

@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    current_user=Depends(get_current_user),
    db=Depends(get_db)
):
    async with db.execute("SELECT user_id FROM products WHERE id=?", (product_id,)) as cur:
        product = await cur.fetchone()
    if not product:
        raise HTTPException(404, "상품을 찾을 수 없어요")
    if product["user_id"] != current_user["id"]:
        raise HTTPException(403, "내 상품만 삭제할 수 있어요")

    await db.execute("DELETE FROM products WHERE id=?", (product_id,))
    await db.commit()
    return {"message": "삭제됐어요"}


# ── 관심 상품 토글 ────────────────────────────────────────────

@router.post("/{product_id}/like")
async def toggle_like(
    product_id: int,
    current_user=Depends(get_current_user),
    db=Depends(get_db)
):
    async with db.execute(
        "SELECT id FROM likes WHERE user_id=? AND product_id=?",
        (current_user["id"], product_id)
    ) as cur:
        existing = await cur.fetchone()

    if existing:
        await db.execute("DELETE FROM likes WHERE user_id=? AND product_id=?",
                         (current_user["id"], product_id))
        await db.execute("UPDATE products SET like_count=MAX(0,like_count-1) WHERE id=?", (product_id,))
        liked = False
    else:
        await db.execute("INSERT INTO likes (user_id, product_id) VALUES (?,?)",
                         (current_user["id"], product_id))
        await db.execute("UPDATE products SET like_count=like_count+1 WHERE id=?", (product_id,))
        liked = True

    await db.commit()
    return {"liked": liked}


# ── 내 판매 목록 ──────────────────────────────────────────────

@router.get("/my/selling")
async def my_products(
    current_user=Depends(get_current_user),
    db=Depends(get_db)
):
    async with db.execute(
        "SELECT * FROM products WHERE user_id=? ORDER BY created_at DESC",
        (current_user["id"],)
    ) as cur:
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


# ── 관심 상품 목록 ────────────────────────────────────────────

@router.get("/my/likes")
async def my_likes(
    current_user=Depends(get_current_user),
    db=Depends(get_db)
):
    async with db.execute("""
        SELECT p.* FROM products p
        JOIN likes l ON p.id=l.product_id
        WHERE l.user_id=?
        ORDER BY l.created_at DESC
    """, (current_user["id"],)) as cur:
        rows = await cur.fetchall()
    return [dict(r) for r in rows]
