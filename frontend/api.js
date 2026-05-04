/**
 * api.js — 진천 자급자족 API 연동
 * 서버 주소만 바꾸면 로컬/배포 환경 모두 동작
 */

// ── 설정 ──────────────────────────────────────────────────────
const API_BASE = "";

// ── 토큰 관리 ─────────────────────────────────────────────────
const Auth = {
  getToken: () => localStorage.getItem("jc_token"),
  setToken: (t) => localStorage.setItem("jc_token", t),
  removeToken: () => localStorage.removeItem("jc_token"),
  getUser: () => JSON.parse(localStorage.getItem("jc_user") || "null"),
  setUser: (u) => localStorage.setItem("jc_user", JSON.stringify(u)),
  removeUser: () => localStorage.removeItem("jc_user"),
  isLoggedIn: () => !!localStorage.getItem("jc_token"),
};

// ── 공통 fetch 래퍼 ───────────────────────────────────────────
async function api(method, path, body = null, isForm = false) {
  const headers = {};
  const token = Auth.getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (!isForm && body) headers["Content-Type"] = "application/json";

  const options = { method, headers };
  if (body) options.body = isForm ? body : JSON.stringify(body);

  try {
    const res = await fetch(`${API_BASE}${path}`, options);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "오류가 발생했어요");
    return data;
  } catch (err) {
    if (err.message === "Failed to fetch") {
      throw new Error("서버에 연결할 수 없어요. 잠시 후 다시 시도해주세요.");
    }
    throw err;
  }
}

// ── 토스트 메시지 ─────────────────────────────────────────────
function toast(msg, isError = false) {
  let el = document.getElementById("api-toast");
  if (!el) {
    el = document.createElement("div");
    el.id = "api-toast";
    el.style.cssText = `
      position:fixed;bottom:80px;left:50%;transform:translateX(-50%);
      padding:10px 20px;border-radius:8px;font-size:13px;font-family:inherit;
      z-index:9999;transition:opacity .3s;pointer-events:none;
      max-width:320px;text-align:center;
    `;
    document.body.appendChild(el);
  }
  el.textContent = msg;
  el.style.background = isError ? "#e8380d" : "#222";
  el.style.color = "#fff";
  el.style.opacity = "1";
  clearTimeout(el._t);
  el._t = setTimeout(() => el.style.opacity = "0", 2500);
}

// ── 로딩 표시 ─────────────────────────────────────────────────
function setLoading(btnEl, loading) {
  if (!btnEl) return;
  if (loading) {
    btnEl._orig = btnEl.textContent;
    btnEl.textContent = "처리 중...";
    btnEl.disabled = true;
    btnEl.style.opacity = "0.7";
  } else {
    btnEl.textContent = btnEl._orig || btnEl.textContent;
    btnEl.disabled = false;
    btnEl.style.opacity = "1";
  }
}

// ══════════════════════════════════════════════════════════════
// 회원 API
// ══════════════════════════════════════════════════════════════

const UserAPI = {
  // 회원가입
  async signup(name, email, password, phone, region) {
    const data = await api("POST", "/api/users/signup", { name, email, password, phone, region });
    Auth.setToken(data.token);
    Auth.setUser({ name: data.name, region: data.region });
    return data;
  },

  // 로그인
  async login(email, password) {
    const data = await api("POST", "/api/users/login", { email, password });
    Auth.setToken(data.token);
    Auth.setUser({ name: data.name, region: data.region });
    return data;
  },

  // 내 정보
  async getMe() {
    return await api("GET", "/api/users/me");
  },

  // 비밀번호 재설정
  async resetPassword(email, name, region, newPassword) {
    return await api("POST", "/api/users/reset-password", {
      email, name, region, new_password: newPassword
    });
  },

  // 로그아웃
  logout() {
    Auth.removeToken();
    Auth.removeUser();
  },
};

// ══════════════════════════════════════════════════════════════
// 상품 API
// ══════════════════════════════════════════════════════════════

const ProductAPI = {
  // 상품 목록
  async list(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return await api("GET", `/api/products${qs ? "?" + qs : ""}`);
  },

  // 상품 상세
  async get(id) {
    return await api("GET", `/api/products/${id}`);
  },

  // 상품 등록
  async create(formData) {
    return await api("POST", "/api/products", formData, true);
  },

  // 상품 수정
  async update(id, formData) {
    return await api("PUT", `/api/products/${id}`, formData, true);
  },

  // 상품 삭제
  async delete(id) {
    return await api("DELETE", `/api/products/${id}`);
  },

  // 관심 토글
  async toggleLike(id) {
    return await api("POST", `/api/products/${id}/like`);
  },

  // 내 판매 목록
  async mySelling() {
    return await api("GET", "/api/products/my/selling");
  },

  // 관심 목록
  async myLikes() {
    return await api("GET", "/api/products/my/likes");
  },
};

// ══════════════════════════════════════════════════════════════
// 거래/후기 API
// ══════════════════════════════════════════════════════════════

const TradeAPI = {
  // 거래 요청 (구매하기)
  async create(productId, dealType, dealPlace, dealTime, payMethod) {
    return await api("POST", "/api/trades", {
      product_id: productId, deal_type: dealType,
      deal_place: dealPlace, deal_time: dealTime, pay_method: payMethod,
    });
  },

  // 거래 완료
  async complete(tradeId) {
    return await api("POST", `/api/trades/${tradeId}/complete`);
  },
};

const ReviewAPI = {
  // 후기 등록
  async create(productId, rating, content) {
    return await api("POST", "/api/reviews", { product_id: productId, rating, content });
  },

  // 판매자 후기 목록
  async getSeller(sellerId) {
    return await api("GET", `/api/reviews/seller/${sellerId}`);
  },
};

// ══════════════════════════════════════════════════════════════
// UI 연동 함수들
// ══════════════════════════════════════════════════════════════

// 가격 포맷
function formatPrice(price) {
  return Number(price).toLocaleString("ko-KR") + "원";
}

// 시간 포맷 (n분 전, n시간 전 등)
function formatTime(dateStr) {
  if (!dateStr) return "";
  const diff = (Date.now() - new Date(dateStr).getTime()) / 1000;
  if (diff < 60) return "방금";
  if (diff < 3600) return Math.floor(diff / 60) + "분 전";
  if (diff < 86400) return Math.floor(diff / 3600) + "시간 전";
  if (diff < 604800) return Math.floor(diff / 86400) + "일 전";
  return dateStr.slice(0, 10);
}

// 상품 카드 HTML 생성
function renderProductCard(p) {
  const isUsed = p.condition === "중고";
  const emoji = {
    "식품/농산물": "🌾", "생활가전": "📺", "의류": "👕",
    "가구": "🪑", "유아": "🧸", "스포츠": "⚽", "기타": "🛍️"
  }[p.category] || "🛍️";

  return `
    <div class="gcard" onclick="openDetail(${p.id})">
      <div class="gcard-img">
        ${p.image_path
          ? `<img src="${p.image_path}" style="width:100%;height:100%;object-fit:cover">`
          : emoji}
        <div class="ribbon ${isUsed ? "used" : ""}">${p.condition || "새상품"}</div>
      </div>
      <div class="gcard-info">
        <div class="gcard-name">${p.title}</div>
        <div><span class="gcard-price">${formatPrice(p.price)}</span></div>
        <div class="gcard-meta">
          <span>${p.region || ""}</span>
          <span>${formatTime(p.created_at)}</span>
        </div>
      </div>
    </div>`;
}

// ── 메인 화면 상품 로드 ───────────────────────────────────────
let currentPage = 1;
let currentFilter = {};

async function loadProducts(filter = {}, append = false) {
  const grid = document.getElementById("main-grid");
  if (!grid) return;

  // -------------------------------------------------------------
  // ⭐ [수정된 부분] 상단 카테고리 탭과 필터 상태 값 가져오기
  // -------------------------------------------------------------
  // 1. 상단 탭(빨간 배경)에서 선택된 카테고리 글자 가져오기
  const mainCatEl = document.querySelector('.hd-cat.on');
  const categoryValue = mainCatEl && mainCatEl.textContent !== '전체' ? mainCatEl.textContent.trim() : '';

  // 2. 필터 화면에서 상태(새상품/중고) 값 가져오기
  const condEl = document.querySelector('.fil-section:nth-child(3) .fil-chip.on');
  const conditionValue = condEl && condEl.textContent !== '전체' ? condEl.textContent.trim() : '';

  // 읽어온 필터 값을 currentFilter 객체에 덮어씌웁니다.
  currentFilter = {};
  if (categoryValue) currentFilter.category = categoryValue;
  if (conditionValue) currentFilter.condition = conditionValue;
  // -------------------------------------------------------------

  if (!append) {
    grid.innerHTML = `<div style="grid-column:1/-1;padding:40px;text-align:center;color:#aaa;font-size:14px">로딩 중...</div>`;
    currentPage = 1;
  }

  try {
    const params = { ...currentFilter, ...filter, page: currentPage, limit: 20 };
    const res = await ProductAPI.list(params);

    if (!append) grid.innerHTML = "";

    if (res.items.length === 0 && !append) {
      grid.innerHTML = `<div style="grid-column:1/-1;padding:40px;text-align:center;color:#aaa;font-size:14px">해당하는 상품이 없어요. 🌿</div>`;
      return;
    }

    res.items.forEach(p => {
      grid.insertAdjacentHTML("beforeend", renderProductCard(p));
    });

    currentPage++;
  } catch (err) {
    grid.innerHTML = `<div style="grid-column:1/-1;padding:40px;text-align:center;color:#e8380d;font-size:13px">${err.message}</div>`;
  }
}

// ── 상품 상세 열기 ────────────────────────────────────────────
let currentProduct = null;

async function openDetail(productId) {
  show("s-detail");
  try {
    const p = await ProductAPI.get(productId);
    currentProduct = p;

    // 이미지
    const imgEl = document.getElementById("det-img");
    if (imgEl) {
      const emoji = {"식품/농산물":"🌾","생활가전":"📺","의류":"👕","가구":"🪑","유아":"🧸","스포츠":"⚽"}[p.category] || "🛍️";
      imgEl.innerHTML = p.image_path
        ? `<img src="${p.image_path}" style="width:100%;height:100%;object-fit:cover">`
        : emoji;
    }

    // 배지
    const badgesEl = document.getElementById("det-badges");
    if (badgesEl) {
      const cls = p.condition === "중고" ? "det-badge-used" : "det-badge-new";
      badgesEl.innerHTML = `<span class="det-badge ${cls}">${p.condition || "새상품"}</span>`;
    }

    // 제목, 가격
    const nameEl = document.getElementById("det-name");
    if (nameEl) nameEl.textContent = p.title || "";
    const priceEl = document.getElementById("det-price");
    if (priceEl) priceEl.textContent = formatPrice(p.price);

    // 메타
    const metaEl = document.getElementById("det-meta");
    if (metaEl) metaEl.innerHTML = `<span>${p.region||""}</span><span>조회 ${p.view_count||0}</span><span>관심 ${p.like_count||0}</span>`;

    // 판매자
    const snameEl = document.getElementById("det-sname");
    if (snameEl) snameEl.textContent = p.seller_name || "";
    const ssubEl = document.getElementById("det-ssub");
    if (ssubEl) ssubEl.textContent = (p.seller_region || "") + " 판매자";

    // 설명
    const descEl = document.getElementById("det-desc");
    if (descEl) descEl.innerHTML = (p.description || "").split("\n").join("<br>");

    // 스펙
    const condEl = document.getElementById("det-condition");
    if (condEl) condEl.textContent = p.condition || "";
    const dealEl = document.getElementById("det-deal");
    if (dealEl) dealEl.textContent = p.deal_type || "";
    const regEl = document.getElementById("det-region");
    if (regEl) regEl.textContent = p.region || "";
    const offerEl = document.getElementById("det-offer");
    if (offerEl) offerEl.textContent = p.allow_offer ? "가능" : "불가";

    // 관심 버튼
    const heartEl = document.querySelector(".det-heart");
    if (heartEl) heartEl.textContent = p.liked ? "❤️" : "🤍";

  } catch (err) {
    toast("상품 정보를 불러올 수 없어요", true);
    show("s-main");
  }
}

// ── 관심 토글 ─────────────────────────────────────────────────
async function toggleLike() {
  if (!Auth.isLoggedIn()) { toast("로그인이 필요해요"); show("s-login"); return; }
  if (!currentProduct) return;
  try {
    const res = await ProductAPI.toggleLike(currentProduct.id);
    const heartEl = document.querySelector(".det-heart");
    if (heartEl) heartEl.textContent = res.liked ? "❤️" : "🤍";
    toast(res.liked ? "관심 상품에 추가됐어요!" : "관심 상품에서 제거됐어요");
  } catch (err) { toast(err.message, true); }
}

// ── 로그인 처리 ───────────────────────────────────────────────
async function doLogin() {
  const email = document.getElementById("login-email")?.value.trim();
  const pw = document.getElementById("login-pw")?.value;
  const err = document.getElementById("login-error");
  const btn = document.querySelector("#s-login .auth-btn");

  if (!email || !pw) {
    if (err) { err.textContent = "이메일과 비밀번호를 입력해주세요"; err.classList.add("show"); }
    return;
  }

  setLoading(btn, true);
  try {
    await UserAPI.login(email, pw);
    if (err) err.classList.remove("show");
    await loadProducts();
    loadMyInfo();
    show("s-main");
  } catch (e) {
    if (err) { err.textContent = e.message; err.classList.add("show"); }
  } finally {
    setLoading(btn, false);
  }
}

// ── 회원가입 처리 ─────────────────────────────────────────────
async function doSignup() {
  const name   = document.getElementById("signup-name")?.value.trim();
  const email  = document.getElementById("signup-email")?.value.trim();
  const pw     = document.getElementById("signup-pw")?.value;
  const pw2    = document.getElementById("signup-pw2")?.value;
  const region = document.getElementById("signup-region")?.value;
  const phone  = document.getElementById("signup-phone")?.value.trim();
  const err    = document.getElementById("signup-error");
  const btn    = document.querySelector("#s-signup .auth-btn");

  const check = (cond, msg) => { if (cond) { if (err) { err.textContent = msg; err.classList.add("show"); } return false; } return true; };
  if (!check(!name, "이름을 입력해주세요")) return;
  if (!check(!email, "이메일을 입력해주세요")) return;
  if (!check(pw.length < 8, "비밀번호는 8자 이상이어야 해요")) return;
  if (!check(pw !== pw2, "비밀번호가 일치하지 않아요")) return;
  if (!check(!region, "지역을 선택해주세요")) return;

  setLoading(btn, true);
  try {
    await UserAPI.signup(name, email, pw, phone, region);
    if (err) err.classList.remove("show");
    toast("가입 완료! 환영합니다 😊");
    await loadProducts();
    loadMyInfo();
    show("s-main");
  } catch (e) {
    if (err) { err.textContent = e.message; err.classList.add("show"); }
  } finally {
    setLoading(btn, false);
  }
}

// ── 판매 등록 처리 ────────────────────────────────────────────
async function submitProduct() {
  if (!Auth.isLoggedIn()) { toast("로그인이 필요해요"); show("s-login"); return; }

  const title    = document.getElementById("reg-title")?.value.trim();
  const desc     = document.getElementById("reg-desc")?.value.trim();
  const price    = document.getElementById("reg-price")?.value;
  const category = document.getElementById("reg-category")?.value; // 값이 없으면 빈 문자열("")
  const region   = document.getElementById("reg-region")?.value || "진천읍";
  
  // 수정된 부분: 화면에 있는 여러 칩(버튼) 그룹을 순서대로 가져옵니다.
  // 첫 번째 그룹은 '상태', 두 번째 그룹은 '거래방식' 입니다.
  const chipGroups = document.querySelectorAll("#s-reg .reg-chips");
  const condition = chipGroups[0]?.querySelector(".reg-chip.on")?.textContent?.trim() || "중고 양호";
  const dealType  = chipGroups[1]?.querySelector(".reg-chip.on")?.textContent?.trim() || "직거래";

  const imageInput = document.getElementById("reg-image-input");
  const btn        = document.getElementById("reg-submit-btn");

  // 검증: 카테고리 필수 선택 추가
  if (!category) { toast("카테고리를 선택해주세요", true); return; }
  if (!title)  { toast("상품명을 입력해주세요", true); return; }
  if (!price || Number(price) <= 0) { toast("가격을 입력해주세요", true); return; }

  const formData = new FormData();
  formData.append("title",       title);
  formData.append("description", desc || "");
  formData.append("price",       price);
  formData.append("category",    category);
  formData.append("condition",   condition);
  formData.append("region",      region);
  formData.append("deal_type",   dealType);
  if (imageInput?.files[0]) formData.append("image", imageInput.files[0]);

  setLoading(btn, true);
  try {
    const token = Auth.getToken();
    const res = await fetch(`${API_BASE}/api/products`, {
      method: "POST",
      headers: token ? { "Authorization": `Bearer ${token}` } : {},
      body: formData
    });
    
    const data = await res.json();
    if (!res.ok) { toast(data.detail || "등록 실패", true); return; }
    
    toast("상품이 등록됐어요 🎉");
    
    // 폼 초기화 (카테고리도 초기화되도록 추가)
    ["reg-title", "reg-desc", "reg-price", "reg-category"].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.value = "";
    });
    if (imageInput) imageInput.value = "";
    
    await loadProducts();
    show("s-main");
  } catch(e) {
    toast("서버 연결 오류가 발생했어요", true);
  } finally {
    setLoading(btn, false);
  }
}

// ── 구매 처리 ─────────────────────────────────────────────────
async function submitPurchase() {
  if (!Auth.isLoggedIn()) { toast("로그인이 필요해요"); show("s-login"); return; }
  if (!currentProduct) return;

  const dealType  = document.querySelector("#s-pay .pay-method-btn.on")?.textContent || "직거래";
  const dealPlace = document.querySelectorAll("#s-pay .pay-input")[0]?.value || "";
  const dealTime  = document.querySelectorAll("#s-pay .pay-input")[1]?.value || "";
  const payMethod = document.querySelectorAll("#s-pay .pay-method")[1]?.querySelector(".on")?.textContent || "계좌이체";
  const btn       = document.querySelector("#s-pay .pay-btn");

  setLoading(btn, true);
  try {
    await TradeAPI.create(currentProduct.id, dealType, dealPlace, dealTime, payMethod);
    show("s-done");
  } catch (e) {
    toast(e.message, true);
  } finally {
    setLoading(btn, false);
  }
}

// ── 내 정보 로드 ──────────────────────────────────────────────
async function loadMyInfo() {
  const user = Auth.getUser();
  const nameEl   = document.getElementById("my-name-text");
  const regionEl = document.getElementById("my-region-text");
  if (nameEl && user) nameEl.textContent = user.name || "";
  if (regionEl && user) regionEl.textContent = user.region || "진천";

  if (!Auth.isLoggedIn()) return;
  try {
    const me = await UserAPI.getMe();
    if (nameEl) nameEl.textContent = me.name;
    if (regionEl) regionEl.textContent = me.region || "진천";
    const stats = me.stats;
    const nums = document.querySelectorAll(".my-stat-num");
    if (nums[0]) nums[0].textContent = stats.selling;
    if (nums[1]) nums[1].textContent = stats.done;
    if (nums[2]) nums[2].textContent = me.review_avg + "★";
  } catch (e) { /* 오류 무시 */ }
}

// ── 내 판매목록 로드 ──────────────────────────────────────────
async function loadMySelling() {
  if (!Auth.isLoggedIn()) { show("s-login"); return; }
  show("s-myselling");
  const list = document.getElementById("my-selling-list");
  if (!list) return;
  list.innerHTML = '<div style="padding:40px;text-align:center;color:#aaa;font-size:14px">로딩 중...</div>';
  try {
    const items = await ProductAPI.mySelling();
    if (!items.length) {
      list.innerHTML = '<div style="padding:40px;text-align:center;color:#aaa;font-size:14px">판매 상품이 없어요</div>';
      return;
    }
    const statusMap = {
      "판매중":   { cls: "status-selling", label: "판매중" },
      "예약중":   { cls: "status-reserved", label: "예약중" },
      "거래완료": { cls: "status-done",    label: "거래완료" },
      "판매중단": { cls: "status-stopped", label: "판매중단" },
    };
    const emoji = { "식품/농산물":"🌾","생활가전":"📺","의류":"👕","가구":"🪑","유아":"🧸","스포츠":"⚽" };

    list.innerHTML = items.map(p => {
      const st = statusMap[p.status] || { cls:"", label: p.status };
      const img = p.image_path
        ? `<img src="${p.image_path}" style="width:100%;height:100%;object-fit:cover;border-radius:8px">`
        : (emoji[p.category] || "🛍️");

      // 상태별 액션 버튼
      let actionBtns = "";
      if (p.status === "판매중") {
        actionBtns = `
          <button class="sell-action-btn btn-stop" onclick="event.stopPropagation();changeProductStatus(${p.id},'판매중단')">판매중단</button>
          <button class="sell-action-btn btn-complete" onclick="event.stopPropagation();changeProductStatus(${p.id},'거래완료')">거래완료</button>`;
      } else if (p.status === "판매중단") {
        actionBtns = `
          <button class="sell-action-btn btn-restart" onclick="event.stopPropagation();changeProductStatus(${p.id},'판매중')">다시 판매</button>
          <button class="sell-action-btn btn-delete" onclick="event.stopPropagation();deleteProduct(${p.id})">삭제</button>`;
      } else if (p.status === "예약중") {
        actionBtns = `
          <button class="sell-action-btn btn-complete" onclick="event.stopPropagation();changeProductStatus(${p.id},'거래완료')">거래완료</button>`;
      }

      return `
        <div class="my-sell-item" onclick="openDetail(${p.id})">
          <div class="my-sell-img">${img}</div>
          <div class="my-sell-body">
            <div class="my-sell-name">${p.title}</div>
            <div class="my-sell-price">${formatPrice(p.price)}</div>
            <div style="display:flex;align-items:center;flex-wrap:wrap;gap:4px;margin-top:5px">
              <span class="my-sell-status ${st.cls}">${st.label}</span>
              ${actionBtns}
            </div>
          </div>
        </div>`;
    }).join("");
  } catch (e) {
    list.innerHTML = '<div style="padding:40px;text-align:center;color:#e8380d;font-size:13px">불러오기 실패</div>';
  }
}

// ── 상품 상태 변경 ──────────────────────────────────────────
async function changeProductStatus(productId, newStatus) {
  if (!confirm(`상품을 "${newStatus}" 처리할까요?`)) return;
  try {
    const token = Auth.getToken();
    const formData = new FormData();
    formData.append("status", newStatus);
    const res = await fetch(`/api/products/${productId}`, {
      method: "PUT",
      headers: token ? { "Authorization": `Bearer ${token}` } : {},
      body: formData
    });
    if (!res.ok) { toast("변경 실패", true); return; }
    toast(`"${newStatus}"로 변경됐어요`);
    await loadMySelling();
    await loadProducts();
  } catch(e) {
    toast("오류가 발생했어요", true);
  }
}

// ── 상품 삭제 ──────────────────────────────────────────────
async function deleteProduct(productId) {
  if (!confirm("상품을 삭제할까요? 되돌릴 수 없어요.")) return;
  try {
    const token = Auth.getToken();
    const res = await fetch(`/api/products/${productId}`, {
      method: "DELETE",
      headers: token ? { "Authorization": `Bearer ${token}` } : {},
    });
    if (!res.ok) { toast("삭제 실패", true); return; }
    toast("삭제됐어요");
    await loadMySelling();
    await loadProducts();
  } catch(e) {
    toast("오류가 발생했어요", true);
  }
}

// ── 로그아웃 ──────────────────────────────────────────────────
function doLogout() {
  UserAPI.logout();
  toast("로그아웃 됐어요");
  show("s-login");
}

// ── 초기화 ────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
  // 로그인 상태이면 메인으로, 아니면 로그인 화면
  if (Auth.isLoggedIn()) {
    show("s-main");
    await loadProducts();
    loadMyInfo();
  } else {
    show("s-login");
  }

  // 관심 버튼 연결
  const heartEl = document.querySelector(".det-heart");
  if (heartEl) heartEl.onclick = toggleLike;

  // 구매하기 버튼 연결
  const buyBtn = document.querySelector(".det-buy");
  if (buyBtn) buyBtn.onclick = () => {
    if (!Auth.isLoggedIn()) { toast("로그인이 필요해요"); show("s-login"); return; }
    show("s-pay");
  };

  // 결제하기 버튼 연결
  const payBtn = document.querySelector(".pay-btn");
  if (payBtn) payBtn.onclick = submitPurchase;

  // 판매 등록 버튼 연결
  const regBtn = document.querySelector(".reg-submit");
  if (regBtn) regBtn.onclick = submitProduct;

  // 내 정보 탭 연결
  document.querySelectorAll(".bn").forEach(bn => {
    if (bn.textContent.includes("나")) {
      bn.onclick = () => { loadMyInfo(); show("s-my"); };
    }
  });

  // 내 판매 목록 클릭
  const mySellingBtn = document.querySelector('[onclick="show(\'s-myselling\')"]');
  if (mySellingBtn) mySellingBtn.onclick = loadMySelling;
});