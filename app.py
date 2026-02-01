import pandas as pd
import streamlit as st
from pathlib import Path

# =========================
# НАСТРОЙКИ
# =========================
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQwA5g3ZuBmZlY3vQMbc7nautnpK7c4ioKtTYU_mTskZb6A6nJ_yeokKIvfbVBFH1jTPpzOgoBMD89n/pub?gid=372714191&single=true&output=csv"

BRAND_PRIMARY = "#172C6C"   # темно-синий (как в презентации)
BRAND_SECONDARY = "#435488" # второй синий
BRAND_BG = "#F5F7FB"        # светлый фон
BRAND_CARD = "#FFFFFF"      # карточки
BRAND_ACCENT = "#D9C0A9"    # теплый акцент (беж)
BRAND_MUTED = "#667085"     # серый текст

st.set_page_config(
    page_title="Минстрой Курской области • Реестр объектов",
    layout="wide",
)

# =========================
# CSS (красивый вид)
# =========================
st.markdown(
    f"""
<style>
  .stApp {{
    background: {BRAND_BG};
  }}

  /* Шапка */
  .hero {{
    display:flex; align-items:center; gap:16px;
    padding: 18px 18px;
    background: linear-gradient(90deg, {BRAND_PRIMARY}, {BRAND_SECONDARY});
    border-radius: 16px;
    color: white;
    box-shadow: 0 10px 24px rgba(16, 24, 40, 0.18);
    margin-bottom: 14px;
  }}
  .hero h1 {{
    font-size: 34px;
    line-height: 1.1;
    margin: 0;
    font-weight: 800;
    letter-spacing: 0.2px;
  }}
  .hero p {{
    margin: 6px 0 0 0;
    opacity: 0.9;
    font-size: 14px;
  }}
  .pill {{
    display:inline-block;
    padding: 6px 10px;
    border-radius: 999px;
    background: rgba(255,255,255,0.16);
    border: 1px solid rgba(255,255,255,0.22);
    font-size: 12px;
    margin-top: 10px;
  }}

  /* Карточка */
  .card {{
    background: {BRAND_CARD};
    border-radius: 16px;
    padding: 14px 14px;
    border: 1px solid rgba(16, 24, 40, 0.08);
    box-shadow: 0 10px 18px rgba(16, 24, 40, 0.06);
  }}
  .card-title {{
    font-size: 18px;
    font-weight: 800;
    margin: 0 0 6px 0;
    color: #101828;
  }}
  .card-sub {{
    font-size: 13px;
    color: {BRAND_MUTED};
    margin: 0 0 10px 0;
  }}
  .kv {{
    display:flex;
    gap:10px;
    flex-wrap: wrap;
    margin-bottom: 10px;
  }}
  .tag {{
    display:inline-block;
    padding: 6px 10px;
    border-radius: 999px;
    background: {BRAND_BG};
    border: 1px solid rgba(16,24,40,0.08);
    color: #101828;
    font-size: 12px;
  }}
  .tag-accent {{
    background: #FFF7ED;
    border: 1px solid rgba(217,192,169,0.55);
  }}
  .muted {{
    color: {BRAND_MUTED};
    font-size: 12px;
  }}

  /* Кнопки */
  .stLinkButton > a {{
    border-radius: 12px !important;
    font-weight: 700 !important;
    border: 1px solid rgba(16,24,40,0.12) !important;
  }}
  .stButton > button {{
    border-radius: 12px !important;
    font-weight: 700 !important;
  }}

  /* Фильтры */
  section[data-testid="stSidebar"] {{
    background: {BRAND_BG};
  }}
</style>
""",
    unsafe_allow_html=True,
)

# =========================
# ЗАГРУЗКА ДАННЫХ
# =========================
@st.cache_data(ttl=300)
def load_data(url: str) -> pd.DataFrame:
    df = pd.read_csv(url)

    # Нормализуем названия колонок на всякий случай
    df.columns = [c.strip() for c in df.columns]

    # Убедимся что есть нужные поля
    expected = [
        "id", "sector", "district", "name", "responsible",
        "status", "work_flag", "address", "card_url", "folder_url"
    ]
    for col in expected:
        if col not in df.columns:
            df[col] = ""

    # Приводим к строкам, чтобы фильтры не ломались из-за NaN
    for c in df.columns:
        df[c] = df[c].astype(str).replace({"nan": "", "None": ""}).fillna("")

    return df


def district_sort_key(x: str):
    """
    Сортировка районов:
    1) г. Курск
    2) Курский район (или Курский)
    3) далее по алфавиту
    """
    s = (x or "").strip()

    # приоритеты (можно расширять)
    if s.lower() in ["г. курск", "город курск", "курск", "г курск"]:
        return (0, "г. курск")
    if s.lower() in ["курский", "курский район", "курский р-н", "курский рн"]:
        return (1, "курский район")

    return (2, s.lower())


def nice_value(v: str, fallback: str = "—") -> str:
    v = (v or "").strip()
    return v if v else fallback


# =========================
# HEADER (с гербом)
# =========================
df = load_data(CSV_URL)

crest_path = Path("assets/crest.png")
left, right = st.columns([1, 12], vertical_alignment="center")
with left:
    if crest_path.exists():
        st.image(str(crest_path), width=74)
    else:
        st.write("")  # если герба нет, просто пусто

with right:
    st.markdown(
        """
<div class="hero">
  <div>
    <h1>Минстрой Курской области • Реестр объектов</h1>
    <p>Единый список объектов 2025–2028 с быстрыми фильтрами и переходом в карточку/папку.</p>
    <span class="pill">Источник данных: Google Sheets (CSV)</span>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

# =========================
# ФИЛЬТРЫ
# =========================
# Уникальные значения
sectors = sorted([s for s in df["sector"].unique() if s.strip()], key=lambda x: x.lower())
districts = sorted([d for d in df["district"].unique() if d.strip()], key=district_sort_key)
statuses = sorted([s for s in df["status"].unique() if s.strip()], key=lambda x: x.lower())

c1, c2, c3 = st.columns([4, 4, 4])
with c1:
    sector_choice = st.selectbox("Отрасль", ["Все"] + sectors, index=0)
with c2:
    district_choice = st.selectbox("Район", ["Все"] + districts, index=0)
with c3:
    status_choice = st.selectbox("Статус", ["Все"] + statuses, index=0)

query = st.text_input("Поиск (ID / наименование / адрес / ответственный)", value="").strip().lower()

# Применяем фильтры
filtered = df.copy()

if sector_choice != "Все":
    filtered = filtered[filtered["sector"].str.strip() == sector_choice]

if district_choice != "Все":
    filtered = filtered[filtered["district"].str.strip() == district_choice]

if status_choice != "Все":
    filtered = filtered[filtered["status"].str.strip() == status_choice]

if query:
    mask = (
        filtered["id"].str.lower().str.contains(query, na=False)
        | filtered["name"].str.lower().str.contains(query, na=False)
        | filtered["address"].str.lower().str.contains(query, na=False)
        | filtered["responsible"].str.lower().str.contains(query, na=False)
    )
    filtered = filtered[mask]

st.caption(f"Показано объектов: **{len(filtered)}** из **{len(df)}**")
st.divider()

# =========================
# КАРТОЧКИ
# =========================
# ВАЖНО: никаких st.write(st.link_button(...)) — иначе Streamlit печатает служебный объект.
# Мы вызываем кнопки напрямую.

# Опционально: если ты добавишь в CSV колонку image_url, мы будем показывать картинку.
has_images = "image_url" in filtered.columns

# Показ по 2 карточки в ряд
cols_per_row = 2
rows = (len(filtered) + cols_per_row - 1) // cols_per_row

items = filtered.to_dict("records")

for r in range(rows):
    row_cols = st.columns(cols_per_row, gap="large")
    for j in range(cols_per_row):
        idx = r * cols_per_row + j
        if idx >= len(items):
            break

        item = items[idx]
        with row_cols[j]:
            # Содержимое карточки
            st.markdown('<div class="card">', unsafe_allow_html=True)

            title = f'{nice_value(item.get("id"))} • {nice_value(item.get("name"))}'
            st.markdown(f'<div class="card-title">{title}</div>', unsafe_allow_html=True)

            sub = f'{nice_value(item.get("sector"))} · {nice_value(item.get("district"))}'
            st.markdown(f'<div class="card-sub">{sub}</div>', unsafe_allow_html=True)

            # Теги
            st.markdown('<div class="kv">', unsafe_allow_html=True)
            st.markdown(f'<span class="tag tag-accent">Статус: {nice_value(item.get("status"))}</span>', unsafe_allow_html=True)
            st.markdown(f'<span class="tag">Работы: {nice_value(item.get("work_flag"))}</span>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown(f'<div class="muted"><b>Адрес:</b> {nice_value(item.get("address"))}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="muted"><b>Ответственный:</b> {nice_value(item.get("responsible"))}</div>', unsafe_allow_html=True)

            # Картинка (если есть image_url)
            if has_images:
                img_url = (item.get("image_url") or "").strip()
                if img_url:
                    st.image(img_url, use_container_width=True)

            # Кнопки
            b1, b2 = st.columns(2)
            with b1:
                card_url = (item.get("card_url") or "").strip()
                if card_url:
                    st.link_button("📄 Открыть карточку", card_url, use_container_width=True)
                else:
                    st.button("📄 Открыть карточку", disabled=True, use_container_width=True)

            with b2:
                folder_url = (item.get("folder_url") or "").strip()
                if folder_url:
                    st.link_button("📁 Открыть папку", folder_url, use_container_width=True)
                else:
                    st.button("📁 Открыть папку", disabled=True, use_container_width=True)

            st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
st.caption("© Минстрой Курской области • Реестр объектов (демо-интерфейс)")
