import streamlit as st
import pandas as pd
import base64
from pathlib import Path

# -----------------------------
# Конфиг страницы
# -----------------------------
st.set_page_config(
    page_title="Реестр объектов — Курская область",
    page_icon="🏛️",
    layout="wide",
)

# -----------------------------
# Настройки / Secrets
# -----------------------------
CSV_URL = st.secrets.get("CSV_URL", "").strip()
APP_PASSWORD = str(st.secrets.get("APP_PASSWORD", "")).strip()  # обязательно задайте в Secrets

# -----------------------------
# Утилиты
# -----------------------------
def _read_file_b64(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    return base64.b64encode(p.read_bytes()).decode("utf-8")


def _norm(s: str) -> str:
    return str(s).strip().lower()


def _pick_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """
    Ищем колонку по списку возможных названий (в разных вариантах).
    """
    cols = list(df.columns)
    norm_map = {_norm(c): c for c in cols}

    for cand in candidates:
        c = norm_map.get(_norm(cand))
        if c:
            return c

    # мягкий поиск по вхождению
    for c in cols:
        cn = _norm(c)
        for cand in candidates:
            if _norm(cand) in cn:
                return c
    return None


@st.cache_data(ttl=300, show_spinner=False)
def load_data(csv_url: str) -> pd.DataFrame:
    if not csv_url:
        return pd.DataFrame()

    try:
        df = pd.read_csv(csv_url)
    except Exception:
        # иногда Google отдаёт ; вместо ,
        try:
            df = pd.read_csv(csv_url, sep=";")
        except Exception:
            return pd.DataFrame()

    # Убираем полностью пустые строки
    df = df.dropna(how="all").copy()

    # Приводим имена колонок к строкам
    df.columns = [str(c).strip() for c in df.columns]

    return df


def css():
    st.markdown(
        """
        <style>
          /* Общие */
          .block-container { padding-top: 24px; padding-bottom: 48px; max-width: 1180px; }
          @media (max-width: 1100px){ .block-container{ max-width: 980px; } }
          @media (max-width: 768px){ .block-container{ padding-top: 16px; padding-left: 14px; padding-right: 14px; } }

          /* Шапка */
          .hero-wrap{
            margin: 6px auto 18px auto;
          }
          .hero{
            position: relative;
            border-radius: 18px;
            padding: 18px 22px;
            background: linear-gradient(135deg, #0b2b55 0%, #1a4f8f 55%, #315f9f 100%);
            box-shadow: 0 16px 34px rgba(0,0,0,0.18);
            overflow: hidden;
          }
          .hero:before{
            content: "";
            position:absolute;
            right:-120px; top:-120px;
            width: 360px; height: 360px;
            background: rgba(255,255,255,0.12);
            border-radius: 50%;
          }
          .hero:after{
            content: "";
            position:absolute;
            right:40px; top:50%;
            width: 260px; height: 260px;
            background: rgba(255,255,255,0.10);
            border-radius: 50%;
            transform: translateY(-50%);
          }
          .hero-row{
            display:flex;
            gap:16px;
            align-items:flex-start;
            position: relative;
            z-index: 2;
          }
          .hero-crest{
            width: 54px;
            height: 54px;
            flex: 0 0 54px;
            border-radius: 12px;
            background: rgba(255,255,255,0.10);
            display:flex;
            align-items:center;
            justify-content:center;
            box-shadow: inset 0 0 0 1px rgba(255,255,255,0.14);
          }
          .hero-crest img{
            width: 40px;
            height: 40px;
            object-fit: contain;
            display:block;
          }
          .hero-titles{
            color: #fff;
            min-width: 0;
          }
          .hero-ministry{
            font-weight: 800;
            font-size: 18px;
            line-height: 1.25;
            margin: 1px 0 6px 0;
            letter-spacing: 0.2px;
          }
          .hero-app{
            font-weight: 700;
            font-size: 14px;
            opacity: 0.95;
            margin: 0 0 6px 0;
          }
          .hero-sub{
            font-size: 13px;
            opacity: 0.90;
            margin: 0 0 10px 0;
          }
          .hero-pill{
            display:inline-flex;
            gap:10px;
            align-items:center;
            padding: 8px 12px;
            border-radius: 999px;
            background: rgba(0,0,0,0.18);
            box-shadow: inset 0 0 0 1px rgba(255,255,255,0.14);
            font-size: 12px;
            opacity: 0.95;
            max-width: 100%;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
          }

          /* Фильтры */
          .filters-title{
            font-weight: 700;
            margin: 6px 0 8px 0;
          }

          /* Карточки */
          .card{
            border-radius: 18px;
            background: #fff;
            border: 1px solid rgba(0,0,0,0.06);
            box-shadow: 0 10px 28px rgba(0,0,0,0.06);
            padding: 16px 16px 14px 16px;
            margin: 14px 0;
          }
          .card-title{
            font-weight: 900;
            font-size: 18px;
            line-height: 1.25;
            margin: 0 0 10px 0;
          }
          @media (max-width: 768px){
            .card{ padding: 14px; }
            .card-title{ font-size: 17px; }
          }

          .kv-box{
            border-radius: 14px;
            background: rgba(0,0,0,0.03);
            border: 1px solid rgba(0,0,0,0.04);
            padding: 10px 12px;
          }
          .kv-grid{
            display:grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px 14px;
          }
          @media (max-width: 768px){
            .kv-grid{ grid-template-columns: 1fr; }
          }
          .kv-item{
            display:flex;
            gap: 10px;
            align-items:flex-start;
            min-width: 0;
          }
          .kv-ico{
            width: 22px;
            height: 22px;
            display:flex;
            align-items:center;
            justify-content:center;
            border-radius: 8px;
            background: rgba(0,0,0,0.05);
            flex: 0 0 22px;
            margin-top: 1px;
          }
          .kv-label{
            font-weight: 800;
            margin-right: 6px;
          }
          .kv-text{
            color: rgba(0,0,0,0.78);
            word-break: break-word;
          }

          .chips{
            display:flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-top: 10px;
          }
          .chip{
            display:inline-flex;
            gap: 8px;
            align-items:center;
            padding: 6px 10px;
            border-radius: 999px;
            background: rgba(30,111,255,0.08);
            border: 1px solid rgba(30,111,255,0.18);
            font-size: 12px;
            font-weight: 700;
            color: rgba(0,0,0,0.78);
          }

          .btn-row{
            display:grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-top: 12px;
          }
          @media (max-width: 768px){
            .btn-row{ grid-template-columns: 1fr; }
          }
          .btn{
            display:flex;
            align-items:center;
            justify-content:center;
            gap: 10px;
            padding: 12px 14px;
            border-radius: 12px;
            border: 1px solid rgba(0,0,0,0.10);
            text-decoration:none !important;
            color: rgba(0,0,0,0.85) !important;
            font-weight: 800;
            background: #fff;
            box-shadow: 0 6px 16px rgba(0,0,0,0.06);
          }
          .btn:hover{
            transform: translateY(-1px);
            transition: 120ms ease;
            box-shadow: 0 10px 24px rgba(0,0,0,0.08);
          }

          .note{
            margin-top: 10px;
            font-size: 12px;
            color: rgba(0,0,0,0.55);
            border-top: 1px dashed rgba(0,0,0,0.12);
            padding-top: 10px;
          }

          /* Логин */
          .login-wrap{
            max-width: 520px;
            margin: 16px auto 0 auto;
          }
          .login-card{
            border-radius: 18px;
            background: #fff;
            border: 1px solid rgba(0,0,0,0.06);
            box-shadow: 0 12px 30px rgba(0,0,0,0.08);
            padding: 16px;
          }
          .login-title{
            font-weight: 900;
            font-size: 18px;
            margin: 0 0 6px 0;
          }
          .login-sub{
            margin: 0 0 12px 0;
            color: rgba(0,0,0,0.62);
            font-size: 13px;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header(crest_b64: str, show_source_pill: bool):
    pill_html = ""
    if show_source_pill:
        pill_html = """
          <div class="hero-pill">📄 <span style="font-weight:800;">Источник данных:</span> <span style="opacity:.95;">Google Sheets (CSV)</span></div>
        """

    crest_img = ""
    if crest_b64:
        crest_img = f'<img src="data:image/png;base64,{crest_b64}" alt="Герб"/>'
    else:
        crest_img = ""

    header_html = f"""
    <div class="hero-wrap">
      <div class="hero">
        <div class="hero-row">
          <div class="hero-crest">{crest_img}</div>
          <div class="hero-titles">
            <div class="hero-ministry">Министерство восстановления, развития приграничья и строительства Курской области</div>
            <div class="hero-app">Реестр объектов</div>
            <div class="hero-sub">Единый список объектов 2025–2028 с быстрыми фильтрами и переходом в карточку/папку.</div>
            {pill_html}
          </div>
        </div>
      </div>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)


def safe_str(x) -> str:
    if x is None:
        return ""
    if pd.isna(x):
        return ""
    return str(x).strip()


def is_url(x: str) -> bool:
    x = safe_str(x)
    return x.startswith("http://") or x.startswith("https://")


def render_card(row: pd.Series, col_map: dict):
    name = safe_str(row.get(col_map["name"], ""))
    sector = safe_str(row.get(col_map["sector"], ""))
    district = safe_str(row.get(col_map["district"], ""))
    address = safe_str(row.get(col_map["address"], ""))
    responsible = safe_str(row.get(col_map["responsible"], ""))
    status = safe_str(row.get(col_map["status"], ""))
    works = safe_str(row.get(col_map["works"], ""))

    card_url = safe_str(row.get(col_map["card_url"], ""))
    folder_url = safe_str(row.get(col_map["folder_url"], ""))

    # Дефолты
    if not name:
        name = "Без названия"

    if not status:
        status = "—"
    if not works:
        works = "—"

    # Кнопки (если нет ссылок — делаем disabled-вид)
    card_btn = (
        f'<a class="btn" href="{card_url}" target="_blank" rel="noopener">📄 Открыть карточку</a>'
        if is_url(card_url)
        else '<div class="btn" style="opacity:.45; cursor:not-allowed;">📄 Открыть карточку</div>'
    )
    folder_btn = (
        f'<a class="btn" href="{folder_url}" target="_blank" rel="noopener">📁 Открыть папку</a>'
        if is_url(folder_url)
        else '<div class="btn" style="opacity:.45; cursor:not-allowed;">📁 Открыть папку</div>'
    )

    html = f"""
    <div class="card">
      <div class="card-title">{name}</div>

      <div class="kv-box">
        <div class="kv-grid">
          <div class="kv-item">
            <div class="kv-ico">🏷️</div>
            <div class="kv-text"><span class="kv-label">Отрасль:</span> {sector if sector else "—"}</div>
          </div>
          <div class="kv-item">
            <div class="kv-ico">📍</div>
            <div class="kv-text"><span class="kv-label">Район:</span> {district if district else "—"}</div>
          </div>
          <div class="kv-item">
            <div class="kv-ico">🗺️</div>
            <div class="kv-text"><span class="kv-label">Адрес:</span> {address if address else "—"}</div>
          </div>
          <div class="kv-item">
            <div class="kv-ico">👤</div>
            <div class="kv-text"><span class="kv-label">Ответственный:</span> {responsible if responsible else "—"}</div>
          </div>
        </div>
      </div>

      <div class="chips">
        <div class="chip">📌 <span>Статус:</span> <span style="opacity:.85;">{status}</span></div>
        <div class="chip">🛠️ <span>Работы:</span> <span style="opacity:.85;">{works}</span></div>
      </div>

      <div class="btn-row">
        {card_btn}
        {folder_btn}
      </div>

      <div class="note">Место под фото и дополнительные пункты (заполнишь в реестре — мы красиво выведем позже).</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# -----------------------------
# CSS + Герб
# -----------------------------
css()
crest_b64 = _read_file_b64("assets/gerb.png")  # у вас файл уже так называется

# -----------------------------
# Авторизация
# -----------------------------
if "auth" not in st.session_state:
    st.session_state.auth = False

def auth_screen():
    render_header(crest_b64, show_source_pill=False)  # ВАЖНО: без источника на экране пароля

    st.markdown('<div class="login-wrap"><div class="login-card">', unsafe_allow_html=True)
    st.markdown('<div class="login-title">🔒 Доступ по паролю</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-sub">Введите пароль для входа в реестр.</div>', unsafe_allow_html=True)

    pwd = st.text_input("Пароль", type="password", placeholder="Введите пароль…", label_visibility="collapsed")

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        btn = st.button("Войти", use_container_width=True)

    if btn:
        if not APP_PASSWORD:
            st.error("В Secrets не задан APP_PASSWORD.")
        elif pwd == APP_PASSWORD:
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Неверный пароль.")

    st.markdown("</div></div>", unsafe_allow_html=True)

# Если не авторизован — показываем экран пароля и выходим
if not st.session_state.auth:
    auth_screen()
    st.stop()

# -----------------------------
# Основная страница
# -----------------------------
render_header(crest_b64, show_source_pill=True)

df = load_data(CSV_URL)

if df.empty:
    st.error("Данные не загрузились (реестр пустой). Проверьте CSV_URL в Secrets или доступ к таблице.")
    st.stop()

# -----------------------------
# Маппинг колонок (под разные названия)
# -----------------------------
col_name = _pick_col(df, ["Наименование", "Название", "Объект", "Наименование объекта", "name", "object"])
col_sector = _pick_col(df, ["Отрасль", "Сфера", "Направление", "sector"])
col_district = _pick_col(df, ["Район", "Муниципалитет", "МО", "district"])
col_address = _pick_col(df, ["Адрес", "Место", "Локация", "address"])
col_responsible = _pick_col(df, ["Ответственный", "Куратор", "Ответственные", "responsible"])
col_status = _pick_col(df, ["Статус", "Состояние", "status"])
col_works = _pick_col(df, ["Работы", "Вид работ", "Этап", "works"])
col_card_url = _pick_col(df, ["Ссылка на карточку", "Карточка", "card_url", "url_card", "Card URL"])
col_folder_url = _pick_col(df, ["Ссылка на папку", "Папка", "folder_url", "url_folder", "Folder URL"])

# если каких-то колонок нет — создадим пустые, чтобы не падать
for c in [col_name, col_sector, col_district, col_address, col_responsible, col_status, col_works, col_card_url, col_folder_url]:
    pass

def ensure_col(col: str | None, fallback_name: str) -> str:
    if col and col in df.columns:
        return col
    if fallback_name not in df.columns:
        df[fallback_name] = ""
    return fallback_name

col_map = {
    "name": ensure_col(col_name, "Наименование"),
    "sector": ensure_col(col_sector, "Отрасль"),
    "district": ensure_col(col_district, "Район"),
    "address": ensure_col(col_address, "Адрес"),
    "responsible": ensure_col(col_responsible, "Ответственный"),
    "status": ensure_col(col_status, "Статус"),
    "works": ensure_col(col_works, "Работы"),
    "card_url": ensure_col(col_card_url, "Ссылка на карточку"),
    "folder_url": ensure_col(col_folder_url, "Ссылка на папку"),
}

# -----------------------------
# Фильтры (районы — динамически по выбранной отрасли/статусу)
# -----------------------------
# Базовые списки
sectors_all = sorted([x for x in df[col_map["sector"]].dropna().astype(str).str.strip().unique() if x and x != "nan"])
statuses_all = sorted([x for x in df[col_map["status"]].dropna().astype(str).str.strip().unique() if x and x != "nan"])

# Выбор отрасли / статус
c1, c2, c3 = st.columns([1, 1, 1])

with c1:
    sector_opt = ["Все"] + sectors_all
    sector = st.selectbox("🏷️ Отрасль", sector_opt, index=0)

with c3:
    status_opt = ["Все"] + statuses_all
    status = st.selectbox("📌 Статус", status_opt, index=0)

# Промежуточная фильтрация для расчёта районов
df_tmp = df.copy()
if sector != "Все":
    df_tmp = df_tmp[df_tmp[col_map["sector"]].astype(str).str.strip() == sector]
if status != "Все":
    df_tmp = df_tmp[df_tmp[col_map["status"]].astype(str).str.strip() == status]

districts_dynamic = sorted([x for x in df_tmp[col_map["district"]].dropna().astype(str).str.strip().unique() if x and x != "nan"])
with c2:
    district_opt = ["Все"] + districts_dynamic
    district = st.selectbox("📍 Район", district_opt, index=0)

query = st.text_input("🔎 Поиск (наименование / адрес / ответственный)", placeholder="Введите текст для поиска…")

# Финальная фильтрация
df_view = df.copy()
if sector != "Все":
    df_view = df_view[df_view[col_map["sector"]].astype(str).str.strip() == sector]
if status != "Все":
    df_view = df_view[df_view[col_map["status"]].astype(str).str.strip() == status]
if district != "Все":
    df_view = df_view[df_view[col_map["district"]].astype(str).str.strip() == district]

if query.strip():
    q = query.strip().lower()
    mask = (
        df_view[col_map["name"]].astype(str).str.lower().str.contains(q, na=False)
        | df_view[col_map["address"]].astype(str).str.lower().str.contains(q, na=False)
        | df_view[col_map["responsible"]].astype(str).str.lower().str.contains(q, na=False)
    )
    df_view = df_view[mask]

st.caption(f"Показано объектов: **{len(df_view)}** из **{len(df)}**")

st.markdown("---")

# -----------------------------
# Рендер карточек: ОДНА КОЛОНКА
# -----------------------------
for _, row in df_view.iterrows():
    render_card(row, col_map)
