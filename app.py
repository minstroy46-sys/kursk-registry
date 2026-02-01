import re
import html
from pathlib import Path

import pandas as pd
import streamlit as st


# =========================
# НАСТРОЙКИ
# =========================
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQwA5g3ZuBmZlY3vQMbc7nautnpK7c4ioKtTYU_mTskZb6A6nJ_yeokKIvfbVBFH1jTPpzOgoBMD89n/pub?gid=372714191&single=true&output=csv"

PAGE_TITLE = "Министерство восстановления, развития приграничья и строительства Курской области · Реестр объектов"
MINISTRY_TITLE = "Министерство восстановления, развития приграничья и строительства Курской области"
SUBTITLE = "Единый список объектов 2025–2028 с быстрыми фильтрами и переходом в карточку/папку."
BADGE_TEXT = "Источник данных: Google Sheets (CSV)"

# Если у тебя герб лежит в репозитории — положи файл сюда:
# repo/assets/gerb.png
GERB_PATH = Path("assets/gerb.png")

PRIORITY_DISTRICTS = ["г. Курск", "Курск", "Курский район"]  # приоритет для сортировки


# =========================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =========================
def _clean_str(x) -> str:
    """Приводит значение к нормальной строке: убирает NaN/None и лишние пробелы."""
    if x is None:
        return ""
    try:
        # pandas NaN
        if pd.isna(x):
            return ""
    except Exception:
        pass
    s = str(x)
    s = s.replace("\u00a0", " ")  # неразрывный пробел
    s = s.strip()
    return s


def esc(x) -> str:
    """Экранирует текст, чтобы он НЕ мог ломать HTML карточек."""
    return html.escape(_clean_str(x), quote=True)


def normalize_for_search(s: str) -> str:
    s = _clean_str(s).lower()
    s = re.sub(r"\s+", " ", s)
    return s


def district_sort_key(d: str):
    """Сортировка районов: Курск -> Курский район -> остальные по алфавиту."""
    ds = _clean_str(d)
    # приводим к канонике
    if ds == "Курск":
        ds = "г. Курск"

    # приоритет
    if ds == "г. Курск":
        return (0, ds)
    if ds == "Курский район":
        return (1, ds)
    return (2, ds)


@st.cache_data(ttl=300, show_spinner=False)
def load_data(url: str) -> pd.DataFrame:
    df = pd.read_csv(url)
    # Нормализуем названия колонок
    df.columns = [c.strip() for c in df.columns]

    # Убедимся что нужные есть
    needed = [
        "id", "sector", "district", "name", "responsible",
        "status", "work_flag", "address", "card_url", "folder_url"
    ]
    for col in needed:
        if col not in df.columns:
            df[col] = ""

    # Приводим к строкам для стабильности
    for col in needed:
        df[col] = df[col].apply(_clean_str)

    return df


def pick_image_bytes():
    """Пытается взять герб из assets/gerb.png, если есть."""
    try:
        if GERB_PATH.exists():
            return GERB_PATH.read_bytes()
    except Exception:
        pass
    return None


def inject_css():
    st.markdown(
        """
        <style>
          /* Общий фон */
          .stApp {
            background: #f4f7fb;
          }

          /* Убираем лишние отступы сверху */
          .block-container {
            padding-top: 18px !important;
            padding-bottom: 36px !important;
            max-width: 1260px;
          }

          /* ШАПКА */
          .hero-wrap{
            display:flex;
            gap:18px;
            align-items:stretch;
            margin: 8px 0 16px 0;
          }
          .hero-card{
            flex:1;
            background: linear-gradient(180deg, #2f4f90 0%, #243e73 100%);
            color: #fff;
            border-radius: 16px;
            padding: 18px 20px;
            box-shadow: 0 10px 26px rgba(15, 23, 42, 0.18);
            border: 1px solid rgba(255,255,255,0.08);
            position: relative;
            overflow: hidden;
          }
          .hero-card:before{
            content:"";
            position:absolute;
            inset:-120px -180px auto auto;
            width: 360px;
            height: 360px;
            background: radial-gradient(circle, rgba(255,255,255,0.16), rgba(255,255,255,0));
            transform: rotate(25deg);
          }
          .hero-title-ministry{
            font-size: 26px;
            font-weight: 800;
            line-height: 1.15;
            margin: 0;
          }
          .hero-title-registry{
            font-size: 34px;
            font-weight: 900;
            line-height: 1.15;
            margin: 8px 0 0 0;
          }
          .hero-sub{
            margin-top: 8px;
            font-size: 13px;
            color: rgba(255,255,255,0.86);
            max-width: 820px;
          }
          .hero-badge{
            display:inline-flex;
            align-items:center;
            gap:8px;
            margin-top: 10px;
            padding: 6px 10px;
            border-radius: 999px;
            font-size: 12px;
            background: rgba(255,255,255,0.10);
            border: 1px solid rgba(255,255,255,0.14);
            width: fit-content;
          }

          .hero-gerb{
            width: 86px;
            height: 86px;
            border-radius: 14px;
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.10);
            display:flex;
            align-items:center;
            justify-content:center;
            overflow:hidden;
            box-shadow: inset 0 0 0 1px rgba(255,255,255,0.06);
          }
          .hero-gerb img{
            width: 72px;
            height: 72px;
            object-fit: contain;
            filter: drop-shadow(0 6px 10px rgba(0,0,0,0.18));
          }

          /* Метки */
          .pill{
            display:inline-flex;
            align-items:center;
            gap:6px;
            padding: 6px 10px;
            border-radius: 999px;
            background: #eef2ff;
            border: 1px solid #dbe3ff;
            color:#1f3a8a;
            font-size:12px;
            font-weight: 600;
          }

          /* Карточка объекта */
          .obj-card{
            background:#ffffff;
            border: 1px solid rgba(15, 23, 42, 0.08);
            border-radius: 16px;
            padding: 14px 14px 12px 14px;
            box-shadow: 0 8px 18px rgba(15, 23, 42, 0.06);
            margin-bottom: 14px;
          }
          .obj-title{
            font-size: 16px;
            font-weight: 800;
            margin: 0 0 10px 0;
          }
          .meta{
            background:#f7f9fc;
            border: 1px solid rgba(15, 23, 42, 0.06);
            border-radius: 12px;
            padding: 10px 12px;
            margin-bottom: 10px;
          }
          .meta-row{
            display:flex;
            gap:10px;
            margin: 3px 0;
            font-size: 13px;
            color: #111827;
          }
          .meta-ico{
            width: 18px;
            opacity: 0.95;
            flex: 0 0 18px;
          }
          .meta-key{
            font-weight: 700;
            color:#0f172a;
            margin-right: 6px;
          }
          .meta-val{
            color:#111827;
          }

          .btn-row{
            display:flex;
            gap:10px;
            margin-top: 10px;
          }
          /* Стили для streamlit кнопок */
          div[data-testid="stButton"] button{
            border-radius: 12px !important;
            padding: 10px 14px !important;
            border: 1px solid rgba(15,23,42,0.14) !important;
          }
          div[data-testid="stButton"] button:hover{
            border-color: rgba(15,23,42,0.24) !important;
          }

          /* Лейблы над селектами */
          .filter-label{
            font-weight: 800;
            margin: 8px 0 4px 2px;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================
# APP
# =========================
st.set_page_config(page_title=PAGE_TITLE, page_icon="🏗️", layout="wide")
inject_css()

df = load_data(CSV_URL)

# Приводим районы к виду "г. Курск" если было "Курск"
df["district"] = df["district"].apply(lambda x: "г. Курск" if _clean_str(x) == "Курск" else _clean_str(x))

# Заголовок (герб + шапка)
gerb_bytes = pick_image_bytes()

left = ""
if gerb_bytes:
    st.sidebar.image(gerb_bytes, width=120)

st.markdown(
    f"""
    <div class="hero-wrap">
      <div class="hero-card">
        <div style="display:flex; gap:16px; align-items:center;">
          <div class="hero-gerb">
            {"<img src='data:image/png;base64," + (pd.util.hash_pandas_object(pd.Series([1])).astype(str).iloc[0]) + "'/>" if False else ""}
          </div>
          <div style="flex:1;">
            <div class="hero-title-ministry">{html.escape(MINISTRY_TITLE)}</div>
            <div class="hero-title-registry">Реестр объектов</div>
            <div class="hero-sub">{html.escape(SUBTITLE)}</div>
            <div class="hero-badge">📌 {html.escape(BADGE_TEXT)}</div>
          </div>
        </div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Если герб есть — покажем его ВНУТРИ заливки (правильно, как ты хочешь)
if gerb_bytes:
    import base64
    b64 = base64.b64encode(gerb_bytes).decode("utf-8")
    st.markdown(
        f"""
        <style>
          .hero-gerb {{
            background: rgba(255,255,255,0.10) !important;
          }}
          .hero-gerb:before {{
            content:"";
            position:absolute;
            width:0; height:0;
          }}
        </style>
        <script>
          // ничего
        </script>
        """,
        unsafe_allow_html=True
    )
    # Перерисуем шапку корректно с картинкой
    st.markdown(
        f"""
        <div class="hero-wrap">
          <div class="hero-card">
            <div style="display:flex; gap:16px; align-items:center;">
              <div class="hero-gerb" style="position:relative;">
                <img src="data:image/png;base64,{b64}" />
              </div>
              <div style="flex:1;">
                <div class="hero-title-ministry">{html.escape(MINISTRY_TITLE)}</div>
                <div class="hero-title-registry">Реестр объектов</div>
                <div class="hero-sub">{html.escape(SUBTITLE)}</div>
                <div class="hero-badge">📌 {html.escape(BADGE_TEXT)}</div>
              </div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ===== Фильтры =====
sectors = sorted([s for s in df["sector"].unique() if _clean_str(s)])
districts = sorted([d for d in df["district"].unique() if _clean_str(d)], key=district_sort_key)
statuses = sorted([s for s in df["status"].unique() if _clean_str(s)])

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown('<div class="filter-label">🏷️ Отрасль</div>', unsafe_allow_html=True)
    sector_sel = st.selectbox(" ", ["Все"] + sectors, label_visibility="collapsed")

with col2:
    st.markdown('<div class="filter-label">📍 Район</div>', unsafe_allow_html=True)
    district_sel = st.selectbox("  ", ["Все"] + districts, label_visibility="collapsed")

with col3:
    st.markdown('<div class="filter-label">📌 Статус</div>', unsafe_allow_html=True)
    status_sel = st.selectbox("   ", ["Все"] + statuses, label_visibility="collapsed")

st.markdown('<div class="filter-label">🔎 Поиск (наименование / адрес / ответственный)</div>', unsafe_allow_html=True)
q = st.text_input("Поиск", "", label_visibility="collapsed")

# ===== Применяем фильтры =====
f = df.copy()

if sector_sel != "Все":
    f = f[f["sector"] == sector_sel]

if district_sel != "Все":
    f = f[f["district"] == district_sel]

if status_sel != "Все":
    f = f[f["status"] == status_sel]

q_norm = normalize_for_search(q)
if q_norm:
    blob = (
        f["name"].apply(normalize_for_search)
        + " " + f["address"].apply(normalize_for_search)
        + " " + f["responsible"].apply(normalize_for_search)
        + " " + f["id"].apply(normalize_for_search)
    )
    f = f[blob.str.contains(re.escape(q_norm), na=False)]

st.caption(f"Показано объектов: {len(f)} из {len(df)}")

st.markdown("<hr/>", unsafe_allow_html=True)

# ===== Вывод карточек =====
def render_card(row: pd.Series):
    # !!! КРИТИЧНО: все текстовые поля эскейпим, чтобы НЕ сломать HTML
    name = esc(row.get("name", ""))
    sector_v = esc(row.get("sector", ""))
    district_v = esc(row.get("district", ""))
    address = esc(row.get("address", ""))
    responsible = esc(row.get("responsible", ""))
    status_v = esc(row.get("status", ""))
    work_flag = esc(row.get("work_flag", ""))

    card_url = _clean_str(row.get("card_url", ""))
    folder_url = _clean_str(row.get("folder_url", ""))

    # Доп. нормализация статуса/работ
    if status_v == "" or status_v.lower() == "nan":
        status_v = "—"
    if work_flag == "" or work_flag.lower() == "nan":
        work_flag = "—"

    st.markdown(
        f"""
        <div class="obj-card">
          <div class="obj-title">{name}</div>

          <div class="meta">
            <div class="meta-row"><span class="meta-ico">🏷️</span><span><span class="meta-key">Отрасль:</span> <span class="meta-val">{sector_v}</span></span></div>
            <div class="meta-row"><span class="meta-ico">📍</span><span><span class="meta-key">Район:</span> <span class="meta-val">{district_v}</span></span></div>
            <div class="meta-row"><span class="meta-ico">🗺️</span><span><span class="meta-key">Адрес:</span> <span class="meta-val">{address}</span></span></div>
            <div class="meta-row"><span class="meta-ico">👤</span><span><span class="meta-key">Ответственный:</span> <span class="meta-val">{responsible}</span></span></div>
            <div style="margin-top:8px; display:flex; gap:10px; flex-wrap:wrap;">
              <span class="pill">📌 Статус: {status_v}</span>
              <span class="pill">🛠️ Работы: {work_flag}</span>
            </div>
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


# Сетка 2 колонки
cols = st.columns(2)
for i, (_, row) in enumerate(f.iterrows()):
    with cols[i % 2]:
        render_card(row)
