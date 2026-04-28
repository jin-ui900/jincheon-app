"""
router_products.py — 상품 API (PostgreSQL)
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
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
    """, current_user["id"], title, description, price, category,
        condition, deal_type, region, allow_offer, is_free, image_path)
    return {"message": "상품이 등록됐어요 🎉"}


@router.get("")
async def list_products(
    category:  str = "",
    condition: str = "",
    region:    str = "",
    min_price: int = 0,
    max_price: int = 99999999,
    deal_type: str = "",
    keyword:   str = "",
    sort:      str = "latest",
    page:      int = 1,
    limit:     int = 20,
    db=Depends(get_db)
):
    where = ["p.status != '거래완료'"]
    params = []
    i = 1

    if category:  where.append(f"p.category=${i}");  params.append(category);  i+=1
    if condition: where.append(f"p.condition=${i}"); params.append(condition); i+=1
    if region:    where.append(f"p.region=${i}");    params.append(region);    i+=1
    if deal_type: where.append(f"p.deal_type=${i}"); params.append(deal_type); i+=1
    if keyword:
        where.append(f"(p.title ILIKE ${i} OR p.description ILIKE ${i})")
        params.append(f"%{keyword}%"); i+=1

    where.append(f"p.price BETWEEN ${i} AND ${i+1}")
    params += [min_price, max_price]; i+=2

    order = {"latest": "p.created_at DESC", "price_asc": "p.price ASC", "price_desc": "p.price DESC"}.get(sort, "p.created_at DESC")
    sql = f"""SELECT p.*, u.name as seller_name, u.region as seller_region
              FROM products p JOIN users u ON p.user_id=u.id
              WHERE {' AND '.join(where)}
              ORDER BY {order} LIMIT ${i} OFFSET ${i+1}"""
    params += [limit, (page-1)*limit]

    rows = await db.fetch(sql, *params)
    count_sql = f"SELECT COUNT(*) FROM products p WHERE {' AND '.join(where[:-1])}"
    total = await db.fetchval(count_sql, *params[:-2])

    return {"total": total, "page": page, "items": [dict(r) for r in rows]}


@router.get("/my/selling")
async def my_products(current_user=Depends(get_current_user), db=Depends(get_db)):
    rows = await db.fetch(
        "SELECT * FROM products WHERE user_id=$1 ORDER BY created_at DESC",
        current_user["id"]
    )
    return [dict(r) for r in rows]


@router.get("/my/likes")
async def my_likes(current_user=Depends(get_current_user), db=Depends(get_db)):
    rows = await db.fetch("""
        SELECT p.* FROM products p
        JOIN likes l ON p.id=l.product_id
        WHERE l.user_id=$1 ORDER BY l.created_at DESC
    """, current_user["id"])
    return [dict(r) for r in rows]


@router.get("/{product_id}")
async def get_product(product_id: int, current_user=Depends(get_optional_user), db=Depends(get_db)):
    await db.execute("UPDATE products SET view_count=view_count+1 WHERE id=$1", product_id)
    product = await db.fetchrow("""
        SELECT p.*, u.name as seller_name, u.region as seller_region
        FROM products p JOIN users u ON p.user_id=u.id WHERE p.id=$1
    """, product_id)
    if not product:
        raise HTTPException(404, "상품을 찾을 수 없어요")
    liked = False
    if current_user:
        row = await db.fetchrow(
            "SELECT id FROM likes WHERE user_id=$1 AND product_id=$2",
            current_user["id"], product_id
        )
        liked = row is not None
    return {**dict(product), "liked": liked}


@router.put("/{product_id}")
async def update_product(
    product_id: int,
    title:      str = Form(""),
    description:str = Form(""),
    price:      int = Form(0),
    status:     str = Form(""),
    image:      Optional[UploadFile] = File(None),
    current_user=Depends(get_current_user),
    db=Depends(get_db)
):
    product = await db.fetchrow("SELECT user_id FROM products WHERE id=$1", product_id)
    if not product: raise HTTPException(404, "상품을 찾을 수 없어요")
    if product["user_id"] != current_user["id"]: raise HTTPException(403, "내 상품만 수정할 수 있어요")
    image_path = save_image(image) if image and image.filename else None
    fields, params, i = [], [], 1
    if title:       fields.append(f"title=${i}");       params.append(title);       i+=1
    if description: fields.append(f"description=${i}"); params.append(description); i+=1
    if price:       fields.append(f"price=${i}");       params.append(price);       i+=1
    if status:      fields.append(f"status=${i}");      params.append(status);      i+=1
    if image_path:  fields.append(f"image_path=${i}");  params.append(image_path);  i+=1
    if fields:
        params.append(product_id)
        await db.execute(f"UPDATE products SET {', '.join(fields)} WHERE id=${i}", *params)
    return {"message": "수정됐어요"}


@router.delete("/{product_id}")
async def delete_product(product_id: int, current_user=Depends(get_current_user), db=Depends(get_db)):
    product = await db.fetchrow("SELECT user_id FROM products WHERE id=$1", product_id)
    if not product: raise HTTPException(404, "상품을 찾을 수 없어요")
    if product["user_id"] != current_user["id"]: raise HTTPException(403, "내 상품만 삭제할 수 있어요")
    await db.execute("DELETE FROM products WHERE id=$1", product_id)
    return {"message": "삭제됐어요"}


@router.post("/{product_id}/like")
async def toggle_like(product_id: int, current_user=Depends(get_current_user), db=Depends(get_db)):
    existing = await db.fetchrow(
        "SELECT id FROM likes WHERE user_id=$1 AND product_id=$2",
        current_user["id"], product_id
    )
    if existing:
        await db.execute("DELETE FROM likes WHERE user_id=$1 AND product_id=$2", current_user["id"], product_id)
        await db.execute("UPDATE products SET like_count=GREATEST(0,like_count-1) WHERE id=$1", product_id)
        return {"liked": False}
    else:
        await db.execute("INSERT INTO likes (user_id, product_id) VALUES ($1,$2)", current_user["id"], product_id)
        await db.execute("UPDATE products SET like_count=like_count+1 WHERE id=$1", product_id)
        return {"liked": True}
