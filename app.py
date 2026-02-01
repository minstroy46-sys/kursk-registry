import base64
import html
from pathlib import Path

import pandas as pd
import streamlit as st


# =========================
# НАСТРОЙКИ
# =========================
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQwA5g3ZuBmZlY3vQMbc7nautnpK7c4ioKtTYU_mTskZb6A6nJ_yeokKIvfbVBFH1jTPpzOgoBMD89n/pub?gid=372714191&single=true&output=csv"
GERB_PATH = Path("assets/gerb.png")

MINISTRY_NAME = "Министерство восстановления, развития приграничья и строительства Курской области"
APP_NAME = "Реестр объектов"
SUBTITLE = "Единый список объектов 2025–2028 с быстрыми фильтрами и переходом в карточку/папку."
DATA_PILL = "Источник данных: Google Sheets (CSV)"


# =========================
# УТИЛИТЫ
# =========================
def b64_image(path: Path) -> str:
    try:
        data = path.read_bytes()
        return "data:image/png;base64," + base64.b64encode(data).decode("utf-8")
    except Exception:
        return ""


def norm_str(x) -> str:
    if x is None:
        return "—"
    try:
        if pd.isna(x):
            return "—"
    except Exception:
        pass
    s = str(x).strip()
    if not s:
        return "—"
    if s.lower() == "nan":
        return "—"
    return s


def esc(x) -> str:
    return html.escape(norm_str(x), quote=True)


def priority_sort_district(values: list[str]) -> list[str]:
    cleaned = [v for v in values if v and v != "—"]
    uniq = sorted(set(cleaned), key=lambda s: s.lower())

    kursk_city_keys = {"г. курск", "город курск", "курск", "г курск"}
    kursk_raion_keys = {"курский", "курский район", "курский р-н", "курский р-он"}

    def is_kursk_city(s: str) -> bool:
        t = s.strip().lower()
        return t in kursk_city_keys or t.startswith("г. курск") or t == "г курск"

    def is_kursk_raion(s: str) -> bool:
        t = s.strip().lower()
        return t in kursk_raion_keys or t.startswith("курский район") or t.startswith("курский")

    kursk_city = [x for x in uniq if is_kursk_city(x)]
    kursk_raion = [x for x in uniq if (not is_kursk_city(x)) and is_kursk_raion(x)]
    rest = [x for x in uniq if (x not in kursk_city) and (x not in kursk_raion)]
    return kursk_city + kursk_raion + rest


@st.cache_data(show_spinner=False, ttl=300)
def load_data(url: str) -> pd.DataFrame:
    df = pd.read_csv(url)
    needed = [
        "sector",
        "district",
        "name",
        "responsible",
        "status",
        "work_flag",
        "address",
        "card_url",
        "folder_url",
        "id",
    ]
    for col in needed:
        if col not in df.columns:
            df[col] = ""

    return df


# =========================
# PAGE
# =========================
st.set_page_config(
    page_title=f"{APP_NAME} — Курская область",
    page_icon="📋",
    layout="wide",
)

gerb_data_uri = b64_image(GERB_PATH)

# =========================
# CSS (Шапка ровная, без "ломаных" кругов; Министерство в одну строку)
# =========================
st.markdown(
    """
<style>
/* Главное: НЕ сжимаем слишком сильно, чтобы заголовок помещался в одну строку */
.block-container {
    padding-top: 1.2rem;
    padding-bottom: 2rem;
    max-width: 1500px; /* было 1200 */
}

:root {
  --hero-bg1: #233a6a;
  --hero-bg2: #142a4e;
  --hero-line: rgba(255,255,255,0.10);
  --card-muted: rgba(0,0,0,0.045);
  --border: rgba(0,0,0,0.08);
}

.hero {
  position: relative;
  overflow: hidden;
  border-radius: 18px;
  padding: 22px 22px;
  background: linear-gradient(135deg, var(--hero-bg1), var(--hero-bg2));
  box-shadow: 0 18px 35px rgba(0,0,0,0.18);
  border: 1px solid rgba(255,255,255,0.10);
  margin-bottom: 16px;
}

/* ОДНА мягкая диагональ без "ломаных" элементов */
.hero::after{
  content:"";
  position:absolute;
  inset:-40px -140px -40px auto;
  width: 520px;
  transform: skewX(-18deg);
  background: linear-gradient(180deg, rgba(255,255,255,0.10), rgba(255,255,255,0.02));
  opacity: 0.55;
  border-radius: 40px;
}

/* Внутренности */
.hero-inner {
  position: relative;
  display: grid;
  grid-template-columns: 86px 1fr;
  gap: 16px;
  align-items: center;
}

.hero-logo {
  width: 76px;
  height: 76px;
  border-radius: 14px;
  background: rgba(255,255,255,0.10);
  display:flex;
  align-items:center;
  justify-content:center;
  border: 1px solid rgba(255,255,255,0.14);
  box-shadow: inset 0 0 0 1px rgba(0,0,0,0.10);
}

.hero-logo img {
  width: 56px;
  height: 56px;
  object-fit: contain;
  filter: drop-shadow(0 6px 10px rgba(0,0,0,0.25));
}

/* Министерство — ОДНА строка на всю ширину */
.hero-ministry {
  color: rgba(255,255,255,0.96);
  font-weight: 900;
  letter-spacing: 0.2px;
  margin: 0 0 6px 0;

  white-space: nowrap;     /* одна строка */
  overflow: hidden;
  text-overflow: ellipsis; /* если экран узкий — аккуратно обрежет */
  font-size: clamp(20px, 1.55vw, 28px); /* адаптивно */
  line-height: 1.1;
}

/* Реестр — меньше чем Министерство */
.hero-app {
  color: rgba(255,255,255,0.98);
  font-size: clamp(18px, 1.3vw, 22px);
  font-weight: 800;
  margin: 0 0 8px 0;
}

.hero-sub {
  color: rgba(255,255,255,0.85);
  font-size: 13px;
  margin: 0 0 10px 0;
}

.hero-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(255,255,255,0.10);
  border: 1px solid rgba(255,255,255,0.16);
  color: rgba(255,255,255,0.92);
  font-size: 12px;
  width: fit-content;
}

.filters-wrap {
  padding: 10px 14px;
  border-radius: 14px;
  border: 1px solid var(--border);
  background: rgba(0,0,0,0.015);
  margin-bottom: 10px;
}

.card {
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 14px 14px 12px 14px;
  background: white;
  box-shadow: 0 6px 18px rgba(0,0,0,0.06);
}

.card h3 {
  font-size: 16px;
  margin: 0 0 10px 0;
}

.meta {
  border: 1px solid var(--border);
  background: var(--card-muted);
  border-radius: 12px;
  padding: 10px 10px;
  margin-bottom: 10px;
}

.meta-row {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  margin: 4px 0;
  color: rgba(0,0,0,0.76);
  font-size: 12.8px;
}

.meta-ico {
  width: 18px;
  text-align: center;
  opacity: 0.95;
}

.chips {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin: 6px 0 10px 0;
}

.chip {
  display:inline-flex;
  align-items:center;
  gap: 6px;
  padding: 5px 10px;
  border-radius: 999px;
  font-size: 12px;
  border: 1px solid rgba(0,0,0,0.10);
  background: rgba(0,0,0,0.02);
}

.small-muted {
  color: rgba(0,0,0,0.55);
  font-size: 12px;
}
</style>
""",
    unsafe_allow_html=True,
)

# =========================
# HEADER
# =========================
logo_html = (
    f'<div class="hero-logo"><img src="{gerb_data_uri}" alt="Герб" /></div>'
    if gerb_data_uri
    else '<div class="hero-logo">🏛️</div>'
)

st.markdown(
    f"""
<div class="hero">
  <div class="hero-inner">
    {logo_html}
    <div>
      <div class="hero-ministry">{html.escape(MINISTRY_NAME)}</div>
      <div class="hero-app">{html.escape(APP_NAME)}</div>
      <div class="hero-sub">{html.escape(SUBTITLE)}</div>
      <div class="hero-pill">📄 {html.escape(DATA_PILL)}</div>
    </div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# =========================
# DATA
# =========================
df = load_data(CSV_URL)

sector_vals = sorted(
    set([norm_str(x) for x in df["sector"].tolist() if norm_str(x) != "—"]),
    key=lambda s: s.lower(),
)
district_vals = priority_sort_district([norm_str(x) for x in df["district"].tolist()])
status_vals = sorted(
    set([norm_str(x) for x in df["status"].tolist() if norm_str(x) != "—"]),
    key=lambda s: s.lower(),
)

# =========================
# FILTERS
# =========================
st.markdown('<div class="filters-wrap">', unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)

with c1:
    sector = st.selectbox("🏷️ Отрасль", ["Все"] + sector_vals, index=0)
with c2:
    district = st.selectbox("📍 Район", ["Все"] + district_vals, index=0)
with c3:
    status = st.selectbox("📌 Статус", ["Все"] + status_vals, index=0)

q = st.text_input("🔎 Поиск (наименование / адрес / ответственный / id)", value="").strip().lower()
st.markdown("</div>", unsafe_allow_html=True)

f = df.copy()
if sector != "Все":
    f = f[f["sector"].astype(str).str.strip() == sector]
if district != "Все":
    f = f[f["district"].astype(str).str.strip() == district]
if status != "Все":
    f = f[f["status"].astype(str).str.strip() == status]

if q:
    def row_match(row) -> bool:
        hay = " ".join(
            [
                str(row.get("id", "")),
                str(row.get("name", "")),
                str(row.get("address", "")),
                str(row.get("responsible", "")),
            ]
        ).lower()
        return q in hay

    f = f[f.apply(row_match, axis=1)]

st.markdown(f'<div class="small-muted">Показано объектов: {len(f)} из {len(df)}</div>', unsafe_allow_html=True)
st.divider()


# =========================
# CARD RENDER
# =========================
def render_card(row: pd.Series):
    name = esc(row.get("name"))
    sector_v = esc(row.get("sector"))
    district_v = esc(row.get("district"))
    address_v = esc(row.get("address"))
    responsible_v = esc(row.get("responsible"))

    status_v = norm_str(row.get("status"))
    work_v = norm_str(row.get("work_flag"))

    card_url = norm_str(row.get("card_url"))
    folder_url = norm_str(row.get("folder_url"))

    status_chip = html.escape(status_v if status_v != "—" else "—")
    work_chip = html.escape(work_v if work_v != "—" else "—")

    st.markdown(
        f"""
<div class="card">
  <h3>{name}</h3>

  <div class="meta">
    <div class="meta-row"><span class="meta-ico">🏷️</span><span><b>Отрасль:</b> {sector_v}</span></div>
    <div class="meta-row"><span class="meta-ico">📍</span><span><b>Район:</b> {district_v}</span></div>
    <div class="meta-row"><span class="meta-ico">🗺️</span><span><b>Адрес:</b> {address_v}</span></div>
    <div class="meta-row"><span class="meta-ico">👤</span><span><b>Ответственный:</b> {responsible_v}</span></div>
  </div>

  <div class="chips">
    <div class="chip">📌 <b>Статус:</b> {status_chip}</div>
    <div class="chip">🛠️ <b>Работы:</b> {work_chip}</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    b1, b2 = st.columns(2)
    with b1:
        if card_url != "—" and card_url.startswith("http"):
            st.link_button("📄 Открыть карточку", card_url, use_container_width=True)
        else:
            st.button("📄 Открыть карточку", use_container_width=True, disabled=True)
    with b2:
        if folder_url != "—" and folder_url.startswith("http"):
            st.link_button("📁 Открыть папку", folder_url, use_container_width=True)
        else:
            st.button("📁 Открыть папку", use_container_width=True, disabled=True)


# =========================
# GRID
# =========================
rows = f.to_dict(orient="records")
for i in range(0, len(rows), 2):
    col_left, col_right = st.columns(2)
    with col_left:
        render_card(pd.Series(rows[i]))
    with col_right:
        if i + 1 < len(rows):
            render_card(pd.Series(rows[i + 1]))
        else:
            st.empty()
