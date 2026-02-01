# app.py
# -*- coding: utf-8 -*-

import base64
import html
import os
from io import BytesIO

import pandas as pd
import requests
import streamlit as st


# =========================
# НАСТРОЙКИ (ПРОВЕРЬТЕ ЭТО)
# =========================

CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQwA5g3ZuBmZlY3vQMbc7nautnpK7c4ioKtTYU_mTskZb6A6nJ_yeokKIvfbVBFH1jTPpzOgoBMD89n/pub?gid=372714191&single=true&output=csv"

# Герб: положите файл в репо рядом с app.py
GERB_PATH = "gerb.png"

TITLE_MINISTRY = "Министерство восстановления, развития приграничья и строительства Курской области"
TITLE_APP = "Реестр объектов"
SUBTITLE = "Единый список объектов 2025–2028 с быстрыми фильтрами и переходом в карточку/папку."

# Названия колонок в CSV (как у вас в таблице)
COL_ID = "id"
COL_SECTOR = "sector"
COL_DISTRICT = "district"
COL_NAME = "name"
COL_RESP = "responsible"
COL_STATUS = "status"
COL_WORK = "work_flag"
COL_ADDR = "address"
COL_CARD = "card_url"
COL_FOLDER = "folder_url"


# =========================
# СТРАНИЦА
# =========================
st.set_page_config(
    page_title="Реестр объектов — Курская область",
    page_icon="🗂️",
    layout="wide",
)

CSS = """
<style>
body { background: #f4f7fb; }

/* Контейнер страницы */
.block-container { padding-top: 0.6rem; padding-bottom: 2rem; max-width: 1200px; }

/* Full-bleed шапка */
.hero-bleed{
  position: relative;
  left: 50%;
  right: 50%;
  margin-left: -50vw;
  margin-right: -50vw;
  width: 100vw;
  padding: 26px 0 18px 0;
}
.hero-inner{
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
}

.hero {
  width: 100%;
  border-radius: 20px;
  padding: 22px 26px;
  background:
    radial-gradient(1100px 520px at 10% 0%, rgba(255,255,255,0.12), rgba(255,255,255,0) 60%),
    linear-gradient(135deg, #1f3b7a 0%, #233c7a 35%, #1c2f63 100%);
  box-shadow: 0 14px 30px rgba(0,0,0,0.18);
  color: #fff;
  position: relative;
  overflow: hidden;
}
.hero:after{
  content:"";
  position:absolute;
  right:-120px; top:-140px;
  width:620px; height:520px;
  background: linear-gradient(135deg, rgba(255,255,255,0.12), rgba(255,255,255,0));
  transform: rotate(20deg);
  border-radius: 44px;
}
.hero-grid{
  position: relative;
  display:flex;
  gap:18px;
  align-items:center;
}
.hero-logo{
  width:92px; height:92px;
  border-radius: 16px;
  background: rgba(255,255,255,0.10);
  border: 1px solid rgba(255,255,255,0.18);
  display:flex; align-items:center; justify-content:center;
  flex: 0 0 auto;
  overflow:hidden;
  box-shadow: inset 0 0 0 1px rgba(255,255,255,0.10);
}
.hero-logo img{ width:74px; height:74px; object-fit:contain; }

.hero-titles{ display:flex; flex-direction:column; gap:6px; min-width: 0; }

/* Крупнее “Министерство …”, 2 строки */
.hero-ministry{
  font-size: 22px;
  font-weight: 900;
  line-height: 1.18;
  opacity: 0.98;
  max-width: 980px;
  word-break: keep-all;
}

/* “Реестр объектов” */
.hero-app{
  font-size: 36px;
  font-weight: 900;
  line-height: 1.05;
  letter-spacing: 0.2px;
  margin-top: 2px;
}

.hero-sub{
  font-size: 13.5px;
  opacity: 0.92;
  max-width: 920px;
}

.pill{
  display:inline-flex; align-items:center; gap:8px;
  margin-top: 10px;
  font-size: 12px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(255,255,255,0.18);
  background: rgba(255,255,255,0.10);
  width: fit-content;
}

/* Карточки */
.card {
  border-radius: 16px;
  border: 1px solid rgba(0,0,0,0.08);
  background: #ffffff;
  padding: 14px 14px 12px 14px;
  box-shadow: 0 10px 26px rgba(0,0,0,0.06);
  margin-bottom: 14px;
}

.card-title{
  font-size: 16.5px;
  font-weight: 800;
  line-height: 1.25;
  margin-bottom: 8px;
}

.meta{
  background: #f7f9fc;
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: 12px;
  padding: 10px 12px;
  margin-bottom: 10px;
}
.meta-row{
  display:flex;
  gap:8px;
  align-items:flex-start;
  margin: 3px 0;
  font-size: 13px;
  line-height: 1.35;
}
.meta-ico{ width: 18px; text-align:center; opacity:0.95; }
.meta b{ font-weight: 700; }

.badges{ display:flex; gap:8px; flex-wrap: wrap; margin: 8px 0 10px 0; }
.badge{
  display:inline-flex; align-items:center; gap:6px;
  padding: 5px 10px;
  border-radius: 999px;
  font-size: 12px;
  border: 1px solid rgba(0,0,0,0.10);
  background: #ffffff;
}

/* Делаем кнопки чуть ровнее */
div[data-testid="column"] button, div[data-testid="column"] a {
  width: 100%;
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# =========================
# УТИЛИТЫ
# =========================
def safe(x) -> str:
    """HTML-экранирование, чтобы никогда не ломались карточки."""
    if x is None:
        return ""
    x = str(x)
    if x.lower() in ("nan", "none"):
        return ""
    return html.escape(x)


def img_to_b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def norm_text(x: str) -> str:
    x = "" if x is None else str(x)
    x = x.strip()
    if x.lower() in ("nan", "none"):
        return ""
    return x


def district_sort_key(d: str):
    """Курск первым, Курский район вторым, дальше по алфавиту."""
    t = norm_text(d).lower().replace(".", "").replace("ё", "е")
    # 1) г. Курск
    if t in ("г курск", "гкурск", "курск", "город курск"):
        return (0, "курск")
    # 2) Курский район
    if "курск" in t and "район" in t:
        return (1, t)
    # 3) остальное
    return (2, t)


@st.cache_data(ttl=600, show_spinner=False)
def load_df(csv_url: str) -> pd.DataFrame:
    r = requests.get(csv_url, timeout=30)
    r.raise_for_status()
    content = r.content

    df = pd.read_csv(BytesIO(content), dtype=str).fillna("")
    # нормализуем пробелы
    for c in df.columns:
        df[c] = df[c].astype(str).map(lambda x: x.strip())
    return df


def header_block():
    logo_html = ""
    try:
        if GERB_PATH and os.path.exists(GERB_PATH):
            logo_html = f'<div class="hero-logo"><img src="data:image/png;base64,{img_to_b64(GERB_PATH)}" /></div>'
    except Exception:
        logo_html = ""

    st.markdown(
        f"""
        <div class="hero-bleed">
          <div class="hero-inner">
            <div class="hero">
              <div class="hero-grid">
                {logo_html}
                <div class="hero-titles">
                  <div class="hero-ministry">{safe(TITLE_MINISTRY)}</div>
                  <div class="hero-app">{safe(TITLE_APP)}</div>
                  <div class="hero-sub">{safe(SUBTITLE)}</div>
                  <div class="pill">🧾 Источник данных: Google Sheets (CSV)</div>
                </div>
              </div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_card(row: pd.Series):
    name = norm_text(row.get(COL_NAME, ""))
    sector = norm_text(row.get(COL_SECTOR, ""))
    district = norm_text(row.get(COL_DISTRICT, ""))
    address = norm_text(row.get(COL_ADDR, ""))
    responsible = norm_text(row.get(COL_RESP, ""))
    status = norm_text(row.get(COL_STATUS, ""))
    work = norm_text(row.get(COL_WORK, ""))

    card_url = norm_text(row.get(COL_CARD, ""))
    folder_url = norm_text(row.get(COL_FOLDER, ""))

    # БЕЗ ID в заголовке — как вы просили
    title_text = name if name else "Объект"

    # Бейджи
    badge_status = status if status else "—"
    badge_work = work if work else "—"

    # Метаданные — всегда через safe(), чтобы один кривой символ не ломал карточку
    meta_html = f"""
    <div class="meta">
      <div class="meta-row"><span class="meta-ico">🏷️</span><span><b>Отрасль:</b> {safe(sector) if sector else "—"}</span></div>
      <div class="meta-row"><span class="meta-ico">📍</span><span><b>Район:</b> {safe(district) if district else "—"}</span></div>
      <div class="meta-row"><span class="meta-ico">🗺️</span><span><b>Адрес:</b> {safe(address) if address else "—"}</span></div>
      <div class="meta-row"><span class="meta-ico">👤</span><span><b>Ответственный:</b> {safe(responsible) if responsible else "—"}</span></div>
    </div>
    """

    st.markdown(f'<div class="card"><div class="card-title">{safe(title_text)}</div>{meta_html}', unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="badges">
          <div class="badge">📌 <b>Статус:</b> {safe(badge_status)}</div>
          <div class="badge">🛠️ <b>Работы:</b> {safe(badge_work)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        if card_url:
            st.link_button("📄 Открыть карточку", card_url, use_container_width=True)
        else:
            st.button("📄 Открыть карточку", use_container_width=True, disabled=True)
    with c2:
        if folder_url:
            st.link_button("📁 Открыть папку", folder_url, use_container_width=True)
        else:
            st.button("📁 Открыть папку", use_container_width=True, disabled=True)

    st.markdown("</div>", unsafe_allow_html=True)


# =========================
# ОСНОВНОЕ ПРИЛОЖЕНИЕ
# =========================
header_block()

try:
    df = load_df(CSV_URL)
except Exception as e:
    st.error("Не удалось загрузить CSV. Проверьте ссылку публикации (output=csv) и доступность.")
    st.code(str(e))
    st.stop()

# Проверка наличия колонок
required_cols = [COL_SECTOR, COL_DISTRICT, COL_NAME, COL_RESP, COL_STATUS, COL_WORK, COL_ADDR, COL_CARD, COL_FOLDER]
missing = [c for c in required_cols if c not in df.columns]
if missing:
    st.error("В CSV не хватает колонок: " + ", ".join(missing))
    st.info("Проверьте шапку таблицы Google Sheets и названия колонок в начале app.py.")
    st.stop()

# Фильтры
sectors = sorted([s for s in df[COL_SECTOR].unique() if norm_text(s)], key=lambda x: norm_text(x).lower())
districts = sorted([d for d in df[COL_DISTRICT].unique() if norm_text(d)], key=district_sort_key)
statuses = sorted([s for s in df[COL_STATUS].unique() if norm_text(s)], key=lambda x: norm_text(x).lower())

colA, colB, colC = st.columns(3)
with colA:
    sector_sel = st.selectbox("🏷️ Отрасль", ["Все"] + sectors, index=0)
with colB:
    district_sel = st.selectbox("📍 Район", ["Все"] + districts, index=0)
with colC:
    status_sel = st.selectbox("📌 Статус", ["Все"] + statuses, index=0)

q = st.text_input("🔎 Поиск (наименование / адрес / ответственный / id)", value="").strip()

# Применяем фильтры
f = df.copy()

if sector_sel != "Все":
    f = f[f[COL_SECTOR].astype(str) == sector_sel]

if district_sel != "Все":
    f = f[f[COL_DISTRICT].astype(str) == district_sel]

if status_sel != "Все":
    f = f[f[COL_STATUS].astype(str) == status_sel]

if q:
    qlow = q.lower()
    def row_match(r):
        parts = [
            str(r.get(COL_ID, "")),
            str(r.get(COL_NAME, "")),
            str(r.get(COL_ADDR, "")),
            str(r.get(COL_RESP, "")),
        ]
        joined = " ".join(parts).lower()
        return qlow in joined

    f = f[f.apply(row_match, axis=1)]

st.caption(f"Показано объектов: {len(f)} из {len(df)}")
st.divider()

# Сетка карточек
if len(f) == 0:
    st.info("По выбранным фильтрам ничего не найдено.")
    st.stop()

# 2 колонки карточек
left, right = st.columns(2)
for i, (_, row) in enumerate(f.iterrows()):
    with (left if i % 2 == 0 else right):
        render_card(row)
