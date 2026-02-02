import base64
from pathlib import Path

import pandas as pd
import requests
import streamlit as st


# ---------------------------
# CONFIG
# ---------------------------
st.set_page_config(
    page_title="Реестр объектов — Курская область",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed",
)

ASSETS_DIR = Path(__file__).parent / "assets"
GERB_PATH = ASSETS_DIR / "gerb.png"


# ---------------------------
# HELPERS
# ---------------------------
def _b64_image(path: Path) -> str:
    if not path.exists():
        return ""
    data = path.read_bytes()
    return base64.b64encode(data).decode("utf-8")


def inject_global_css():
    st.markdown(
        """
<style>
/* Общая геометрия */
.block-container{
    padding-top: 28px !important;
    padding-bottom: 40px !important;
    max-width: 1150px !important;
}
@media (max-width: 900px){
    .block-container{ max-width: 900px !important; padding-top: 14px !important; }
}

/* Убираем “лишние” поля Streamlit */
header[data-testid="stHeader"]{ background: transparent; }
div[data-testid="stToolbar"]{ visibility: hidden; height: 0px; }
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* HERO */
.hero-wrap{
    width: 100%;
    margin: 0 auto 18px auto;
}
.hero{
    position: relative;
    border-radius: 18px;
    padding: 20px 22px;
    color: #fff;
    overflow: hidden;
    box-shadow: 0 14px 34px rgba(0,0,0,.18);
    background: linear-gradient(135deg, #0B2B54 0%, #11417A 55%, #1B5AA7 100%);
}
.hero::after{
    content:"";
    position:absolute;
    right:-120px;
    top:-120px;
    width: 420px;
    height: 420px;
    border-radius: 50%;
    background: rgba(255,255,255,.18);
    filter: blur(0px);
}
.hero::before{
    content:"";
    position:absolute;
    right:-40px;
    top:80px;
    width: 240px;
    height: 240px;
    border-radius: 50%;
    background: rgba(255,255,255,.12);
}
.hero-row{
    position: relative;
    display:flex;
    gap:14px;
    align-items:flex-start;
}
.hero-crest{
    width: 64px;
    height: 64px;
    border-radius: 14px;
    background: rgba(255,255,255,.10);
    border: 1px solid rgba(255,255,255,.18);
    display:flex;
    align-items:center;
    justify-content:center;
    flex: 0 0 auto;
}
.hero-crest img{
    width: 46px;
    height: 46px;
    object-fit: contain;
}
.hero-titles{ flex:1; min-width: 0; }
.hero-ministry{
    font-weight: 800;
    font-size: 18px;
    line-height: 1.2;
    margin-bottom: 6px;
    letter-spacing: .2px;
}
.hero-app{
    font-weight: 700;
    font-size: 14px;
    opacity: .95;
    margin-bottom: 4px;
}
.hero-sub{
    font-size: 12.5px;
    opacity: .90;
    margin-bottom: 10px;
}
.hero-pill{
    display:inline-flex;
    gap:8px;
    align-items:center;
    padding: 7px 12px;
    border-radius: 999px;
    background: rgba(255,255,255,.12);
    border: 1px solid rgba(255,255,255,.20);
    font-size: 12px;
    width: fit-content;
}
.hero-pill b{ font-weight: 800; }

/* Мобильная адаптация HERO */
@media (max-width: 700px){
    .hero{ padding: 18px 16px; border-radius: 18px; }
    .hero-row{ gap: 12px; }
    .hero-crest{ width: 58px; height: 58px; border-radius: 14px; }
    .hero-crest img{ width: 42px; height: 42px; }
    .hero-ministry{ font-size: 18px; }
}

/* ФИЛЬТРЫ */
.filters-wrap{
    margin: 12px 0 4px 0;
}
.small-muted{
    font-size: 12px;
    color: rgba(0,0,0,.55);
}

/* КАРТОЧКИ */
.card{
    background: #fff;
    border: 1px solid rgba(0,0,0,.08);
    border-radius: 18px;
    padding: 16px 16px 14px 16px;
    margin: 14px 0;
    box-shadow: 0 10px 26px rgba(0,0,0,.06);
}
.card-title{
    font-size: 18px;
    font-weight: 850;
    margin: 0 0 10px 0;
    line-height: 1.25;
}
.card-kv{
    background: rgba(0,0,0,.025);
    border: 1px solid rgba(0,0,0,.06);
    border-radius: 14px;
    padding: 10px 12px;
}
.kv-grid{
    display:flex;
    flex-wrap: wrap;
    gap: 10px 14px;
}
.kv-item{
    display:flex;
    align-items:flex-start;
    gap: 8px;
    min-width: 240px;
    flex: 1 1 240px;
}
.kv-ic{ width: 18px; text-align:center; margin-top: 2px; }
.kv-label{ font-weight: 800; margin-right: 6px; }
.kv-val{ opacity: .95; }

.badges{
    display:flex;
    gap: 10px;
    flex-wrap: wrap;
    margin: 10px 0 10px 0;
}
.badge{
    display:inline-flex;
    align-items:center;
    gap: 8px;
    padding: 7px 12px;
    border-radius: 999px;
    border: 1px solid rgba(27,90,167,.25);
    background: rgba(27,90,167,.08);
    font-size: 12.5px;
    width: fit-content;
}
.badge b{ font-weight: 850; }

.btn-row{
    display:flex;
    gap: 12px;
    flex-wrap: wrap;
    margin-top: 10px;
}
.a-btn{
    flex: 1 1 260px;
    text-decoration:none !important;
    display:inline-flex;
    align-items:center;
    justify-content:center;
    gap: 10px;
    padding: 12px 14px;
    border-radius: 12px;
    border: 1px solid rgba(0,0,0,.12);
    background: #fff;
    color: #111 !important;
    font-weight: 800;
}
.a-btn:hover{
    background: rgba(0,0,0,.02);
    border-color: rgba(0,0,0,.18);
}
.note{
    margin-top: 10px;
    padding-top: 10px;
    border-top: 1px dashed rgba(0,0,0,.10);
    font-size: 12.5px;
    color: rgba(0,0,0,.55);
}

/* ТЁМНАЯ ТЕМА (мобильный Streamlit часто показывает темнее) */
@media (prefers-color-scheme: dark){
    .small-muted{ color: rgba(255,255,255,.65); }
    .card{
        background: rgba(255,255,255,.04);
        border: 1px solid rgba(255,255,255,.10);
        box-shadow: 0 10px 28px rgba(0,0,0,.35);
    }
    .card-title{ color: rgba(255,255,255,.92); }
    .card-kv{
        background: rgba(255,255,255,.03);
        border: 1px solid rgba(255,255,255,.08);
    }
    .kv-val{ color: rgba(255,255,255,.86); }
    .kv-label{ color: rgba(255,255,255,.92); }
    .badge{
        border: 1px solid rgba(120,170,255,.22);
        background: rgba(120,170,255,.10);
        color: rgba(255,255,255,.90);
    }
    .a-btn{
        background: rgba(255,255,255,.03);
        border: 1px solid rgba(255,255,255,.12);
        color: rgba(255,255,255,.92) !important;
    }
    .a-btn:hover{ background: rgba(255,255,255,.06); }
    .note{ color: rgba(255,255,255,.60); border-top-color: rgba(255,255,255,.12); }
}
</style>
        """,
        unsafe_allow_html=True,
    )


def render_hero(show_source: bool = True):
    crest_b64 = _b64_image(GERB_PATH)
    crest_html = (
        f'<img src="data:image/png;base64,{crest_b64}" alt="Герб" />' if crest_b64 else ""
    )

    source_pill = ""
    if show_source:
        source_pill = """
        <div class="hero-pill">
            <span style="opacity:.95;">🗂️</span>
            <b>Источник данных:</b>
            <span style="opacity:.95;">Google Sheets (CSV)</span>
        </div>
        """

    st.markdown(
        f"""
<div class="hero-wrap">
  <div class="hero">
    <div class="hero-row">
      <div class="hero-crest">{crest_html}</div>
      <div class="hero-titles">
        <div class="hero-ministry">Министерство восстановления, развития приграничья и строительства Курской области</div>
        <div class="hero-app">Реестр объектов</div>
        <div class="hero-sub">Единый список объектов 2025–2028 с быстрыми фильтрами и переходом в карточку/папку.</div>
        {source_pill}
      </div>
    </div>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False, ttl=300)
def load_data() -> pd.DataFrame:
    """
    Загружаем реестр:
    - приоритет: st.secrets["CSV_URL"]
    - fallback: local xlsx (если вдруг нужно)
    """
    csv_url = None
    if "CSV_URL" in st.secrets:
        csv_url = st.secrets["CSV_URL"]

    if csv_url:
        r = requests.get(csv_url, timeout=25)
        r.raise_for_status()
        # Важно: читать через bytes -> корректнее для кодировок
        from io import BytesIO

        bio = BytesIO(r.content)
        df = pd.read_csv(bio)
        return df

    # fallback на локальный xlsx (если когда-то используете)
    for name in ["реестр.xlsx", "registry.xlsx", "РЕЕСТР.xlsx"]:
        p = Path(__file__).parent / name
        if p.exists():
            return pd.read_excel(p)

    return pd.DataFrame()


def norm_col(df: pd.DataFrame, variants: list[str], target: str) -> pd.DataFrame:
    """
    Приводим разные названия колонок к единым, если в реестре они отличаются.
    """
    if target in df.columns:
        return df
    for v in variants:
        if v in df.columns:
            df = df.rename(columns={v: target})
            return df
    df[target] = ""
    return df


def clean_text(x) -> str:
    if pd.isna(x):
        return ""
    s = str(x).strip()
    if s.lower() == "nan":
        return ""
    return s


def build_filters(df: pd.DataFrame):
    """
    Фильтры делаем “каскадно”:
    - Отрасль влияет на доступные Районы и Статусы
    - Район влияет на доступные Статусы
    """
    st.markdown('<div class="filters-wrap">', unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 1, 1], gap="large")

    # 1) Отрасль
    with c1:
        sector_all = sorted({clean_text(x) for x in df["sector"].tolist() if clean_text(x)})
        sector_opts = ["Все"] + sector_all
        sector = st.selectbox("🏷️ Отрасль", sector_opts, index=0)

    # подфильтр по отрасли
    df1 = df.copy()
    if sector != "Все":
        df1 = df1[df1["sector"].astype(str) == sector]

    # 2) Район (только те, где есть объекты после выбора отрасли)
    with c2:
        dist_all = sorted({clean_text(x) for x in df1["district"].tolist() if clean_text(x)})
        dist_opts = ["Все"] + dist_all
        district = st.selectbox("📍 Район", dist_opts, index=0)

    df2 = df1.copy()
    if district != "Все":
        df2 = df2[df2["district"].astype(str) == district]

    # 3) Статус (после отрасли+района)
    with c3:
        status_all = sorted({clean_text(x) for x in df2["status"].tolist() if clean_text(x)})
        status_opts = ["Все"] + status_all
        status = st.selectbox("📌 Статус", status_opts, index=0)

    # Поиск
    q = st.text_input("🔎 Поиск (наименование / адрес / ответственный / id)", value="")

    st.markdown("</div>", unsafe_allow_html=True)
    return sector, district, status, q


def apply_filters(df: pd.DataFrame, sector: str, district: str, status: str, q: str) -> pd.DataFrame:
    out = df.copy()

    if sector != "Все":
        out = out[out["sector"].astype(str) == sector]
    if district != "Все":
        out = out[out["district"].astype(str) == district]
    if status != "Все":
        out = out[out["status"].astype(str) == status]

    if q.strip():
        qq = q.strip().lower()
        search_cols = ["name", "address", "responsible", "id"]
        mask = False
        for c in search_cols:
            if c in out.columns:
                mask = mask | out[c].astype(str).str.lower().str.contains(qq, na=False)
        out = out[mask]

    return out


def render_card(row: pd.Series):
    name = clean_text(row.get("name", ""))
    sector = clean_text(row.get("sector", ""))
    district = clean_text(row.get("district", ""))
    address = clean_text(row.get("address", ""))
    responsible = clean_text(row.get("responsible", ""))
    status = clean_text(row.get("status", ""))
    works = clean_text(row.get("works", ""))
    card_url = clean_text(row.get("card_url", ""))
    folder_url = clean_text(row.get("folder_url", ""))

    # Значения по умолчанию (чтобы красиво выглядело)
    status_show = status if status else "—"
    works_show = works if works else "—"

    # Кнопки: если ссылки нет — делаем неактивную “пустышку”
    def btn_html(label: str, icon: str, url: str) -> str:
        if url:
            return f'<a class="a-btn" href="{url}" target="_blank" rel="noopener noreferrer">{icon} {label}</a>'
        return f'<span class="a-btn" style="opacity:.45; cursor:not-allowed;">{icon} {label}</span>'

    st.markdown(
        f"""
<div class="card">
  <div class="card-title">{name}</div>

  <div class="card-kv">
    <div class="kv-grid">
      <div class="kv-item">
        <div class="kv-ic">🏷️</div>
        <div><span class="kv-label">Отрасль:</span><span class="kv-val">{sector if sector else "—"}</span></div>
      </div>
      <div class="kv-item">
        <div class="kv-ic">📍</div>
        <div><span class="kv-label">Район:</span><span class="kv-val">{district if district else "—"}</span></div>
      </div>
      <div class="kv-item">
        <div class="kv-ic">🗺️</div>
        <div><span class="kv-label">Адрес:</span><span class="kv-val">{address if address else "—"}</span></div>
      </div>
      <div class="kv-item">
        <div class="kv-ic">👤</div>
        <div><span class="kv-label">Ответственный:</span><span class="kv-val">{responsible if responsible else "—"}</span></div>
      </div>
    </div>
  </div>

  <div class="badges">
    <div class="badge">📌 <b>Статус:</b> {status_show}</div>
    <div class="badge">🛠️ <b>Работы:</b> {works_show}</div>
  </div>

  <div class="btn-row">
    {btn_html("Открыть карточку", "📄", card_url)}
    {btn_html("Открыть папку", "📁", folder_url)}
  </div>

  <div class="note">Место под фото и дополнительные пункты (заполнишь в реестре — мы красиво выведем позже).</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def password_gate() -> bool:
    """
    Вход по паролю.
    Пароль хранить в Streamlit Secrets:
    APP_PASSWORD = "ваш_пароль"
    """
    if st.session_state.get("auth_ok"):
        return True

    app_pass = st.secrets.get("APP_PASSWORD", "")
    if not app_pass:
        # если пароль не задан — не блокируем
        st.session_state["auth_ok"] = True
        return True

    # Шапка на экране пароля — БЕЗ “Источник данных”
    render_hero(show_source=False)

    st.markdown(
        """
<div class="card" style="max-width: 760px; margin: 16px auto 0 auto;">
  <div class="card-title" style="font-size:16px; margin-bottom:8px;">🔒 Доступ по паролю</div>
  <div style="opacity:.70; margin-bottom:10px;">Введите пароль для входа в реестр.</div>
</div>
        """,
        unsafe_allow_html=True,
    )

    # Ввод пароля
    pw = st.text_input("Пароль", type="password", label_visibility="collapsed", placeholder="Введите пароль…")
    colb1, colb2, colb3 = st.columns([1, 1, 1])
    with colb2:
        btn = st.button("Войти", use_container_width=True)

    if btn:
        if pw == app_pass:
            st.session_state["auth_ok"] = True
            st.rerun()
        else:
            st.error("Неверный пароль.")

    return False


# ---------------------------
# MAIN
# ---------------------------
inject_global_css()

# 1) Парольный доступ
if not password_gate():
    st.stop()

# 2) Основная шапка (с источником)
render_hero(show_source=True)

# 3) Данные
try:
    df = load_data()
except Exception:
    df = pd.DataFrame()

# 4) Приведение колонок под единый стандарт
# Подстройка под ваши возможные имена столбцов в реестре:
if df is None or df.empty:
    st.warning("Данные не загрузились (реестр пустой). Проверьте CSV_URL в Secrets или доступ к таблице.")
    st.stop()

df = norm_col(df, ["Отрасль", "отрасль", "sector", "Сектор"], "sector")
df = norm_col(df, ["Район", "район", "district", "Муниципалитет"], "district")
df = norm_col(df, ["Статус", "статус", "status"], "status")
df = norm_col(df, ["Наименование", "наименование", "name", "Объект"], "name")
df = norm_col(df, ["Адрес", "адрес", "address"], "address")
df = norm_col(df, ["Ответственный", "ответственный", "responsible", "Куратор"], "responsible")
df = norm_col(df, ["Работы", "работы", "works"], "works")
df = norm_col(df, ["ID", "id", "Id"], "id")
df = norm_col(df, ["Ссылка на карточку", "card_url", "Карточка", "card"], "card_url")
df = norm_col(df, ["Ссылка на папку", "folder_url", "Папка", "folder"], "folder_url")

# 5) Фильтры
sector, district, status, q = build_filters(df)

# 6) Применяем фильтры
filtered = apply_filters(df, sector, district, status, q)

st.markdown(f'<div class="small-muted">Показано объектов: <b>{len(filtered)}</b> из <b>{len(df)}</b></div>', unsafe_allow_html=True)
st.divider()

# 7) Вывод карточек (одна колонка — как вы просили)
if filtered.empty:
    st.info("По выбранным фильтрам объектов не найдено.")
else:
    # Стабильный порядок
    filtered = filtered.reset_index(drop=True)
    for _, row in filtered.iterrows():
        render_card(row)
