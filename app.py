import base64
import html
from pathlib import Path

import pandas as pd
import streamlit as st


# =========================
# НАСТРОЙКИ
# =========================
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQwA5g3ZuBmZlY3vQMbc7nautnpK7c4ioKtTYU_mTskZb6A6nJ_yeokKIvfbVBFH1jTPpzOgoBMD89n/pub?gid=372714191&single=true&output=csv"
APP_TITLE = "Министерство восстановления, развития приграничья и строительства Курской области"
APP_SUBTITLE = "Реестр объектов"
APP_DESC = "Единый список объектов 2025–2028 с быстрыми фильтрами и переходом в карточку/папку."


# =========================
# HELPERS
# =========================
def esc(x) -> str:
    """Safe HTML escape + NaN/None -> '—'."""
    if x is None:
        return "—"
    try:
        if pd.isna(x):
            return "—"
    except Exception:
        pass
    s = str(x).strip()
    if not s or s.lower() == "nan":
        return "—"
    return html.escape(s)


def read_image_b64(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    return base64.b64encode(p.read_bytes()).decode("utf-8")


def pick_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    lower_map = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand in df.columns:
            return cand
        lc = cand.lower()
        if lc in lower_map:
            return lower_map[lc]
    return None


def normalize_url(x) -> str:
    s = str(x or "").strip()
    if not s or s.lower() == "nan":
        return ""
    return s


def ordered_districts(values: list[str]) -> list[str]:
    clean = []
    for v in values:
        if v is None:
            continue
        s = str(v).strip()
        if not s or s.lower() == "nan":
            continue
        clean.append(s)

    # unique
    clean = list(dict.fromkeys(clean))

    first = []
    for prefer in ["г. Курск", "Курск"]:
        if prefer in clean:
            first.append(prefer)
            clean.remove(prefer)
            break

    for prefer in ["Курский район", "Курский р-н", "Курский р-он"]:
        if prefer in clean:
            first.append(prefer)
            clean.remove(prefer)
            break

    rest = sorted(clean, key=lambda x: x.lower())
    return first + rest


# =========================
# PAGE
# =========================
st.set_page_config(
    page_title=f"{APP_SUBTITLE} — Курская область",
    page_icon="🏛️",
    layout="wide",
)

GERB_B64 = read_image_b64("assets/gerb.png")


# =========================
# CSS (адаптив + светлая/тёмная тема + скрытие футера)
# =========================
st.markdown(
    """
<style>
/* контейнер */
.main .block-container{
    padding-top: 1.2rem;
    padding-bottom: 2.2rem;
    max-width: 1200px;
}

/* --- попытка убрать нижнюю подпись Streamlit (футер) --- */
footer {visibility: hidden;}
#MainMenu {visibility: hidden;}
header {visibility: hidden;}

/* ===== HERO ===== */
.hero-wrap{
    width: 100%;
    border-radius: 18px;
    overflow: hidden;
    box-shadow: 0 14px 30px rgba(0,0,0,.12);
    background: linear-gradient(135deg, #0f2a57 0%, #1a3f7d 45%, #0e2b5e 100%);
    position: relative;
}

.hero-wrap::after{
    content:"";
    position:absolute;
    inset:-30%;
    background:
      radial-gradient(circle at 70% 35%, rgba(255,255,255,.10), rgba(255,255,255,0) 55%),
      radial-gradient(circle at 20% 80%, rgba(255,255,255,.08), rgba(255,255,255,0) 60%);
    transform: rotate(8deg);
    pointer-events:none;
}

.hero{
    position: relative;
    z-index: 1;
    display: flex;
    gap: 16px;
    align-items: center;
    padding: 18px 22px;
}

.hero-logo{
    width: 92px;
    height: 92px;
    flex: 0 0 auto;
    border-radius: 16px;
    background: rgba(255,255,255,.08);
    border: 1px solid rgba(255,255,255,.18);
    display:flex;
    align-items:center;
    justify-content:center;
    backdrop-filter: blur(6px);
}

.hero-logo img{
    width: 68px;
    height: 68px;
    object-fit: contain;
    display:block;
}

.hero-text{ flex: 1 1 auto; min-width: 0; }

.hero-ministry{
    font-size: 22px;
    line-height: 1.18;
    font-weight: 800;
    color: #ffffff;
    margin: 0 0 6px 0;
    letter-spacing: .2px;
    word-break: break-word;
}

.hero-app{
    font-size: 18px;
    line-height: 1.18;
    font-weight: 700;
    color: rgba(255,255,255,.92);
    margin: 0 0 10px 0;
}

.hero-desc{
    font-size: 13px;
    line-height: 1.45;
    color: rgba(255,255,255,.85);
    margin: 0 0 10px 0;
}

.hero-pill{
    display:inline-flex;
    align-items:center;
    gap:8px;
    padding: 7px 10px;
    border-radius: 999px;
    background: rgba(255,255,255,.10);
    border: 1px solid rgba(255,255,255,.18);
    color: rgba(255,255,255,.92);
    font-size: 12px;
}

/* labels */
.filter-label{ font-weight: 700; margin: 2px 0 6px 0; }

/* ===== CARDS ===== */
.card{
    border-radius: 16px;
    padding: 14px 14px 12px 14px;
    border: 1px solid rgba(0,0,0,.07);
    background: rgba(255,255,255,.92);
    box-shadow: 0 8px 18px rgba(0,0,0,.06);
}

.card-title{
    font-size: 15px;
    font-weight: 800;
    margin: 0 0 10px 0;
}

.meta{
    border-radius: 12px;
    padding: 10px 10px;
    background: rgba(0,0,0,.035);
    border: 1px solid rgba(0,0,0,.06);
}

.meta-row{
    display:flex;
    align-items:flex-start;
    gap: 8px;
    margin: 4px 0;
    font-size: 13px;
    line-height: 1.35;
}
.meta-ico{ width: 18px; flex: 0 0 auto; }

.badges{
    display:flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 10px;
}

.badge{
    display:inline-flex;
    align-items:center;
    gap: 8px;
    padding: 6px 10px;
    border-radius: 999px;
    border: 1px solid rgba(0,0,0,.08);
    background: rgba(255,255,255,.75);
    font-size: 12px;
}

/* MOBILE */
@media (max-width: 640px){
    .main .block-container{
        padding-top: .8rem;
        padding-left: .9rem;
        padding-right: .9rem;
    }
    .hero{
        flex-wrap: wrap;
        justify-content: flex-start;
        padding: 16px 16px;
    }
    .hero-logo{ width: 80px; height: 80px; border-radius: 14px; }
    .hero-logo img{ width: 60px; height: 60px; }
    .hero-ministry{ font-size: 18px; }
    .hero-app{ font-size: 16px; margin-bottom: 8px; }
    .hero-desc{ font-size: 12.5px; }
}

/* DARK MODE */
@media (prefers-color-scheme: dark){
    .main{ background: #0b1220 !important; color: rgba(255,255,255,.92) !important; }
    .card{
        background: rgba(17,27,46,.85) !important;
        border: 1px solid rgba(255,255,255,.10) !important;
        box-shadow: 0 10px 22px rgba(0,0,0,.35) !important;
    }
    .card-title{ color: rgba(255,255,255,.96) !important; }
    .meta{
        background: rgba(255,255,255,.06) !important;
        border: 1px solid rgba(255,255,255,.10) !important;
    }
    .meta-row{ color: rgba(255,255,255,.90) !important; }
    .badge{
        background: rgba(255,255,255,.06) !important;
        border: 1px solid rgba(255,255,255,.12) !important;
        color: rgba(255,255,255,.92) !important;
    }
}
</style>
""",
    unsafe_allow_html=True,
)


# =========================
# DATA
# =========================
@st.cache_data(ttl=300)
def load_data(url: str) -> pd.DataFrame:
    return pd.read_csv(url)


df = load_data(CSV_URL)

col_id = pick_col(df, ["ID", "id", "Код", "Код объекта", "Шифр", "Номер"])
col_name = pick_col(df, ["Наименование", "Название", "Объект", "Наименование объекта"])
col_sector = pick_col(df, ["Отрасль", "Сфера", "Направление"])
col_district = pick_col(df, ["Район", "Муниципалитет", "МО", "Территория"])
col_address = pick_col(df, ["Адрес", "Местоположение", "Адрес объекта"])
col_resp = pick_col(df, ["Ответственный", "Куратор", "Ответственные"])
col_status = pick_col(df, ["Статус", "Состояние", "Стадия"])
col_works = pick_col(df, ["Работы", "Работы?", "Выполнение", "Строительство"])
col_card_url = pick_col(df, ["Ссылка на карточку", "Карточка", "Card URL", "card_url", "URL карточки"])
col_folder_url = pick_col(df, ["Ссылка на папку", "Папка", "Folder URL", "folder_url", "URL папки"])


# =========================
# HERO
# =========================
logo_html = (
    f'<div class="hero-logo"><img alt="Герб" src="data:image/png;base64,{GERB_B64}"/></div>'
    if GERB_B64
    else '<div class="hero-logo">🏛️</div>'
)

st.markdown(
    f"""
<div class="hero-wrap">
  <div class="hero">
    {logo_html}
    <div class="hero-text">
      <div class="hero-ministry">{html.escape(APP_TITLE)}</div>
      <div class="hero-app">{html.escape(APP_SUBTITLE)}</div>
      <div class="hero-desc">{html.escape(APP_DESC)}</div>
      <span class="hero-pill">📄 Источник данных: Google Sheets (CSV)</span>
    </div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

st.write("")


# =========================
# FILTERS (ВАЖНО: key у каждого виджета!)
# =========================
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown('<div class="filter-label">🏷️ Отрасль</div>', unsafe_allow_html=True)
    sectors = ["Все"]
    if col_sector:
        sectors += sorted(
            [s for s in df[col_sector].dropna().astype(str).str.strip().unique() if s and s.lower() != "nan"],
            key=lambda x: x.lower(),
        )
    sector_sel = st.selectbox(
        "Отрасль",
        sectors,
        index=0,
        key="sector_sel",
        label_visibility="collapsed",
    )

with c2:
    st.markdown('<div class="filter-label">📍 Район</div>', unsafe_allow_html=True)
    districts = ["Все"]
    if col_district:
        raw = df[col_district].dropna().astype(str).str.strip().tolist()
        districts += ordered_districts(raw)
    district_sel = st.selectbox(
        "Район",
        districts,
        index=0,
        key="district_sel",
        label_visibility="collapsed",
    )

with c3:
    st.markdown('<div class="filter-label">📌 Статус</div>', unsafe_allow_html=True)
    statuses = ["Все"]
    if col_status:
        statuses += sorted(
            [s for s in df[col_status].dropna().astype(str).str.strip().unique() if s and s.lower() != "nan"],
            key=lambda x: x.lower(),
        )
    status_sel = st.selectbox(
        "Статус",
        statuses,
        index=0,
        key="status_sel",
        label_visibility="collapsed",
    )

st.markdown('<div class="filter-label">🔎 Поиск (наименование / адрес / ответственный / id)</div>', unsafe_allow_html=True)
q = st.text_input(
    "Поиск",
    value="",
    key="search_q",
    label_visibility="collapsed",
).strip().lower()


# =========================
# APPLY FILTERS
# =========================
view = df.copy()

if col_sector and sector_sel != "Все":
    view = view[view[col_sector].astype(str).str.strip() == sector_sel]

if col_district and district_sel != "Все":
    view = view[view[col_district].astype(str).str.strip() == district_sel]

if col_status and status_sel != "Все":
    view = view[view[col_status].astype(str).str.strip() == status_sel]

if q:
    search_cols = [c for c in [col_name, col_address, col_resp, col_id] if c]
    if search_cols:
        mask = False
        for c in search_cols:
            mask = mask | view[c].astype(str).str.lower().str.contains(q, na=False)
        view = view[mask]

st.caption(f"Показано объектов: {len(view)} из {len(df)}")
st.divider()


# =========================
# RENDER CARDS
# =========================
def render_card(row: pd.Series):
    name = esc(row[col_name]) if col_name else "Объект"
    sector = esc(row[col_sector]) if col_sector else "—"
    district = esc(row[col_district]) if col_district else "—"
    address = esc(row[col_address]) if col_address else "—"
    resp = esc(row[col_resp]) if col_resp else "—"
    status = esc(row[col_status]) if col_status else "—"
    works = esc(row[col_works]) if col_works else "—"

    card_url = normalize_url(row[col_card_url]) if col_card_url else ""
    folder_url = normalize_url(row[col_folder_url]) if col_folder_url else ""

    st.markdown(
        f"""
<div class="card">
  <div class="card-title">{name}</div>
  <div class="meta">
    <div class="meta-row"><span class="meta-ico">🏷️</span><span><b>Отрасль:</b> {sector}</span></div>
    <div class="meta-row"><span class="meta-ico">📍</span><span><b>Район:</b> {district}</span></div>
    <div class="meta-row"><span class="meta-ico">🗺️</span><span><b>Адрес:</b> {address}</span></div>
    <div class="meta-row"><span class="meta-ico">👤</span><span><b>Ответственный:</b> {resp}</span></div>
  </div>

  <div class="badges">
    <span class="badge">📌 <b>Статус:</b> {status}</span>
    <span class="badge">🛠️ <b>Работы:</b> {works}</span>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    b1, b2 = st.columns(2)
    with b1:
        if card_url:
            st.link_button("📄 Открыть карточку", card_url, use_container_width=True)
        else:
            st.button("📄 Открыть карточку", disabled=True, use_container_width=True, help="Ссылка не заполнена")
    with b2:
        if folder_url:
            st.link_button("📁 Открыть папку", folder_url, use_container_width=True)
        else:
            st.button("📁 Открыть папку", disabled=True, use_container_width=True, help="Ссылка не заполнена")


left, right = st.columns(2)

for i, (_, r) in enumerate(view.iterrows()):
    target = left if i % 2 == 0 else right
    with target:
        render_card(r)
        st.write("")
