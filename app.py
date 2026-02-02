import base64
import html
import re
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

ASSET_GERB = "assets/gerb.png"


# =========================
# HELPERS
# =========================
def esc(x) -> str:
    """HTML-safe + NaN/None/empty -> '—'."""
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


def norm(x) -> str:
    if x is None:
        return ""
    try:
        if pd.isna(x):
            return ""
    except Exception:
        pass
    s = str(x).strip()
    if not s or s.lower() == "nan":
        return ""
    return s


def norm_lower(x) -> str:
    return norm(x).lower()


def read_image_b64(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    return base64.b64encode(p.read_bytes()).decode("utf-8")


def ordered_districts(values: list[str]) -> list[str]:
    clean = []
    for v in values:
        s = norm(v)
        if s:
            clean.append(s)

    clean = list(dict.fromkeys(clean))

    first = []
    # 1) Курск
    for prefer in ["г. Курск", "Курск", "г.Курск", "город Курск"]:
        if prefer in clean:
            first.append(prefer)
            clean.remove(prefer)
            break

    # 2) Курский район
    for prefer in ["Курский район", "Курский р-н", "Курский р-он"]:
        if prefer in clean:
            first.append(prefer)
            clean.remove(prefer)
            break

    rest = sorted(clean, key=lambda x: x.lower())
    return first + rest


def looks_like_url(s: str) -> bool:
    s = s.strip().lower()
    return s.startswith("http://") or s.startswith("https://")


def col_sample_strings(df: pd.DataFrame, col: str, n: int = 80) -> list[str]:
    ser = df[col].dropna()
    if ser.empty:
        return []
    vals = ser.astype(str).head(n).tolist()
    vals = [v.strip() for v in vals if v and str(v).strip().lower() != "nan"]
    return vals


def score_column_for_role(values: list[str], role: str) -> float:
    """Heuristic scoring of a column by its content."""
    if not values:
        return -1.0

    # basic stats
    uniq = len(set(values))
    total = len(values)
    avg_len = sum(len(v) for v in values) / max(total, 1)

    low = [v.lower() for v in values]

    if role == "url_card":
        # lots of urls + maybe docs
        url_cnt = sum(looks_like_url(v) for v in values)
        docs_cnt = sum(("docs.google" in v.lower() or "drive.google" in v.lower()) for v in values)
        return url_cnt * 2 + docs_cnt

    if role == "url_folder":
        url_cnt = sum(looks_like_url(v) for v in values)
        folder_hint = sum(("folder" in v.lower() or "folders" in v.lower() or "/folders/" in v.lower()) for v in values)
        drive_hint = sum(("drive.google" in v.lower()) for v in values)
        return url_cnt * 2 + folder_hint * 2 + drive_hint

    if role == "id":
        # patterns: ZDR-001, EDU-010, numbers, etc.
        pat1 = re.compile(r"^[A-ZА-Я]{2,5}[-_ ]?\d{1,4}$")
        pat2 = re.compile(r"^\d{1,6}$")
        hits = sum(bool(pat1.match(v.strip())) or bool(pat2.match(v.strip())) for v in values)
        # prefer high uniqueness
        return hits * 2 + (uniq / max(total, 1)) * 10

    if role == "name":
        # long-ish, unique, not urls, not addresses-heavy
        url_cnt = sum(looks_like_url(v) for v in values)
        addr_mark = sum(("ул" in v or "просп" in v or "дом" in v or "г." in v or "проезд" in v) for v in low)
        # name likes uniqueness and moderate/long length
        return (uniq / max(total, 1)) * 20 + avg_len * 0.12 - url_cnt * 10 - addr_mark * 0.3

    if role == "sector":
        # few categories, typical sector words
        sector_words = ["здравоохран", "образован", "культур", "спорт", "соц", "дорог", "жкх", "благоустр", "транспорт"]
        word_hits = sum(any(w in v for w in sector_words) for v in low)
        # prefer not too many uniques
        uniq_ratio = uniq / max(total, 1)
        return word_hits * 2 + (1 - uniq_ratio) * 15

    if role == "district":
        dist_words = ["район", "р-н", "р-он", "курск", "г.", "посел", "село", "дерев", "округ", "мо "]
        word_hits = sum(any(w in v for w in dist_words) for v in low)
        uniq_ratio = uniq / max(total, 1)
        # district usually has limited uniq and words "район/Курск"
        return word_hits * 2 + (1 - uniq_ratio) * 10 + (avg_len < 40) * 2

    if role == "address":
        addr_words = ["ул", "улица", "просп", "проспект", "дом", "д.", "корп", "к.", "проезд", "переул", "г.", "с.", "пос."]
        word_hits = sum(any(w in v for w in addr_words) for v in low)
        return word_hits * 2 + avg_len * 0.05

    if role == "responsible":
        # "Иванов И.И." or "Иванова Е.Н.; Юдина А.А."
        fio_pat = re.compile(r"[А-ЯЁA-Z][а-яёa-z-]+.*\b[А-ЯЁA-Z]\.\s*[А-ЯЁA-Z]\.")
        hits = sum(bool(fio_pat.search(v)) for v in values)
        return hits * 2 + (avg_len < 80) * 1

    if role == "status":
        # short labels, repeating
        uniq_ratio = uniq / max(total, 1)
        return (1 - uniq_ratio) * 12 + (avg_len < 35) * 2

    if role == "works":
        works_words = ["да", "нет", "ведутся", "не ведутся", "выполня", "строит", "работ", "подряд"]
        hits = sum(any(w in v for w in works_words) for v in low)
        uniq_ratio = uniq / max(total, 1)
        return hits * 2 + (1 - uniq_ratio) * 8

    return -1.0


def detect_columns(df: pd.DataFrame) -> dict:
    """Detect columns based on content, not only headers."""
    # normalize headers a bit
    df = df.copy()
    df.columns = [str(c).replace("\ufeff", "").strip() for c in df.columns]

    cols = list(df.columns)

    # 1) URLs: keep your explicit ones if exist
    card_url = "card_url" if "card_url" in cols else None
    folder_url = "folder_url" if "folder_url" in cols else None

    # otherwise detect
    if not card_url:
        best = (None, -1.0)
        for c in cols:
            vals = col_sample_strings(df, c)
            sc = score_column_for_role(vals, "url_card")
            if sc > best[1]:
                best = (c, sc)
        card_url = best[0] if best[1] >= 2 else None

    if not folder_url:
        best = (None, -1.0)
        for c in cols:
            vals = col_sample_strings(df, c)
            sc = score_column_for_role(vals, "url_folder")
            if sc > best[1]:
                best = (c, sc)
        folder_url = best[0] if best[1] >= 2 else None

    # 2) id: keep explicit "id" if exists
    id_col = "id" if "id" in cols else None
    if not id_col:
        best = (None, -1.0)
        for c in cols:
            vals = col_sample_strings(df, c)
            sc = score_column_for_role(vals, "id")
            if sc > best[1]:
                best = (c, sc)
        id_col = best[0] if best[1] >= 3 else None

    # candidate pool excluding url columns
    exclude = {card_url, folder_url}
    pool = [c for c in cols if c not in exclude]

    # 3) name
    best = (None, -1.0)
    for c in pool:
        vals = col_sample_strings(df, c)
        sc = score_column_for_role(vals, "name")
        if sc > best[1]:
            best = (c, sc)
    name_col = best[0]

    # 4) district
    best = (None, -1.0)
    for c in pool:
        if c == name_col:
            continue
        vals = col_sample_strings(df, c)
        sc = score_column_for_role(vals, "district")
        if sc > best[1]:
            best = (c, sc)
    district_col = best[0] if best[1] >= 2 else None

    # 5) sector
    best = (None, -1.0)
    for c in pool:
        if c in {name_col, district_col}:
            continue
        vals = col_sample_strings(df, c)
        sc = score_column_for_role(vals, "sector")
        if sc > best[1]:
            best = (c, sc)
    sector_col = best[0] if best[1] >= 2 else None

    # 6) address
    best = (None, -1.0)
    for c in pool:
        if c in {name_col, district_col, sector_col}:
            continue
        vals = col_sample_strings(df, c)
        sc = score_column_for_role(vals, "address")
        if sc > best[1]:
            best = (c, sc)
    address_col = best[0] if best[1] >= 2 else None

    # 7) responsible
    best = (None, -1.0)
    for c in pool:
        if c in {name_col, district_col, sector_col, address_col}:
            continue
        vals = col_sample_strings(df, c)
        sc = score_column_for_role(vals, "responsible")
        if sc > best[1]:
            best = (c, sc)
    resp_col = best[0] if best[1] >= 2 else None

    # 8) status
    best = (None, -1.0)
    for c in pool:
        if c in {name_col, district_col, sector_col, address_col, resp_col}:
            continue
        vals = col_sample_strings(df, c)
        sc = score_column_for_role(vals, "status")
        if sc > best[1]:
            best = (c, sc)
    status_col = best[0] if best[1] >= 1.5 else None

    # 9) works
    best = (None, -1.0)
    for c in pool:
        if c in {name_col, district_col, sector_col, address_col, resp_col, status_col}:
            continue
        vals = col_sample_strings(df, c)
        sc = score_column_for_role(vals, "works")
        if sc > best[1]:
            best = (c, sc)
    works_col = best[0] if best[1] >= 1.5 else None

    return {
        "name": name_col,
        "sector": sector_col,
        "district": district_col,
        "address": address_col,
        "responsible": resp_col,
        "status": status_col,
        "works": works_col,
        "card_url": card_url,
        "folder_url": folder_url,
        "id": id_col,
    }


# =========================
# PAGE
# =========================
st.set_page_config(
    page_title=f"{APP_SUBTITLE} — Курская область",
    page_icon="🏛️",
    layout="wide",
)

GERB_B64 = read_image_b64(ASSET_GERB)

# =========================
# CSS (шапку не ломаем; мобильную поддерживаем)
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

/* скрыть меню/футер (как было) */
footer {visibility: hidden;}
#MainMenu {visibility: hidden;}
header {visibility: hidden;}

/* ===== HERO (как у тебя сейчас) ===== */
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
    df_ = pd.read_csv(url)
    df_.columns = [str(c).replace("\ufeff", "").strip() for c in df_.columns]
    return df_


df = load_data(CSV_URL)
cols = detect_columns(df)

# debug only if ?debug=1
debug = st.experimental_get_query_params().get("debug", ["0"])[0] == "1"
if debug:
    with st.sidebar:
        st.subheader("Диагностика (включена через ?debug=1)")
        st.code("\n".join([f"{k}: {v}" for k, v in cols.items()]))
        with st.expander("Все столбцы df.columns"):
            st.write(list(df.columns))


# =========================
# HERO (НЕ МЕНЯЕМ)
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
# FILTERS (key у каждого виджета!)
# =========================
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown('<div class="filter-label">🏷️ Отрасль</div>', unsafe_allow_html=True)
    sectors = ["Все"]
    if cols["sector"]:
        sectors += sorted(
            [s for s in df[cols["sector"]].dropna().astype(str).str.strip().unique() if s and s.lower() != "nan"],
            key=lambda x: x.lower(),
        )
    sector_sel = st.selectbox("Отрасль", sectors, index=0, key="sector_sel", label_visibility="collapsed")

with c2:
    st.markdown('<div class="filter-label">📍 Район</div>', unsafe_allow_html=True)
    districts = ["Все"]
    if cols["district"]:
        raw = df[cols["district"]].dropna().astype(str).str.strip().tolist()
        districts += ordered_districts(raw)
    district_sel = st.selectbox("Район", districts, index=0, key="district_sel", label_visibility="collapsed")

with c3:
    st.markdown('<div class="filter-label">📌 Статус</div>', unsafe_allow_html=True)
    statuses = ["Все"]
    if cols["status"]:
        statuses += sorted(
            [s for s in df[cols["status"]].dropna().astype(str).str.strip().unique() if s and s.lower() != "nan"],
            key=lambda x: x.lower(),
        )
    status_sel = st.selectbox("Статус", statuses, index=0, key="status_sel", label_visibility="collapsed")

st.markdown('<div class="filter-label">🔎 Поиск (наименование / адрес / ответственный / id)</div>', unsafe_allow_html=True)
q = st.text_input("Поиск", value="", key="search_q", label_visibility="collapsed").strip().lower()


# =========================
# APPLY FILTERS
# =========================
view = df.copy()

if cols["sector"] and sector_sel != "Все":
    view = view[view[cols["sector"]].astype(str).str.strip() == sector_sel]

if cols["district"] and district_sel != "Все":
    view = view[view[cols["district"]].astype(str).str.strip() == district_sel]

if cols["status"] and status_sel != "Все":
    view = view[view[cols["status"]].astype(str).str.strip() == status_sel]

if q:
    search_cols = [c for c in [cols["name"], cols["address"], cols["responsible"], cols["id"]] if c]
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
    name = esc(row[cols["name"]]) if cols["name"] else "Объект"

    sector = esc(row[cols["sector"]]) if cols["sector"] else "—"
    district = esc(row[cols["district"]]) if cols["district"] else "—"
    address = esc(row[cols["address"]]) if cols["address"] else "—"
    resp = esc(row[cols["responsible"]]) if cols["responsible"] else "—"
    status = esc(row[cols["status"]]) if cols["status"] else "—"
    works = esc(row[cols["works"]]) if cols["works"] else "—"

    card_url = norm(row[cols["card_url"]]) if cols["card_url"] else ""
    folder_url = norm(row[cols["folder_url"]]) if cols["folder_url"] else ""

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
            st.button("📄 Открыть карточку", disabled=True, use_container_width=True)
    with b2:
        if folder_url:
            st.link_button("📁 Открыть папку", folder_url, use_container_width=True)
        else:
            st.button("📁 Открыть папку", disabled=True, use_container_width=True)


left, right = st.columns(2)

for i, (_, r) in enumerate(view.iterrows()):
    target = left if i % 2 == 0 else right
    with target:
        render_card(r)
        st.write("")
