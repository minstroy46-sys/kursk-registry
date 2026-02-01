import base64
from pathlib import Path

import pandas as pd
import streamlit as st


# ----------------------------
# НАСТРОЙКИ
# ----------------------------
st.set_page_config(
    page_title="Министерство восстановления, развития приграничья и строительства Курской области",
    page_icon="🏛️",
    layout="wide",
)

CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQwA5g3ZuBmZlY3vQMbc7nautnpK7c4ioKtTYU_mTskZb6A6nJ_yeokKIvfbVBFH1jTPpzOgoBMD89n/pub?gid=372714191&single=true&output=csv"

GERB_PATH = Path("assets/gerb.png")  # положи герб сюда в репо


# ----------------------------
# ВСПОМОГАТЕЛЬНОЕ
# ----------------------------
def _b64_image(path: Path) -> str | None:
    if not path.exists():
        return None
    data = path.read_bytes()
    return base64.b64encode(data).decode("utf-8")


def _clean_str(x) -> str:
    if pd.isna(x):
        return ""
    return str(x).strip()


def _district_sort_key(d: str):
    """Сортировка районов: г. Курск -> Курский район -> далее по алфавиту."""
    s = (d or "").strip().lower()

    # 1) Курск первым
    if s in {"г. курск", "курск", "город курск", "г курск"}:
        return (0, "курск")

    # 2) Курский район вторым
    if "курск" in s and "район" in s:
        return (1, "курский район")

    # 3) остальные
    return (2, s)


@st.cache_data(ttl=300)
def load_data(url: str) -> pd.DataFrame:
    df = pd.read_csv(url)

    # нормализуем ожидаемые колонки (как у тебя в CSV)
    # id, sector, district, name, responsible, status, work_flag, address, card_url, folder_url
    for col in [
        "id",
        "sector",
        "district",
        "name",
        "responsible",
        "status",
        "work_flag",
        "address",
        "card_url",
        "folder_url",
    ]:
        if col not in df.columns:
            df[col] = ""

    # чистим строки
    for col in df.columns:
        df[col] = df[col].map(_clean_str)

    # красивее статус/работы
    df["status"] = df["status"].replace({"nan": "", "None": ""})
    df["work_flag"] = df["work_flag"].replace({"nan": "", "None": ""})

    return df


def pill(text: str, tone: str = "neutral") -> str:
    # tone: neutral | ok | warn | bad
    colors = {
        "neutral": ("rgba(37, 99, 235, 0.08)", "rgba(37, 99, 235, 0.18)", "#0f172a"),
        "ok": ("rgba(16, 185, 129, 0.12)", "rgba(16, 185, 129, 0.25)", "#064e3b"),
        "warn": ("rgba(245, 158, 11, 0.14)", "rgba(245, 158, 11, 0.25)", "#78350f"),
        "bad": ("rgba(239, 68, 68, 0.14)", "rgba(239, 68, 68, 0.28)", "#7f1d1d"),
    }
    bg, border, fg = colors.get(tone, colors["neutral"])
    return f"""
    <span class="pill" style="background:{bg};border:1px solid {border};color:{fg};">
      {text}
    </span>
    """


# ----------------------------
# СТИЛИ
# ----------------------------
gerb_b64 = _b64_image(GERB_PATH)

st.markdown(
    f"""
<style>
/* Убираем "обрезанность": делаем контейнер шире и нормальные отступы */
[data-testid="stAppViewContainer"] {{
  background: #f6f8fc;
}}
section.main > div.block-container {{
  padding-top: 22px;
  padding-bottom: 40px;
  max-width: 1400px;  /* можно 1600 если хочешь еще шире */
}}

/* КРАСИВАЯ ШАПКА */
.hero {{
  width: 100%;
  background: linear-gradient(180deg, #2f4b8a 0%, #263e73 100%);
  border-radius: 18px;
  padding: 22px 26px;
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.14);
  border: 1px solid rgba(255,255,255,0.10);
  margin-bottom: 18px;
}}
.hero-inner {{
  display: flex;
  align-items: center;
  gap: 18px;
}}
.hero-crest {{
  width: 84px;
  height: 84px;
  border-radius: 16px;
  background: rgba(255,255,255,0.10);
  border: 1px solid rgba(255,255,255,0.16);
  display:flex;
  align-items:center;
  justify-content:center;
  flex: 0 0 auto;
  overflow: hidden;
}}
.hero-crest img {{
  width: 70px;
  height: 70px;
  object-fit: contain;
}}
.hero-text {{
  min-width: 0;
}}
.hero-ministry {{
  font-size: 28px;             /* ГЛАВНЫЙ заголовок */
  line-height: 1.15;
  font-weight: 800;
  color: #ffffff;
  letter-spacing: 0.2px;
  margin: 0 0 6px 0;
}}
.hero-sub {{
  font-size: 22px;             /* Второй заголовок */
  line-height: 1.2;
  font-weight: 700;
  color: rgba(255,255,255,0.92);
  margin: 0 0 10px 0;
}}
.hero-desc {{
  font-size: 13.5px;
  color: rgba(255,255,255,0.78);
  margin: 0;
}}
.badge {{
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding: 7px 10px;
  border-radius: 999px;
  font-size: 12px;
  color: rgba(255,255,255,0.86);
  background: rgba(255,255,255,0.10);
  border: 1px solid rgba(255,255,255,0.14);
}}

/* ФИЛЬТРЫ */
.filter-label {{
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 6px;
}}
.small-muted {{
  color: #64748b;
  font-size: 12.5px;
}}

/* КАРТОЧКИ */
.card {{
  background: #ffffff;
  border: 1px solid rgba(15,23,42,0.08);
  border-radius: 16px;
  padding: 16px 16px 14px;
  box-shadow: 0 10px 22px rgba(15,23,42,0.06);
  margin-bottom: 14px;
}}
.card-title {{
  font-size: 16px;
  font-weight: 800;
  color: #0f172a;
  margin: 0 0 10px 0;
}}
.meta {{
  display: grid;
  gap: 6px;
  margin-bottom: 10px;
}}
.meta-row {{
  display:flex;
  align-items: flex-start;
  gap: 8px;
  color:#334155;
  font-size: 13.5px;
}}
.meta-ico {{
  width: 18px;
  flex: 0 0 18px;
  opacity: 0.85;
}}
.pill {{
  display:inline-flex;
  align-items:center;
  padding: 5px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  margin-right: 6px;
  margin-top: 4px;
}}
.hr {{
  height: 1px;
  background: rgba(15,23,42,0.08);
  margin: 12px 0;
}}

</style>
""",
    unsafe_allow_html=True,
)


# ----------------------------
# ШАПКА (HTML)
# ----------------------------
if gerb_b64:
    crest_html = f'<img src="data:image/png;base64,{gerb_b64}" alt="Герб" />'
else:
    crest_html = '<div style="color:rgba(255,255,255,0.85);font-weight:800;">🏛️</div>'

st.markdown(
    f"""
<div class="hero">
  <div class="hero-inner">
    <div class="hero-crest">
      {crest_html}
    </div>
    <div class="hero-text">
      <div class="hero-ministry">Министерство восстановления, развития приграничья и строительства Курской области</div>
      <div class="hero-sub">Реестр объектов</div>
      <p class="hero-desc">Единый список объектов 2025–2028 с быстрыми фильтрами и переходом в карточку/папку.</p>
      <div class="badge">🗂️ Источник данных: Google Sheets (CSV)</div>
    </div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)


# ----------------------------
# ДАННЫЕ
# ----------------------------
df = load_data(CSV_URL)

# списки для фильтров
sectors = sorted([x for x in df["sector"].unique() if x])
districts = sorted([x for x in df["district"].unique() if x], key=_district_sort_key)
statuses = sorted([x for x in df["status"].unique() if x])

# ----------------------------
# ФИЛЬТРЫ
# ----------------------------
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown('<div class="filter-label">🏷️ Отрасль</div>', unsafe_allow_html=True)
    sector = st.selectbox("Отрасль", ["Все"] + sectors, label_visibility="collapsed")

with c2:
    st.markdown('<div class="filter-label">📍 Район</div>', unsafe_allow_html=True)
    district = st.selectbox("Район", ["Все"] + districts, label_visibility="collapsed")

with c3:
    st.markdown('<div class="filter-label">📌 Статус</div>', unsafe_allow_html=True)
    status = st.selectbox("Статус", ["Все"] + statuses, label_visibility="collapsed")

st.markdown('<div class="filter-label">🔎 Поиск (наименование / адрес / ответственный)</div>', unsafe_allow_html=True)
q = st.text_input("Поиск", "", label_visibility="collapsed").strip().lower()

# применяем фильтры
f = df.copy()

if sector != "Все":
    f = f[f["sector"] == sector]
if district != "Все":
    f = f[f["district"] == district]
if status != "Все":
    f = f[f["status"] == status]
if q:
    mask = (
        f["name"].str.lower().str.contains(q, na=False)
        | f["address"].str.lower().str.contains(q, na=False)
        | f["responsible"].str.lower().str.contains(q, na=False)
    )
    f = f[mask]

st.markdown(f'<div class="small-muted">Показано объектов: <b>{len(f)}</b> из <b>{len(df)}</b></div>', unsafe_allow_html=True)
st.markdown('<div class="hr"></div>', unsafe_allow_html=True)


# ----------------------------
# ВЫВОД КАРТОЧЕК
# ----------------------------
# 2 колонки карточек (красиво и компактно)
left, right = st.columns(2, gap="large")
cols = [left, right]

def status_tone(s: str) -> str:
    s0 = (s or "").lower()
    if not s0:
        return "neutral"
    if "готов" in s0 or "заверш" in s0:
        return "ok"
    if "в работе" in s0 or "стро" in s0:
        return "warn"
    if "проблем" in s0 or "срыв" in s0 or "нет" == s0:
        return "bad"
    return "neutral"


for i, row in enumerate(f.to_dict(orient="records")):
    col = cols[i % 2]

    name = row.get("name", "")
    sector_v = row.get("sector", "")
    district_v = row.get("district", "")
    address = row.get("address", "")
    responsible = row.get("responsible", "")
    status_v = row.get("status", "")
    work_flag = row.get("work_flag", "")

    card_url = row.get("card_url", "")
    folder_url = row.get("folder_url", "")

    # Плашки
    pills_html = ""
    if status_v:
        pills_html += pill(f"📌 {status_v}", status_tone(status_v))
    if work_flag:
        pills_html += pill(f"🛠️ {work_flag}", "neutral")

    with col:
        st.markdown(
            f"""
            <div class="card">
              <div class="card-title">{name}</div>

              <div class="meta">
                <div class="meta-row"><span class="meta-ico">🏷️</span><span><b>Отрасль:</b> {sector_v}</span></div>
                <div class="meta-row"><span class="meta-ico">📍</span><span><b>Район:</b> {district_v}</span></div>
                <div class="meta-row"><span class="meta-ico">🗺️</span><span><b>Адрес:</b> {address}</span></div>
                <div class="meta-row"><span class="meta-ico">👤</span><span><b>Ответственный:</b> {responsible}</span></div>
              </div>

              <div style="margin: 6px 0 12px 0;">{pills_html}</div>
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

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
