# app.py
# -*- coding: utf-8 -*-
import os
import html
import base64
from io import BytesIO

import pandas as pd
import streamlit as st


# =========================
# НАСТРОЙКИ (ПРАВЬТЕ ТОЛЬКО ЭТО, ЕСЛИ НУЖНО)
# =========================
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQwA5g3ZuBmZlY3vQMbc7nautnpK7c4ioKtTYU_mTskZb6A6nJ_yeokKIvfbVBFH1jTPpzOgoBMD89n/pub?gid=372714191&single=true&output=csv"

TITLE_MINISTRY = "Министерство восстановления, развития приграничья и строительства Курской области"
TITLE_APP = "Реестр объектов"
SUBTITLE = "Единый список объектов 2025–2028 с быстрыми фильтрами и переходом в карточку/папку."

# Положите герб в репозиторий рядом с app.py (или в папку assets/) и укажите путь
# Примеры:
# GERB_PATH = "gerb.png"
# GERB_PATH = "assets/gerb.png"
GERB_PATH = "gerb.png"

# Приоритет района в фильтре (первым будет г. Курск, вторым Курский район, остальные по алфавиту)
DISTRICT_PRIORITY = ["г. Курск", "Курский"]


# =========================
# СТРАНИЦА / БАЗОВЫЕ НАСТРОЙКИ STREAMLIT
# =========================
st.set_page_config(
    page_title=f"{TITLE_APP} — Курская область",
    page_icon="🏛️",
    layout="wide",
)

# =========================
# HELPERS
# =========================
def safe(x) -> str:
    """Экранируем текст, чтобы никакая строка из таблицы не ломала HTML."""
    if x is None:
        return ""
    if isinstance(x, float) and pd.isna(x):
        return ""
    return html.escape(str(x), quote=True)

def img_to_b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def normalize_text(x):
    if x is None:
        return ""
    if isinstance(x, float) and pd.isna(x):
        return ""
    return str(x).strip()

def clean_url(x):
    x = normalize_text(x)
    return x if x.lower().startswith("http") else ""

def district_sort_key(name: str):
    name = normalize_text(name)
    if not name:
        return (9, "")
    if name == DISTRICT_PRIORITY[0]:
        return (0, name)
    if name == DISTRICT_PRIORITY[1]:
        return (1, name)
    return (2, name.lower())

@st.cache_data(ttl=300, show_spinner=False)
def load_data(csv_url: str) -> pd.DataFrame:
    df = pd.read_csv(csv_url)

    # Ожидаемые колонки (у вас именно такие)
    # id, sector, district, name, responsible, status, work_flag, address, card_url, folder_url
    # На всякий случай — приводим к нижнему регистру, убираем пробелы
    df.columns = [c.strip().lower() for c in df.columns]

    # Гарантируем наличие колонок
    for col in [
        "id", "sector", "district", "name", "responsible",
        "status", "work_flag", "address", "card_url", "folder_url"
    ]:
        if col not in df.columns:
            df[col] = ""

    # Нормализуем значения
    for col in df.columns:
        df[col] = df[col].apply(normalize_text)

    # URL чистим
    df["card_url"] = df["card_url"].apply(clean_url)
    df["folder_url"] = df["folder_url"].apply(clean_url)

    # Статусы/флаги: пустые -> "—"
    df["status"] = df["status"].replace("", "—")
    df["work_flag"] = df["work_flag"].replace("", "—")

    return df


# =========================
# CSS (СТАБИЛЬНЫЙ, ЧТОБЫ НЕ ЛОМАЛОСЬ)
# =========================
CSS = """
<style>
/* Шрифты/фон */
.block-container { padding-top: 16px; padding-bottom: 28px; }
html, body, [class*="css"]  { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; }
.stApp { background: #f3f6fb; }

/* Убираем лишний верхний отступ Streamlit */
header[data-testid="stHeader"] { background: transparent; }
div[data-testid="stToolbar"] { right: 10px; }

/* Hero full-bleed (не обрезается) */
.hero-bleed{
  position: relative;
  left: 50%;
  margin-left: -50vw;
  width: 100vw;
  padding: 18px 0 14px 0;
}

.hero-inner{
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 18px;
}

.hero {
  width: 100%;
  border-radius: 22px;
  padding: 22px 24px;
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
  right:-160px; top:-170px;
  width:780px; height:580px;
  background: linear-gradient(135deg, rgba(255,255,255,0.14), rgba(255,255,255,0));
  transform: rotate(18deg);
  border-radius: 52px;
}

.hero-grid{
  position: relative;
  display:flex;
  gap:18px;
  align-items:center;
}

.hero-logo{
  width:96px; height:96px;
  border-radius: 18px;
  background: rgba(255,255,255,0.10);
  border: 1px solid rgba(255,255,255,0.18);
  display:flex; align-items:center; justify-content:center;
  flex: 0 0 auto;
  overflow:hidden;
  box-shadow: inset 0 0 0 1px rgba(255,255,255,0.10);
}

.hero-logo img{ width:78px; height:78px; object-fit:contain; }

.hero-titles{ display:flex; flex-direction:column; gap:8px; min-width: 0; }

.hero-ministry{
  font-size: 28px;
  font-weight: 900;
  line-height: 1.15;
  opacity: 0.98;
}

.hero-app{
  font-size: 40px;
  font-weight: 900;
  line-height: 1.05;
  letter-spacing: 0.2px;
}

.hero-sub{
  font-size: 13.5px;
  opacity: 0.92;
  max-width: 980px;
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

/* Фильтры */
.filters-card {
  background: rgba(255,255,255,0.55);
  border: 1px solid rgba(0,0,0,0.05);
  border-radius: 16px;
  padding: 12px 14px;
}

/* Карточки объектов */
.obj-card {
  background: #ffffff;
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: 16px;
  padding: 14px 14px 12px 14px;
  box-shadow: 0 6px 18px rgba(0,0,0,0.05);
}

.obj-title{
  font-size: 16px;
  font-weight: 800;
  line-height: 1.2;
  margin-bottom: 10px;
}

.meta-box{
  background: #f4f7fb;
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: 12px;
  padding: 10px 12px;
  margin-bottom: 10px;
}

.meta-row{
  display:flex;
  gap:10px;
  align-items:flex-start;
  margin: 4px 0;
  font-size: 13px;
  color: #0f172a;
}

.meta-ico{ width: 18px; text-align:center; opacity: 0.95; }
.meta-key{ font-weight: 700; margin-right: 6px; }
.badge{
  display:inline-flex;
  align-items:center;
  gap:8px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(15,23,42,0.10);
  background: #ffffff;
  font-size: 12px;
  margin-right: 8px;
}

/* Кнопки */
div.stButton>button, a[role="button"]{
  border-radius: 12px !important;
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# =========================
# HERO (ШАПКА) — СТАБИЛЬНАЯ
# =========================
def header_block():
    logo_html = ""
    try:
        if GERB_PATH and os.path.exists(GERB_PATH):
            b64 = img_to_b64(GERB_PATH)
            logo_html = f'<div class="hero-logo"><img src="data:image/png;base64,{b64}" alt="Герб"/></div>'
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


# =========================
# UI — ФИЛЬТРЫ
# =========================
header_block()

with st.container():
    st.markdown('<div class="filters-card">', unsafe_allow_html=True)

    df = load_data(CSV_URL)

    # Списки фильтров
    sectors = sorted([x for x in df["sector"].unique() if x], key=lambda s: s.lower())
    districts = sorted([x for x in df["district"].unique() if x], key=district_sort_key)
    statuses = sorted([x for x in df["status"].unique() if x], key=lambda s: s.lower())

    c1, c2, c3 = st.columns(3)
    with c1:
        sector_sel = st.selectbox("🏷️ Отрасль", ["Все"] + sectors, index=0)
    with c2:
        district_sel = st.selectbox("📍 Район", ["Все"] + districts, index=0)
    with c3:
        status_sel = st.selectbox("📌 Статус", ["Все"] + statuses, index=0)

    q = st.text_input("🔎 Поиск (наименование / адрес / ответственный / id)", value="").strip()

    st.markdown('</div>', unsafe_allow_html=True)


# =========================
# ФИЛЬТРАЦИЯ
# =========================
f = df.copy()

if sector_sel != "Все":
    f = f[f["sector"] == sector_sel]

if district_sel != "Все":
    f = f[f["district"] == district_sel]

if status_sel != "Все":
    f = f[f["status"] == status_sel]

if q:
    qq = q.lower()
    f = f[
        f["name"].str.lower().str.contains(qq, na=False)
        | f["address"].str.lower().str.contains(qq, na=False)
        | f["responsible"].str.lower().str.contains(qq, na=False)
        | f["id"].str.lower().str.contains(qq, na=False)
    ]

st.caption(f"Показано объектов: **{len(f)}** из **{len(df)}**")
st.divider()


# =========================
# РЕНДЕР КАРТОЧЕК — БЕЗ РИСКА «СЛОМАТЬ ОДИН ОБЪЕКТ»
# =========================
def render_object_card(row: pd.Series):
    # Все значения безопасно приводим к строкам и экранируем
    name = safe(row.get("name", ""))
    sector = safe(row.get("sector", "—"))
    district = safe(row.get("district", "—"))
    address = safe(row.get("address", "—"))
    responsible = safe(row.get("responsible", "—"))
    status = safe(row.get("status", "—"))
    work_flag = safe(row.get("work_flag", "—"))

    card_url = clean_url(row.get("card_url", ""))
    folder_url = clean_url(row.get("folder_url", ""))

    st.markdown(
        f"""
        <div class="obj-card">
          <div class="obj-title">{name}</div>

          <div class="meta-box">
            <div class="meta-row"><span class="meta-ico">🏷️</span><span><span class="meta-key">Отрасль:</span>{sector}</span></div>
            <div class="meta-row"><span class="meta-ico">📍</span><span><span class="meta-key">Район:</span>{district}</span></div>
            <div class="meta-row"><span class="meta-ico">🗺️</span><span><span class="meta-key">Адрес:</span>{address}</span></div>
            <div class="meta-row"><span class="meta-ico">👤</span><span><span class="meta-key">Ответственный:</span>{responsible}</span></div>
          </div>

          <div style="margin: 6px 0 10px 0;">
            <span class="badge">📌 <b>Статус:</b> {status}</span>
            <span class="badge">🛠️ <b>Работы:</b> {work_flag}</span>
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
            st.button("📄 Открыть карточку", use_container_width=True, disabled=True)
    with b2:
        if folder_url:
            st.link_button("📁 Открыть папку", folder_url, use_container_width=True)
        else:
            st.button("📁 Открыть папку", use_container_width=True, disabled=True)


# Сетка 2 колонки (как у вас)
cols = st.columns(2)
i = 0

# Немного «устойчивой сортировки» по району и названию
f2 = f.copy()
f2["_district_key"] = f2["district"].apply(district_sort_key)
f2["_name_key"] = f2["name"].str.lower()
f2 = f2.sort_values(by=["_district_key", "_name_key"], ascending=True).drop(columns=["_district_key", "_name_key"])

for _, row in f2.iterrows():
    with cols[i % 2]:
        try:
            render_object_card(row)
        except Exception as e:
            # Даже если одна строка «кривая», приложение не ломаем — показываем упрощённую карточку
            st.error("⚠️ Карточка объекта не отрисовалась из-за некорректных данных в строке.")
            st.write({"id": row.get("id", ""), "name": row.get("name", ""), "error": str(e)})
    i += 1


# =========================
# ПОДСКАЗКА ПО БЭКАПУ (НЕ МЕШАЕТ РАБОТЕ)
# =========================
with st.expander("🧷 Как сделать бэкап (чтобы откатиться за 10 секунд)", expanded=False):
    st.markdown(
        """
1) Откройте GitHub → ваш репозиторий → вкладка **Code**  
2) Нажмите на список веток **main**  
3) Введите имя ветки, например: `backup-ok-1`  
4) Нажмите **Create branch: backup-ok-1 from main**

Теперь это «сейв». Если что-то сломали — возвращаемся на ветку или делаем rollback через History.
        """.strip()
    )
