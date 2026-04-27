# 진천 자급자족 — 개발 가이드

## 폴더 구조
```
jincheon_app/
├── backend/
│   ├── main.py              # 앱 진입점
│   ├── database.py          # DB 연결 및 테이블 생성
│   ├── auth.py              # JWT 인증
│   ├── router_users.py      # 회원 API
│   ├── router_products.py   # 상품 API
│   ├── router_reviews.py    # 후기/거래 API
│   └── requirements.txt     # 필요 패키지
├── frontend/
│   └── static/
│       └── uploads/         # 업로드 이미지 저장
├── railway.toml             # 배포 설정
└── README.md
```

---

## 로컬 실행 방법

### 1. 패키지 설치
```bash
cd jincheon_app/backend
pip install -r requirements.txt
```

### 2. 서버 실행
```bash
uvicorn main:app --reload
```

### 3. API 문서 확인
브라우저에서 열기: http://localhost:8000/docs

---

## 주요 API 목록

### 회원
| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | /api/users/signup | 회원가입 |
| POST | /api/users/login  | 로그인 |
| GET  | /api/users/me     | 내 정보 |
| PUT  | /api/users/me     | 프로필 수정 |

### 상품
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET    | /api/products            | 상품 목록 |
| POST   | /api/products            | 상품 등록 |
| GET    | /api/products/{id}       | 상품 상세 |
| PUT    | /api/products/{id}       | 상품 수정 |
| DELETE | /api/products/{id}       | 상품 삭제 |
| POST   | /api/products/{id}/like  | 관심 토글 |
| GET    | /api/products/my/selling | 내 판매 목록 |
| GET    | /api/products/my/likes   | 관심 목록 |

### 후기 / 거래
| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | /api/reviews                      | 후기 등록 |
| GET  | /api/reviews/seller/{id}          | 판매자 후기 |
| POST | /api/trades                       | 거래 요청 |
| POST | /api/trades/{id}/complete         | 거래 완료 |

---

## Railway 배포 방법

1. GitHub에 이 폴더 올리기
   ```bash
   git init
   git add .
   git commit -m "첫 배포"
   git remote add origin https://github.com/your-id/jincheon-app.git
   git push -u origin main
   ```

2. https://railway.app 접속 → New Project → GitHub 연동

3. 자동 배포 완료! 🎉

---

## 다음 단계 (C단계)
- [ ] 프론트엔드 HTML에 API 연동 (fetch 추가)
- [ ] 이미지 업로드 실제 연결
- [ ] GitHub 올리기
- [ ] Railway 배포
