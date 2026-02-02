import base64
import os
import re
from io import BytesIO
from typing import Optional, Dict, List

import pandas as pd
import streamlit as st


# =========================
# CONFIG
# =========================
st.set_page_config(
    page_title="Реестр объектов — Курская область",
    page_icon="🏛️",
    layout="wide",
)

APP_TITLE = "Министерство восстановления, развития приграничья и строительства Курской области"
APP_SUBTITLE = "Реестр объектов"
APP_DESC = "Единый список объектов 2025–2028 с быстрыми фильтрами и переходом в карточку/папку."
ASSET_GERB = os.path.join("assets", "gerb.png")


# =========================
# HELPERS
# =========================
def img_to_base64(path: str) -> Optional[str]:
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return None


def norm(s: str) -> str:
    """Normalize column names for robust matching."""
    s = str(s).strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = s.replace("ё", "е")
    return s


def pick_col(cols: List[str], *needles: List[str]) -> Optional[str]:
    """
    Find the best matching column among `cols` by checking if all tokens from any
    needle-set exist in the normalized column name.
    needles: list of candidate token lists (synonyms).
    """
    ncols = {c: norm(c) for c in cols}

    for token_set in needles:
        token_set = [norm(t) for t in token_set]
        for c, nc in ncols.items():
            ok = True
            for t in token_set:
                if t not in nc:
                    ok = False
                    break
            if ok:
                return c
    return None


def safe_str(x) -> str:
    if x is None:
        return "—"
    if isinstance(x, float) and pd.isna(x):
        return "—"
    s = str(x).strip()
    return s if s else "—"


def is_blank(x) -> bool:
    if x is None:
        return True
    if isinstance(x, float) and pd.isna(x):
        return True
    s = str(x).strip()
    return s == "" or s.lower() == "nan"


def css_inject():
    st.markdown(
        """
<style>
/* ===== Hide Streamlit footer/menu (watermark) ===== */
footer {visibility: hidden;}
#MainMenu {visibility: hidden;}
header {visibility: hidden;}

/* ===== Page background ===== */
.stApp {
  background: #f5f7fb;
}

/* ===== Hero header ===== */
.hero-wrap{
  width: 100%;
  max-width: 1400px;
  margin: 18px auto 14px auto;
  border-radius: 18px;
  padding: 18px 18px;
  background: linear-gradient(135deg, #0d2d59 0%, #123b75 45%, #1a4a8a 100%);
  box-shadow: 0 14px 28px rgba(7,18,40,0.22);
  position: relative;
  overflow: hidden;
}
.hero-wrap:before{
  content:"";
  position:absolute;
  inset:-40px -120px auto auto;
  width: 520px;
  height: 260px;
  background: rgba(255,255,255,0.06);
  transform: rotate(-18deg);
  border-radius: 70px;
}
.hero-row{
  position: relative;
  display: flex;
  gap: 16px;
  align-items: center;
}
.hero-logo{
  width: 84px;
  height: 84px;
  min-width: 84px;
  border-radius: 14px;
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.10);
  display:flex;
  align-items:center;
  justify-content:center;
}
.hero-logo img{
  width: 64px;
  height: 64px;
  object-fit: contain;
  display:block;
  filter: drop-shadow(0 6px 12px rgba(0,0,0,0.25));
}
.hero-titles{
  color: #fff;
  min-width: 0;
}
.hero-ministry{
  font-size: 26px;
  font-weight: 800;
  line-height: 1.15;
  margin: 0 0 6px 0;
  letter-spacing: 0.2px;
  /* важно: не ломаем строку на ПК */
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.hero-app{
  font-size: 18px;
  font-weight: 700;
  opacity: 0.95;
  margin: 0 0 6px 0;
}
.hero-desc{
  font-size: 13px;
  opacity: 0.86;
  margin: 0 0 10px 0;
}
.hero-pill{
  display:inline-flex;
  align-items:center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(255,255,255,0.12);
  border: 1px solid rgba(255,255,255,0.14);
  font-size: 12px;
  opacity: 0.95;
}

/* ===== Filters ===== */
.filters-wrap{
  width: 100%;
  max-width: 1400px;
  margin: 0 auto;
}
.small-note{
  color: rgba(40,45,60,0.65);
  font-size: 12px;
}

/* ===== Cards ===== */
.card{
  border-radius: 16px;
  border: 1px solid rgba(20,26,40,0.08);
  background: #fff;
  padding: 14px 14px 12px 14px;
  box-shadow: 0 10px 20px rgba(10,18,40,0.06);
}
.card-title{
  font-size: 15px;
  font-weight: 800;
  margin: 0 0 10px 0;
  color: #101828;
}
.meta{
  border-radius: 12px;
  background: #f4f6fa;
  border: 1px solid rgba(20,26,40,0.06);
  padding: 10px 10px;
}
.meta-row{
  display:flex;
  gap:8px;
  align-items:flex-start;
  margin: 4px 0;
  color: #1f2937;
  font-size: 12.5px;
}
.meta-ico{
  width: 18px;
  text-align:center;
  opacity: 0.9;
}
.chips{
  margin-top: 10px;
  display:flex;
  gap:10px;
  flex-wrap: wrap;
}
.chip{
  display:inline-flex;
  gap:6px;
  align-items:center;
  padding: 6px 10px;
  border-radius: 999px;
  background: #eef4ff;
  border: 1px solid rgba(25, 92, 200, 0.16);
  font-size: 12px;
}
.chip2{
  background:#f4f6fa;
  border:1px solid rgba(20,26,40,0.08);
}
.linkbar{
  margin-top: 10px;
  display:flex;
  gap:10px;
}
.linkbar a{
  flex: 1;
  text-decoration:none !important;
}
.linkbtn{
  width: 100%;
  display:inline-flex;
  gap:8px;
  justify-content:center;
  align-items:center;
  padding: 10px 12px;
  border-radius: 12px;
  background: #ffffff;
  border: 1px solid rgba(20,26,40,0.14);
  color: #111827;
  font-weight: 600;
}
.linkbtn:hover{
  background: #f8fafc;
}

/* ===== Mobile tweaks ===== */
@media (max-width: 820px){
  .hero-ministry{
    font-size: 18px;
    white-space: normal;   /* на телефоне переносим красиво */
  }
  .hero-row{
    align-items: flex-start;
  }
  .hero-logo{
    width: 74px;
    height: 74px;
    min-width: 74px;
  }
  .hero-logo img{
    width: 56px;
    height: 56px;
  }
}
</style>
""",
        unsafe_allow_html=True,
    )


def render_hero():
    b64 = img_to_base64(ASSET_GERB)
    if b64:
        gerb_html = f'<img src="data:image/png;base64,{b64}" alt="Герб"/>'
    else:
        gerb_html = "🏛️"

    st.markdown(
        f"""
<div class="hero-wrap">
  <div class="hero-row">
    <div class="hero-logo">{gerb_html}</div>
    <div class="hero-titles">
      <div class="hero-ministry">{APP_TITLE}</div>
      <div class="hero-app">{APP_SUBTITLE}</div>
      <div class="hero-desc">{APP_DESC}</div>
      <div class="hero-pill">📄 Источник данных: Google Sheets (CSV)</div>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=300, show_spinner=False)
def load_data() -> pd.DataFrame:
    """
    Loads data from:
    1) st.secrets["CSV_URL"] (preferred)
    2) Any local .xlsx file in repo root (fallback)
    """
    # --- 1) CSV from secrets ---
    csv_url = None
    try:
        csv_url = st.secrets.get("CSV_URL", None)
    except Exception:
        csv_url = None

    if csv_url:
        try:
            df = pd.read_csv(csv_url)
            if isinstance(df, pd.DataFrame) and len(df) > 0:
                return df
        except Exception:
            pass

    # --- 2) local xlsx fallback ---
    xlsx_candidates = [f for f in os.listdir(".") if f.lower().endswith(".xlsx")]
    if xlsx_candidates:
        try:
            df = pd.read_excel(xlsx_candidates[0])
            if isinstance(df, pd.DataFrame) and len(df) > 0:
                return df
        except Exception:
            pass

    return pd.DataFrame()


def build_schema(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    cols = list(df.columns)

    # Русские варианты в вашем реестре (по скринам)
    col_id = pick_col(cols, ["id"], ["ид"], ["код"], ["шифр"])
    col_sector = pick_col(cols, ["отрасль"], ["сфера"])
    col_district = pick_col(cols, ["район"], ["муницип"], ["мо"], ["округ"])
    col_name = pick_col(cols, ["наименование", "объекта"], ["наименование"], ["объект"])
    col_address = pick_col(cols, ["адрес"], ["место"])
    col_responsible = pick_col(cols, ["ответственный"], ["куратор"], ["ответств"])
    col_status = pick_col(cols, ["статус"])
    col_works = pick_col(cols, ["работы"], ["этап"], ["стадия"])
    col_card_url = pick_col(cols, ["ссылка", "карточ"], ["карточка"], ["card_url"])
    col_folder_url = pick_col(cols, ["ссылка", "папк"], ["папка"], ["folder_url"])

    return {
        "id": col_id,
        "sector": col_sector,
        "district": col_district,
        "name": col_name,
        "address": col_address,
        "responsible": col_responsible,
        "status": col_status,
        "works": col_works,
        "card_url": col_card_url,
        "folder_url": col_folder_url,
    }


def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    schema = build_schema(df)
    out = pd.DataFrame()

    # Берём колонки если есть, иначе создаём пустые
    for k, c in schema.items():
        if c and c in df.columns:
            out[k] = df[c]
        else:
            out[k] = ""

    # Нормализация строк
    for c in out.columns:
        out[c] = out[c].astype(str)

    # Чистим "nan"
    out = out.replace({"nan": "", "None": ""})

    # Если id пустой — попробуем сгенерить стабильный
    if out["id"].str.strip().eq("").all():
        out["id"] = [f"OBJ-{i+1:03d}" for i in range(len(out))]

    # Если name пустой — подставим id (но это крайний случай)
    out["name"] = out["name"].apply(lambda x: x if str(x).strip() else "")
    out.loc[out["name"].str.strip().eq(""), "name"] = out["id"]

    return out


def filter_df(df: pd.DataFrame, sector_sel: str, district_sel: str, status_sel: str, q: str) -> pd.DataFrame:
    dff = df.copy()

    if sector_sel != "Все":
        dff = dff[dff["sector"].fillna("").astype(str).str.strip() == sector_sel]

    if district_sel != "Все":
        dff = dff[dff["district"].fillna("").astype(str).str.strip() == district_sel]

    if status_sel != "Все":
        dff = dff[dff["status"].fillna("").astype(str).str.strip() == status_sel]

    q = (q or "").strip().lower()
    if q:
        def row_hit(r):
            blob = " ".join([
                safe_str(r.get("id")),
                safe_str(r.get("name")),
                safe_str(r.get("sector")),
                safe_str(r.get("district")),
                safe_str(r.get("address")),
                safe_str(r.get("responsible")),
            ]).lower()
            return q in blob

        dff = dff[dff.apply(row_hit, axis=1)]

    return dff


def render_card(row: pd.Series):
    title = safe_str(row.get("name"))
    sector = safe_str(row.get("sector"))
    district = safe_str(row.get("district"))
    address = safe_str(row.get("address"))
    responsible = safe_str(row.get("responsible"))
    status = safe_str(row.get("status"))
    works = safe_str(row.get("works"))
    card_url = safe_str(row.get("card_url"))
    folder_url = safe_str(row.get("folder_url"))

    # если status/works пустые — показываем тире, а не "nan"
    if status.lower() == "nan" or status == "":
        status = "—"
    if works.lower() == "nan" or works == "":
        works = "—"

    st.markdown(
        f"""
<div class="card">
  <div class="card-title">{title}</div>
  <div class="meta">
    <div class="meta-row"><span class="meta-ico">🏷️</span><span><b>Отрасль:</b> {sector}</span></div>
    <div class="meta-row"><span class="meta-ico">📍</span><span><b>Район:</b> {district}</span></div>
    <div class="meta-row"><span class="meta-ico">🗺️</span><span><b>Адрес:</b> {address}</span></div>
    <div class="meta-row"><span class="meta-ico">👤</span><span><b>Ответственный:</b> {responsible}</span></div>
  </div>

  <div class="chips">
    <div class="chip">📌 <b>Статус:</b> {status}</div>
    <div class="chip chip2">🛠️ <b>Работы:</b> {works}</div>
  </div>
""",
        unsafe_allow_html=True,
    )

    # Кнопки — только если ссылки реально есть
    link_parts = []
    if card_url and card_url != "—" and card_url.lower() != "nan" and card_url.startswith("http"):
        link_parts.append(("🧾 Открыть карточку", card_url))
    if folder_url and folder_url != "—" and folder_url.lower() != "nan" and folder_url.startswith("http"):
        link_parts.append(("📁 Открыть папку", folder_url))

    if link_parts:
        btns_html = '<div class="linkbar">'
        for text, url in link_parts:
            btns_html += f'<a href="{url}" target="_blank" rel="noopener"><div class="linkbtn">{text}</div></a>'
        btns_html += "</div>"
        st.markdown(btns_html, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


# =========================
# UI
# =========================
css_inject()
render_hero()

raw = load_data()
if raw is None or raw.empty:
    st.error("Данные не загрузились (реестр пустой). Проверьте CSV_URL в Secrets или наличие .xlsx в репозитории.")
    st.stop()

df = normalize_df(raw)

# ===== FILTERS =====
st.markdown('<div class="filters-wrap">', unsafe_allow_html=True)

# Варианты фильтров
sectors = sorted([s for s in df["sector"].astype(str).str.strip().unique().tolist() if s])
districts = sorted([s for s in df["district"].astype(str).str.strip().unique().tolist() if s])
statuses = sorted([s for s in df["status"].astype(str).str.strip().unique().tolist() if s])

c1, c2, c3 = st.columns([1, 1, 1])

with c1:
    sector_sel = st.selectbox("🏷️ Отрасль", ["Все"] + sectors, index=0, key="sector_sel")
with c2:
    district_sel = st.selectbox("📍 Район", ["Все"] + districts, index=0, key="district_sel")
with c3:
    status_sel = st.selectbox("📌 Статус", ["Все"] + statuses, index=0, key="status_sel")

q = st.text_input("🔎 Поиск (наименование / адрес / ответственный / id)", value="", key="search_q")

st.markdown('</div>', unsafe_allow_html=True)

# ===== APPLY FILTERS =====
dff = filter_df(df, sector_sel, district_sel, status_sel, q)

st.markdown(f'<div class="small-note">Показано объектов: {len(dff)} из {len(df)}</div>', unsafe_allow_html=True)
st.divider()

# ===== GRID OF CARDS =====
# Streamlit сам адаптирует колонки, но на ПК делаем 2
cols = st.columns(2)
for i, (_, row) in enumerate(dff.iterrows()):
    with cols[i % 2]:
        render_card(row)
