import base64
import os
from pathlib import Path

import pandas as pd
import streamlit as st


# -----------------------------
# 0) CONFIG
# -----------------------------
st.set_page_config(
    page_title="Реестр объектов",
    page_icon="🏗️",
    layout="wide",
)

ROOT = Path(__file__).parent
ASSETS = ROOT / "assets"
GERB_PATH = ASSETS / "gerb.png"


# -----------------------------
# 1) HELPERS
# -----------------------------
def _b64_image(path: Path) -> str:
    if not path.exists():
        return ""
    data = path.read_bytes()
    return base64.b64encode(data).decode("utf-8")


def inject_global_css():
    st.markdown(
        """
        <style>
          /* делаем контент аккуратным по ширине (как у тебя было красиво) */
          .block-container{
            padding-top: 1.2rem !important;
            padding-bottom: 2.5rem !important;
            max-width: 1180px !important;
          }

          /* скрываем стандартные элементы Streamlit */
          #MainMenu {visibility: hidden;}
          header {visibility: hidden;}
          footer {visibility: hidden;}

          /* иногда снизу есть "водяные" элементы/иконки — стараемся убрать */
          .stDeployButton {display:none !important;}
          a[href*="streamlit.io"] {display:none !important;}
          div[data-testid="stToolbar"] {visibility: hidden; height: 0px;}
          div[data-testid="stDecoration"] {visibility: hidden; height: 0px;}
          div[data-testid="stStatusWidget"] {visibility: hidden; height: 0px;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero_header(gerb_b64: str):
    # Шапка — как у вас “идеальная”: широкая, с градиентом и гербом.
    # ВАЖНО: не ломаем, только фиксируем на 100% ширины контейнера.
    img_html = ""
    if gerb_b64:
        img_html = f"""<img class="hero-gerb" src="data:image/png;base64,{gerb_b64}" alt="Герб"/>"""
    else:
        # если вдруг не найдёт файл, просто аккуратный плейсхолдер
        img_html = """<div class="hero-gerb hero-gerb--ph">герб</div>"""

    st.markdown(
        f"""
        <style>
          .hero-wrap {{
            width: 100%;
            margin: 0 auto 14px auto;
          }}
          .hero {{
            position: relative;
            width: 100%;
            border-radius: 18px;
            padding: 22px 22px;
            background: linear-gradient(135deg, #0b2a57 0%, #1c4a86 55%, #2a5aa3 100%);
            box-shadow: 0 18px 38px rgba(0,0,0,.18);
            overflow: hidden;
          }}
          /* декоративные мягкие пятна справа (как было) */
          .hero:before {{
            content:"";
            position:absolute;
            right:-120px;
            top:-90px;
            width: 340px;
            height: 340px;
            background: rgba(255,255,255,.12);
            border-radius: 999px;
            filter: blur(0px);
          }}
          .hero:after {{
            content:"";
            position:absolute;
            right:-70px;
            bottom:-120px;
            width: 260px;
            height: 260px;
            background: rgba(255,255,255,.10);
            border-radius: 999px;
          }}

          .hero-row {{
            position: relative;
            display:flex;
            gap:18px;
            align-items:flex-start;
            z-index: 2;
          }}

          .hero-gerb {{
            width: 64px;
            height: 64px;
            border-radius: 14px;
            padding: 8px;
            background: rgba(255,255,255,.08);
            border: 1px solid rgba(255,255,255,.12);
            object-fit: contain;
            flex: 0 0 auto;
          }}
          .hero-gerb--ph {{
            display:flex;
            align-items:center;
            justify-content:center;
            color: rgba(255,255,255,.75);
            font-size: 12px;
            font-weight: 600;
          }}

          .hero-titles {{
            flex: 1 1 auto;
            min-width: 0;
          }}
          .hero-ministry {{
            color: rgba(255,255,255,.95);
            font-weight: 800;
            font-size: 20px;
            line-height: 1.15;
            margin-bottom: 6px;
            text-shadow: 0 2px 10px rgba(0,0,0,.25);
          }}
          .hero-app {{
            color: rgba(255,255,255,.95);
            font-weight: 700;
            font-size: 16px;
            margin-bottom: 6px;
          }}
          .hero-sub {{
            color: rgba(255,255,255,.82);
            font-size: 13px;
            line-height: 1.35;
            margin-bottom: 10px;
          }}
          .hero-pill {{
            display:inline-flex;
            gap:8px;
            align-items:center;
            padding: 7px 10px;
            border-radius: 999px;
            background: rgba(0,0,0,.20);
            border: 1px solid rgba(255,255,255,.14);
            color: rgba(255,255,255,.88);
            font-size: 12px;
            width: fit-content;
          }}

          /* адаптация под телефон — шапка не “ужасная”, всё в колонку */
          @media (max-width: 760px) {{
            .block-container{{ max-width: 100% !important; padding-left: 1rem !important; padding-right: 1rem !important; }}
            .hero{{ padding: 18px 16px; }}
            .hero-ministry{{ font-size: 16px; }}
            .hero-app{{ font-size: 14px; }}
            .hero-row{{ align-items:center; }}
          }}
        </style>

        <div class="hero-wrap">
          <div class="hero">
            <div class="hero-row">
              {img_html}
              <div class="hero-titles">
                <div class="hero-ministry">Министерство восстановления, развития приграничья и строительства Курской области</div>
                <div class="hero-app">Реестр объектов</div>
                <div class="hero-sub">Единый список объектов 2025–2028 с быстрыми фильтрами и переходом в карточку/папку.</div>
                <div class="hero-pill">📄 Источник данных: Google Sheets (CSV)</div>
              </div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Приводим колонки к единым именам:
    id, sector, district, name, address, responsible, status, works, card_url, folder_url
    """
    cols = {c: str(c).strip() for c in df.columns}
    df = df.rename(columns=cols).copy()

    # Частые варианты названий в вашем реестре
    mapping_candidates = [
        ("ID", "id"),
        ("Id", "id"),
        ("id", "id"),
        ("Отрасль", "sector"),
        ("отрасль", "sector"),
        ("Район", "district"),
        ("район", "district"),
        ("Наименование_объекта", "name"),
        ("Наименование объекта", "name"),
        ("Наименование", "name"),
        ("Название", "name"),
        ("Адрес", "address"),
        ("адрес", "address"),
        ("Ответственный", "responsible"),
        ("ответственный", "responsible"),
        ("Статус", "status"),
        ("статус", "status"),
        ("Работы", "works"),
        ("работы", "works"),
        ("Ссылка_на_карточку_(Google)", "card_url"),
        ("Ссылка_на_карточку_(Google-форм)", "card_url"),
        ("Ссылка_на_карточку_(GoogleSheet)", "card_url"),
        ("Ссылка_на_карточку_(Go...)", "card_url"),
        ("Ссылка_на_карточку_(Go", "card_url"),
        ("Ссылка_на_карточку", "card_url"),
        ("card_url", "card_url"),
        ("Ссылка_на_папку_(Drive)", "folder_url"),
        ("Ссылка_на_папку", "folder_url"),
        ("folder_url", "folder_url"),
    ]

    # применяем только те ключи, которые реально есть
    rename_map = {}
    for src, dst in mapping_candidates:
        if src in df.columns and dst not in df.columns:
            rename_map[src] = dst
    df = df.rename(columns=rename_map)

    # гарантируем наличие всех нужных колонок
    for col in ["id", "sector", "district", "name", "address", "responsible", "status", "works", "card_url", "folder_url"]:
        if col not in df.columns:
            df[col] = None

    # чистим пробелы
    for col in ["id", "sector", "district", "name", "address", "responsible", "status", "works", "card_url", "folder_url"]:
        df[col] = df[col].astype("string").fillna("").str.strip()

    return df


@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    """
    Источник:
    1) CSV_URL из Secrets (Google Sheets published CSV)
    2) fallback: любой .xlsx в репозитории (если положишь)
    """
    csv_url = (st.secrets.get("CSV_URL", "") or "").strip()

    df = pd.DataFrame()

    # 1) CSV
    if csv_url:
        try:
            df = pd.read_csv(csv_url)
        except Exception:
            df = pd.DataFrame()

    # 2) fallback xlsx (если вдруг надо)
    if df.empty:
        xlsx_files = list(ROOT.glob("*.xlsx"))
        if xlsx_files:
            try:
                df = pd.read_excel(xlsx_files[0])
            except Exception:
                df = pd.DataFrame()

    if df.empty:
        return df

    df = normalize_columns(df)

    # фильтр пустых строк (без названия и без id — мусор)
    df = df[~((df["name"] == "") & (df["id"] == ""))].copy()

    return df


def auth_gate(gerb_b64: str) -> bool:
    """
    Доступ по паролю (через Secrets).
    """
    if "auth_ok" not in st.session_state:
        st.session_state.auth_ok = False

    app_pass = (st.secrets.get("APP_PASSWORD", "") or "").strip()
    if not app_pass:
        # если пароль не задан — не блокируем доступ (чтобы не “сломать”)
        return True

    if st.session_state.auth_ok:
        return True

    # красивый экран входа: та же шапка + карточка
    hero_header(gerb_b64)

    st.markdown(
        """
        <style>
          .login-wrap{
            width: 100%;
            display:flex;
            justify-content:center;
            margin-top: 8px;
          }
          .login-card{
            width: min(720px, 100%);
            border-radius: 18px;
            padding: 18px 18px 12px 18px;
            background: #ffffff;
            border: 1px solid rgba(0,0,0,.08);
            box-shadow: 0 14px 30px rgba(0,0,0,.08);
          }
          .login-title{
            font-size: 18px;
            font-weight: 800;
            margin-bottom: 6px;
            display:flex;
            align-items:center;
            gap:10px;
          }
          .login-sub{
            font-size: 13px;
            color: rgba(0,0,0,.60);
            margin-bottom: 14px;
          }
        </style>

        <div class="login-wrap">
          <div class="login-card">
            <div class="login-title">🔒 Доступ по паролю</div>
            <div class="login-sub">Введите пароль для входа в реестр.</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # input/btn в Streamlit — прямо под карточкой, но визуально в центре
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        pwd = st.text_input("Пароль", type="password", placeholder="Введите пароль…", label_visibility="collapsed")
        if st.button("Войти", use_container_width=True):
            if pwd == app_pass:
                st.session_state.auth_ok = True
                st.rerun()
            else:
                st.error("Неверный пароль.")

    return False


def inject_cards_css():
    st.markdown(
        """
        <style>
          .card-wrap{
            border-radius: 16px;
            background: #ffffff;
            border: 1px solid rgba(0,0,0,.08);
            box-shadow: 0 10px 24px rgba(0,0,0,.06);
            padding: 14px 14px 12px 14px;
            margin: 0 0 14px 0;
          }
          .card-title{
            font-size: 18px;
            font-weight: 800;
            line-height: 1.25;
            margin: 2px 0 8px 0;
          }
          .card-id{
            font-size: 12px;
            color: rgba(0,0,0,.45);
            margin-bottom: 10px;
          }
          .card-grid{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px 18px;
            background: rgba(0,0,0,.03);
            border: 1px solid rgba(0,0,0,.06);
            border-radius: 12px;
            padding: 10px 12px;
            margin-bottom: 10px;
          }
          .card-line{
            display:flex;
            gap: 8px;
            align-items:flex-start;
            font-size: 13px;
            line-height: 1.25;
          }
          .card-line b{ font-weight: 800; }
          .card-badges{
            display:flex;
            gap: 10px;
            flex-wrap: wrap;
            margin: 6px 0 10px 0;
          }
          .badge{
            display:inline-flex;
            gap: 8px;
            align-items:center;
            padding: 6px 10px;
            border-radius: 999px;
            background: #f6f8fb;
            border: 1px solid rgba(0,0,0,.07);
            font-size: 12px;
          }
          .card-actions{
            display:grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
          }

          /* На телефоне — всё в одну колонку и ровно */
          @media (max-width: 760px){
            .card-grid{ grid-template-columns: 1fr; }
            .card-actions{ grid-template-columns: 1fr; }
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def safe_text(x: str) -> str:
    x = (x or "").strip()
    return x if x else "—"


def card_view(row: pd.Series):
    name = safe_text(row.get("name", ""))
    oid = safe_text(row.get("id", ""))
    sector = safe_text(row.get("sector", ""))
    district = safe_text(row.get("district", ""))
    address = safe_text(row.get("address", ""))
    responsible = safe_text(row.get("responsible", ""))
    status = safe_text(row.get("status", ""))
    works = safe_text(row.get("works", ""))
    card_url = (row.get("card_url", "") or "").strip()
    folder_url = (row.get("folder_url", "") or "").strip()

    # HTML каркас карточки (ровная, вытянутая, под фото/доп.поля место есть)
    st.markdown(
        f"""
        <div class="card-wrap">
          <div class="card-title">{name}</div>
          <div class="card-id">ID: {oid}</div>

          <div class="card-grid">
            <div class="card-line">🏷️ <b>Отрасль:</b> {sector}</div>
            <div class="card-line">📍 <b>Район:</b> {district}</div>
            <div class="card-line">🗺️ <b>Адрес:</b> {address}</div>
            <div class="card-line">👤 <b>Ответственный:</b> {responsible}</div>
          </div>

          <div class="card-badges">
            <span class="badge">📌 <b>Статус:</b> {status}</span>
            <span class="badge">🛠️ <b>Работы:</b> {works}</span>
          </div>

          <div style="margin: 8px 0 10px 0; color: rgba(0,0,0,.45); font-size: 12px;">
            Место под фото и дополнительные пункты (заполнишь в реестре — мы красиво выведем позже).
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Кнопки — нативные Streamlit, чтобы ничего не ломать
    a1, a2 = st.columns([1, 1], gap="small")
    with a1:
        if card_url:
            st.link_button("📄 Открыть карточку", card_url, use_container_width=True)
        else:
            st.button("📄 Открыть карточку", disabled=True, use_container_width=True)
    with a2:
        if folder_url:
            st.link_button("📁 Открыть папку", folder_url, use_container_width=True)
        else:
            st.button("📁 Открыть папку", disabled=True, use_container_width=True)


# -----------------------------
# 2) APP
# -----------------------------
def main():
    inject_global_css()

    gerb_b64 = _b64_image(GERB_PATH)

    # ДОСТУП ПО ПАРОЛЮ
    if not auth_gate(gerb_b64):
        return

    # ШАПКА (НЕ ТРОГАЕМ, ФИКСИРУЕМ)
    hero_header(gerb_b64)

    df = load_data()
    if df.empty:
        st.error("Данные не загрузились (реестр пустой). Проверьте CSV_URL в Secrets или наличие .xlsx в репозитории.")
        return

    inject_cards_css()

    # -----------------------------
    # 2.1 Filters (каскадные)
    # -----------------------------
    # 1) Отрасль
    sectors = sorted([s for s in df["sector"].unique().tolist() if str(s).strip()])
    sector_options = ["Все"] + sectors

    # Важно: ключи стабильные, чтобы не было конфликтов state
    f1, f2, f3 = st.columns([1.4, 1.6, 1.4], gap="large")

    with f1:
        sector_sel = st.selectbox("🏷️ Отрасль", sector_options, index=0, key="sector_sel")

    # Подготовка df по отрасли
    df_sector = df.copy()
    if sector_sel != "Все":
        df_sector = df_sector[df_sector["sector"] == sector_sel].copy()

    # 2) Район (только где есть объекты в выбранной отрасли)
    districts = sorted([d for d in df_sector["district"].unique().tolist() if str(d).strip()])
    district_options = ["Все"] + districts
    # если ранее было выбрано значение, которого теперь нет — сбрасываем на "Все"
    prev_d = st.session_state.get("district_sel", "Все")
    district_index = district_options.index(prev_d) if prev_d in district_options else 0

    with f2:
        district_sel = st.selectbox("📍 Район", district_options, index=district_index, key="district_sel")

    df_sd = df_sector.copy()
    if district_sel != "Все":
        df_sd = df_sd[df_sd["district"] == district_sel].copy()

    # 3) Статус (можно также каскадно сузить по отрасли+району)
    statuses = sorted([s for s in df_sd["status"].unique().tolist() if str(s).strip()])
    status_options = ["Все"] + statuses
    prev_s = st.session_state.get("status_sel", "Все")
    status_index = status_options.index(prev_s) if prev_s in status_options else 0

    with f3:
        status_sel = st.selectbox("📌 Статус", status_options, index=status_index, key="status_sel")

    # Поиск
    q = st.text_input("🔎 Поиск (наименование / адрес / ответственный / id)", value="", key="search_q")

    # -----------------------------
    # 2.2 Apply filters
    # -----------------------------
    df_view = df_sd.copy()
    if status_sel != "Все":
        df_view = df_view[df_view["status"] == status_sel].copy()

    if q.strip():
        qq = q.strip().lower()
        mask = (
            df_view["name"].str.lower().str.contains(qq, na=False)
            | df_view["address"].str.lower().str.contains(qq, na=False)
            | df_view["responsible"].str.lower().str.contains(qq, na=False)
            | df_view["id"].str.lower().str.contains(qq, na=False)
        )
        df_view = df_view[mask].copy()

    st.caption(f"Показано объектов: {len(df_view)} из {len(df)}")
    st.markdown("---")

    # -----------------------------
    # 2.3 Cards (ОДНА КОЛОНКА)
    # -----------------------------
    # Сортировка: сначала по отрасли/району/имени (можно поменять позже, но сейчас не трогаем структуру)
    df_view = df_view.sort_values(by=["sector", "district", "name"], na_position="last")

    # Одна колонка, как ты попросил
    for _, row in df_view.iterrows():
        card_view(row)


if __name__ == "__main__":
    main()
