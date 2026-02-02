import base64
import io
import os
import re
from typing import Optional, Tuple

import pandas as pd
import streamlit as st


# =========================
# CONFIG
# =========================
st.set_page_config(
    page_title="Реестр объектов — Курская область",
    page_icon="🏗️",
    layout="wide",
)

ASSETS_GERB_PATH = os.path.join("assets", "gerb.png")

# Колонки реестра (русские названия — как в твоей таблице)
COL_ID = "ID"
COL_SECTOR = "Отрасль"
COL_DISTRICT = "Район"
COL_NAME = "Наименование_объекта"
COL_ADDRESS = "Адрес"
COL_RESP = "Ответственный"
COL_STATUS = "Статус"
COL_WORKS = "Работы"
COL_CARD_URL = "Ссылка_на_карточку_(Google)"
COL_FOLDER_URL = "Ссылка_на_папку_(Drive)"

# Если в CSV вдруг другие названия — можно подстраховаться маппингом:
ALIASES = {
    COL_ID: ["id", "ID", "Id"],
    COL_SECTOR: ["Отрасль", "sector", "Sector"],
    COL_DISTRICT: ["Район", "district", "District"],
    COL_NAME: ["Наименование_объекта", "name", "Наименование", "Объект", "Наименование объекта"],
    COL_ADDRESS: ["Адрес", "address", "Адрес объекта"],
    COL_RESP: ["Ответственный", "responsible", "Ответственные"],
    COL_STATUS: ["Статус", "status", "Состояние"],
    COL_WORKS: ["Работы", "works", "Виды работ"],
    COL_CARD_URL: ["Ссылка_на_карточку_(Google)", "card_url", "Ссылка на карточку", "Ссылка_на_карточку"],
    COL_FOLDER_URL: ["Ссылка_на_папку_(Drive)", "folder_url", "Ссылка на папку", "Ссылка_на_папку"],
}


# =========================
# HELPERS
# =========================
def _first_existing_column(df: pd.DataFrame, options: list[str]) -> Optional[str]:
    cols = set(df.columns)
    for c in options:
        if c in cols:
            return c
    return None


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Приводим входные названия колонок к нашим "каноничным" русским именам.
    Ничего не удаляем — только создаём/переименовываем.
    """
    df = df.copy()

    rename_map = {}
    for canonical, variants in ALIASES.items():
        existing = _first_existing_column(df, variants)
        if existing and existing != canonical:
            rename_map[existing] = canonical

    if rename_map:
        df = df.rename(columns=rename_map)

    # Гарантируем наличие ключевых колонок (если нет — создаём пустые)
    for must in [COL_ID, COL_SECTOR, COL_DISTRICT, COL_NAME]:
        if must not in df.columns:
            df[must] = ""

    # Остальные — опционально, но для карточек лучше иметь
    for opt in [COL_ADDRESS, COL_RESP, COL_STATUS, COL_WORKS, COL_CARD_URL, COL_FOLDER_URL]:
        if opt not in df.columns:
            df[opt] = ""

    # Чистим пробелы
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].astype(str).str.strip()

    return df


@st.cache_data(show_spinner=False)
def load_data() -> Tuple[pd.DataFrame, str]:
    """
    Источник:
    1) st.secrets["CSV_URL"] (Google Sheets pub?output=csv)
    2) fallback: первый .xlsx в корне репо (если вдруг понадобится)
    """
    csv_url = None
    try:
        csv_url = st.secrets.get("CSV_URL", "").strip()
    except Exception:
        csv_url = ""

    if csv_url:
        try:
            df = pd.read_csv(csv_url)
            df = normalize_columns(df)
            return df, "google_sheets"
        except Exception as e:
            # упадём ниже на fallback
            pass

    # fallback: xlsx в репозитории (не обязателен)
    xlsx_files = [f for f in os.listdir(".") if f.lower().endswith(".xlsx")]
    if xlsx_files:
        try:
            df = pd.read_excel(xlsx_files[0])
            df = normalize_columns(df)
            return df, "xlsx"
        except Exception:
            pass

    return pd.DataFrame(), "empty"


def to_b64_image(path: str) -> Optional[str]:
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode("utf-8")


def safe_text(x: str) -> str:
    if x is None:
        return ""
    x = str(x).strip()
    return "" if x.lower() in ("nan", "none") else x


def contains_query(row: pd.Series, q: str) -> bool:
    if not q:
        return True
    ql = q.lower().strip()
    if not ql:
        return True
    # Ищем по имени/адресу/ответственному/id
    hay = " | ".join(
        [
            safe_text(row.get(COL_NAME, "")),
            safe_text(row.get(COL_ADDRESS, "")),
            safe_text(row.get(COL_RESP, "")),
            safe_text(row.get(COL_ID, "")),
        ]
    ).lower()
    return ql in hay


def init_auth():
    if "auth_ok" not in st.session_state:
        st.session_state.auth_ok = False


def check_password(pw: str) -> bool:
    try:
        target = st.secrets.get("APP_PASSWORD", "")
    except Exception:
        target = ""
    return bool(target) and pw == target


# =========================
# STYLES (ШАПКА + КАРТОЧКИ)
# =========================
GERB_B64 = to_b64_image(ASSETS_GERB_PATH)

BASE_CSS = f"""
<style>
/* Глобально — аккуратные отступы */
.main .block-container {{
    padding-top: 1.6rem;
    padding-bottom: 3rem;
    max-width: 1120px;
}}

/* Убираем лишние элементы Streamlit */
header[data-testid="stHeader"] {{
    background: transparent;
}}
div[data-testid="stToolbar"] {{
    visibility: hidden;
    height: 0px;
}}

/* HERO (как на твоём "идеале") */
.hero-wrap {{
    width: 100%;
    display: flex;
    justify-content: center;
    margin-top: 0.2rem;
    margin-bottom: 1.2rem;
}}
.hero {{
    width: 100%;
    border-radius: 18px;
    overflow: hidden;
    box-shadow: 0 12px 30px rgba(16, 24, 40, 0.20);
    background: linear-gradient(135deg, #0b2b57 0%, #174a8b 55%, #2b5ca1 100%);
    position: relative;
}}
.hero::after {{
    content: "";
    position: absolute;
    right: -110px;
    top: -120px;
    width: 320px;
    height: 320px;
    background: rgba(255,255,255,0.14);
    border-radius: 50%;
}}
.hero::before {{
    content: "";
    position: absolute;
    right: -10px;
    bottom: -140px;
    width: 360px;
    height: 360px;
    background: rgba(255,255,255,0.10);
    border-radius: 50%;
}}
.hero-row {{
    position: relative;
    z-index: 1;
    display: flex;
    gap: 16px;
    align-items: flex-start;
    padding: 18px 22px;
}}
.hero-crest {{
    width: 54px;
    height: 54px;
    border-radius: 12px;
    background: rgba(255,255,255,0.10);
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 0 0 auto;
    border: 1px solid rgba(255,255,255,0.12);
}}
.hero-crest img {{
    width: 44px;
    height: 44px;
    object-fit: contain;
}}
.hero-titles {{
    color: #fff;
    line-height: 1.2;
}}
.hero-ministry {{
    font-size: 18px;
    font-weight: 800;
    margin-bottom: 6px;
}}
.hero-app {{
    font-size: 14px;
    font-weight: 700;
    opacity: 0.95;
    margin-bottom: 6px;
}}
.hero-sub {{
    font-size: 12px;
    opacity: 0.9;
    margin-bottom: 10px;
}}
.hero-pill {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 10px;
    border-radius: 999px;
    font-size: 12px;
    background: rgba(255,255,255,0.12);
    border: 1px solid rgba(255,255,255,0.14);
    width: fit-content;
}}
.hero-pill b {{
    font-weight: 700;
}}

/* Фильтры */
.filters-wrap {{
    margin-top: 0.4rem;
    margin-bottom: 0.6rem;
}}
.small-muted {{
    color: rgba(17, 24, 39, 0.55);
    font-size: 12px;
}}

/* Карточки — один столбец, ровно, красиво */
.card {{
    border: 1px solid rgba(17, 24, 39, 0.10);
    border-radius: 14px;
    padding: 16px 16px 14px 16px;
    background: #fff;
    box-shadow: 0 4px 14px rgba(16,24,40,0.06);
    margin-bottom: 14px;
}}
.card-title {{
    font-size: 20px;
    font-weight: 800;
    margin: 0 0 10px 0;
}}
.card-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px 16px;
    padding: 12px;
    border-radius: 12px;
    background: rgba(17, 24, 39, 0.03);
    border: 1px solid rgba(17, 24, 39, 0.06);
}}
.kv {{
    display: flex;
    gap: 8px;
    align-items: flex-start;
    font-size: 13px;
}}
.kv b {{
    font-weight: 800;
}}
.badges {{
    display: flex;
    gap: 10px;
    margin-top: 10px;
}}
.badge {{
    display: inline-flex;
    gap: 8px;
    align-items: center;
    padding: 6px 10px;
    border-radius: 999px;
    border: 1px solid rgba(17, 24, 39, 0.10);
    background: rgba(59, 130, 246, 0.06);
    font-size: 12px;
}}
.card-actions {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-top: 12px;
}}
.card-footnote {{
    margin-top: 10px;
    padding-top: 10px;
    border-top: 1px dashed rgba(17, 24, 39, 0.15);
    color: rgba(17, 24, 39, 0.55);
    font-size: 12px;
}}

/* Password box */
.auth-wrap {{
    width: 100%;
    display: flex;
    justify-content: center;
    margin-top: 0.2rem;
}}
.auth-card {{
    width: min(720px, 96%);
    border-radius: 16px;
    background: #fff;
    border: 1px solid rgba(17, 24, 39, 0.10);
    box-shadow: 0 10px 26px rgba(16,24,40,0.10);
    padding: 18px 18px 6px 18px;
}}
.auth-title {{
    font-size: 18px;
    font-weight: 900;
    margin-bottom: 4px;
}}
.auth-sub {{
    font-size: 13px;
    color: rgba(17, 24, 39, 0.65);
    margin-bottom: 12px;
}}
</style>
"""

st.markdown(BASE_CSS, unsafe_allow_html=True)


def render_hero(show_source_pill: bool = True):
    gerb_html = ""
    if GERB_B64:
        gerb_html = f'<img src="data:image/png;base64,{GERB_B64}" alt="gerb" />'

    pill = ""
    if show_source_pill:
        pill = '<div class="hero-pill">🗂️ <b>Источник данных:</b> Google Sheets (CSV)</div>'

    html = f"""
    <div class="hero-wrap">
      <div class="hero">
        <div class="hero-row">
          <div class="hero-crest">{gerb_html}</div>
          <div class="hero-titles">
            <div class="hero-ministry">Министерство восстановления, развития приграничья и строительства Курской области</div>
            <div class="hero-app">Реестр объектов</div>
            <div class="hero-sub">Единый список объектов 2025–2028 с быстрыми фильтрами и переходом в карточку/папку.</div>
            {pill}
          </div>
        </div>
      </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_card(row: pd.Series):
    name = safe_text(row.get(COL_NAME, ""))
    obj_id = safe_text(row.get(COL_ID, ""))
    sector = safe_text(row.get(COL_SECTOR, ""))
    district = safe_text(row.get(COL_DISTRICT, ""))
    addr = safe_text(row.get(COL_ADDRESS, ""))
    resp = safe_text(row.get(COL_RESP, ""))
    status = safe_text(row.get(COL_STATUS, ""))
    works = safe_text(row.get(COL_WORKS, ""))
    card_url = safe_text(row.get(COL_CARD_URL, ""))
    folder_url = safe_text(row.get(COL_FOLDER_URL, ""))

    # Если в каких-то строках адрес/название "путаются" — мы НЕ переставляем поля местами,
    # просто показываем как есть. Ты потом в реестре дополнишь корректно.

    # Заглушки
    status_show = status if status else "—"
    works_show = works if works else "—"
    sector_show = sector if sector else "—"
    district_show = district if district else "—"
    addr_show = addr if addr else "—"
    resp_show = resp if resp else "—"

    card_html = f"""
    <div class="card">
      <div class="card-title">{name}</div>

      <div class="card-grid">
        <div class="kv">🏷️ <b>Отрасль:</b> {sector_show}</div>
        <div class="kv">📍 <b>Район:</b> {district_show}</div>
        <div class="kv">🗺️ <b>Адрес:</b> {addr_show}</div>
        <div class="kv">👤 <b>Ответственный:</b> {resp_show}</div>
      </div>

      <div class="badges">
        <div class="badge">📌 <b>Статус:</b> {status_show}</div>
        <div class="badge">🛠️ <b>Работы:</b> {works_show}</div>
      </div>

      <div class="card-actions">
        <div>
          {"<a href='" + card_url + "' target='_blank'><button style='width:100%; padding:10px; border-radius:10px; border:1px solid rgba(17,24,39,0.20); background:#fff; cursor:pointer;'>📄 Открыть карточку</button></a>" if card_url else "<button style='width:100%; padding:10px; border-radius:10px; border:1px solid rgba(17,24,39,0.10); background:rgba(17,24,39,0.03); color:rgba(17,24,39,0.45);' disabled>📄 Открыть карточку</button>"}
        </div>
        <div>
          {"<a href='" + folder_url + "' target='_blank'><button style='width:100%; padding:10px; border-radius:10px; border:1px solid rgba(17,24,39,0.20); background:#fff; cursor:pointer;'>📁 Открыть папку</button></a>" if folder_url else "<button style='width:100%; padding:10px; border-radius:10px; border:1px solid rgba(17,24,39,0.10); background:rgba(17,24,39,0.03); color:rgba(17,24,39,0.45);' disabled>📁 Открыть папку</button>"}
        </div>
      </div>

      <div class="card-footnote">
        Место под фото и дополнительные пункты (заполнишь в реестре — мы красиво выведем позже).
      </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)


# =========================
# AUTH SCREEN
# =========================
def render_auth_screen():
    # Шапка остаётся, но БЕЗ "Источник данных"
    render_hero(show_source_pill=False)

    st.markdown(
        """
        <div class="auth-wrap">
          <div class="auth-card">
            <div class="auth-title">🔒 Доступ по паролю</div>
            <div class="auth-sub">Введите пароль для входа в реестр.</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Делаем поля под карточкой аккуратно и по центру
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        pw = st.text_input("Пароль", type="password", label_visibility="collapsed", placeholder="Введите пароль…")
        btn = st.button("Войти", use_container_width=True)

        if btn:
            if check_password(pw):
                st.session_state.auth_ok = True
                st.rerun()
            else:
                st.error("Неверный пароль.")


# =========================
# MAIN APP
# =========================
def main():
    init_auth()

    if not st.session_state.auth_ok:
        render_auth_screen()
        return

    # В основной части — шапка с "Источник данных"
    render_hero(show_source_pill=True)

    df, source = load_data()
    if df.empty:
        st.error("Данные не загрузились (реестр пустой). Проверьте CSV_URL в Secrets или наличие .xlsx в репозитории.")
        return

    # Уникальные значения
    sectors_all = sorted([s for s in df[COL_SECTOR].dropna().astype(str).unique().tolist() if s and s.lower() != "nan"])
    districts_all = sorted([d for d in df[COL_DISTRICT].dropna().astype(str).unique().tolist() if d and d.lower() != "nan"])
    statuses_all = sorted([s for s in df[COL_STATUS].dropna().astype(str).unique().tolist() if s and s.lower() != "nan"])

    # =========================
    # FILTERS (с зависимым районом)
    # =========================
    st.markdown('<div class="filters-wrap"></div>', unsafe_allow_html=True)

    f1, f2, f3 = st.columns([2, 2, 2])
    with f1:
        sector_sel = st.selectbox("🏷️ Отрасль", ["Все"] + sectors_all, index=0)
    # Зависимый список районов: если выбрали отрасль — районы только по этой отрасли
    df_for_districts = df.copy()
    if sector_sel != "Все":
        df_for_districts = df_for_districts[df_for_districts[COL_SECTOR] == sector_sel]
    districts_dynamic = sorted(
        [d for d in df_for_districts[COL_DISTRICT].dropna().astype(str).unique().tolist() if d and d.lower() != "nan"]
    )

    with f2:
        district_sel = st.selectbox("📍 Район", ["Все"] + districts_dynamic, index=0)
    with f3:
        status_sel = st.selectbox("📌 Статус", ["Все"] + statuses_all, index=0)

    q = st.text_input("🔎 Поиск (наименование / адрес / ответственный / id)", value="")

    # =========================
    # APPLY FILTERS
    # =========================
    filtered = df.copy()

    if sector_sel != "Все":
        filtered = filtered[filtered[COL_SECTOR] == sector_sel]

    if district_sel != "Все":
        filtered = filtered[filtered[COL_DISTRICT] == district_sel]

    if status_sel != "Все":
        filtered = filtered[filtered[COL_STATUS] == status_sel]

    if q.strip():
        mask = filtered.apply(lambda r: contains_query(r, q), axis=1)
        filtered = filtered[mask]

    st.markdown(f'<div class="small-muted">Показано объектов: {len(filtered)} из {len(df)}</div>', unsafe_allow_html=True)
    st.divider()

    # =========================
    # CARDS — ОДНА КОЛОНКА
    # =========================
    # Чтобы порядок был стабильный: сначала по отрасли/району/ID (если нужно)
    # Сейчас — просто как в таблице.
    for _, row in filtered.iterrows():
        render_card(row)


if __name__ == "__main__":
    main()
