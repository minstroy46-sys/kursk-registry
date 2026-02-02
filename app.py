import os
import pandas as pd
import streamlit as st

# =========================
# CONFIG
# =========================
st.set_page_config(
    page_title="Реестр объектов — Курская область",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed",
)

APP_TITLE = "Министерство восстановления, развития приграничья и строительства Курской области"
APP_SUBTITLE = "Реестр объектов"
APP_DESC = "Единый список объектов 2025–2028 с быстрыми фильтрами и переходом в карточку/папку."

# Если хотите полностью убрать «Источник данных» даже в основном приложении — поставьте False
SHOW_SOURCE_PILL_IN_MAIN = True

# Лого/герб: можно хранить как URL или base64. Если нет — будет просто пустая плашка.
# Подставьте свой путь/URL если нужно.
LOGO_URL = None  # например: "https://.../gerb.png"

# Ожидаемые колонки (можно менять под ваш реестр)
COL_NAME = "Наименование"
COL_SECTOR = "Отрасль"
COL_DISTRICT = "Район"
COL_ADDRESS = "Адрес"
COL_RESP = "Ответственный"
COL_STATUS = "Статус"
COL_WORKS = "Работы"
COL_CARD_URL = "Ссылка на карточку"
COL_FOLDER_URL = "Ссылка на папку"


# =========================
# CSS (важно для мобильной версии)
# =========================
def inject_css():
    st.markdown(
        """
<style>
/* Общие */
.block-container { padding-top: 18px; padding-bottom: 40px; max-width: 1200px; }
@media (max-width: 1024px){
  .block-container { padding-left: 14px; padding-right: 14px; }
}
hr { margin: 16px 0 18px 0; }

/* HERO */
.hero-wrap{
  margin: 8px auto 18px auto;
  border-radius: 18px;
  background: linear-gradient(135deg, #0b2a50 0%, #1a4f8f 55%, #2b66ad 100%);
  box-shadow: 0 14px 34px rgba(15, 30, 56, .18);
  overflow: hidden;
  position: relative;
}
.hero-wrap:after{
  content:"";
  position:absolute;
  right:-120px;
  top:-120px;
  width: 360px;
  height: 360px;
  border-radius: 999px;
  background: rgba(255,255,255,0.10);
}
.hero-wrap:before{
  content:"";
  position:absolute;
  right:60px;
  bottom:-140px;
  width: 420px;
  height: 420px;
  border-radius: 999px;
  background: rgba(255,255,255,0.08);
}
.hero{
  position: relative;
  z-index: 2;
  display: flex;
  gap: 14px;
  padding: 18px 18px 16px 18px;
  align-items: flex-start;
}
.hero-crest{
  width: 54px; height: 54px;
  border-radius: 12px;
  background: rgba(255,255,255,0.12);
  display:flex;
  align-items:center;
  justify-content:center;
  flex: 0 0 auto;
  overflow:hidden;
  border: 1px solid rgba(255,255,255,0.14);
}
.hero-crest img{
  width: 44px; height: 44px; object-fit: contain;
}
.hero-titles{ color: #fff; min-width: 0; }
.hero-ministry{
  font-size: 16px;
  font-weight: 800;
  line-height: 1.25;
  margin-bottom: 6px;
}
.hero-app{
  font-size: 14px;
  font-weight: 700;
  opacity: .95;
  margin-bottom: 6px;
}
.hero-sub{
  font-size: 12.5px;
  opacity: .9;
  line-height: 1.35;
  max-width: 880px;
}
.hero-pill{
  display:inline-flex;
  align-items:center;
  gap: 8px;
  margin-top: 10px;
  padding: 7px 10px;
  border-radius: 999px;
  background: rgba(0,0,0,0.18);
  border: 1px solid rgba(255,255,255,0.16);
  font-size: 12px;
  color: rgba(255,255,255,0.95);
  white-space: nowrap;
}
.hero-pill b{ font-weight: 800; }

@media (max-width: 720px){
  .hero { padding: 16px 14px; }
  .hero-crest{ width: 50px; height: 50px; }
  .hero-ministry{ font-size: 15px; }
  .hero-sub{ font-size: 12px; }
  .hero-pill{ white-space: normal; }
}

/* Фильтры */
.filters-wrap{
  margin: 0 auto 10px auto;
}
.filters-meta{
  font-size: 12px;
  color: rgba(0,0,0,.55);
  margin-top: 6px;
}
@media (max-width: 720px){
  /* На мобиле делаем элементы управления шире */
  div[data-testid="stSelectbox"] > div { min-height: 46px; }
  div[data-testid="stTextInput"] > div { min-height: 46px; }
}

/* Карточки */
.cards-wrap{ margin-top: 10px; }
.obj-card{
  background: #fff;
  border-radius: 16px;
  border: 1px solid rgba(0,0,0,0.07);
  box-shadow: 0 10px 24px rgba(15, 30, 56, .06);
  padding: 14px 14px 12px 14px;
  margin: 0 0 14px 0;
}
.obj-title{
  font-size: 18px;
  font-weight: 850;
  line-height: 1.22;
  margin-bottom: 10px;
}
.kv-box{
  background: rgba(0,0,0,0.03);
  border: 1px solid rgba(0,0,0,0.05);
  border-radius: 12px;
  padding: 10px 10px;
}
.kv-grid{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 12px;
}
.kv-item{
  display:flex;
  gap: 8px;
  align-items:flex-start;
  min-width: 0;
}
.kv-ico{
  width: 20px;
  flex: 0 0 20px;
  opacity: .95;
  margin-top: 1px;
}
.kv-label{
  font-weight: 800;
  margin-right: 6px;
}
.kv-val{
  opacity: .95;
  word-break: break-word;
}
.badges{
  display:flex;
  gap: 8px;
  flex-wrap: wrap;
  margin: 10px 0 10px 0;
}
.badge{
  display:inline-flex;
  align-items:center;
  gap: 8px;
  padding: 7px 10px;
  border-radius: 999px;
  background: rgba(27, 86, 160, 0.08);
  border: 1px solid rgba(27, 86, 160, 0.18);
  font-size: 12px;
  font-weight: 700;
}
.badge span{ opacity: .9; font-weight: 800; }
.actions{
  display:grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 8px;
}
.a-btn{
  display:flex;
  align-items:center;
  justify-content:center;
  gap: 10px;
  border-radius: 12px;
  padding: 12px 12px;
  border: 1px solid rgba(0,0,0,0.12);
  background: #fff;
  font-weight: 800;
  text-decoration: none !important;
  color: rgba(0,0,0,.86) !important;
}
.a-btn:hover{
  border-color: rgba(27, 86, 160, 0.35);
  box-shadow: 0 8px 20px rgba(15, 30, 56, .07);
}
.card-note{
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed rgba(0,0,0,0.12);
  font-size: 12px;
  color: rgba(0,0,0,0.55);
}
@media (max-width: 840px){
  .kv-grid{ grid-template-columns: 1fr; }
  .obj-title{ font-size: 16px; }
  .actions{ grid-template-columns: 1fr; }
}

/* Экран пароля */
.login-wrap{
  margin: 10px auto 0 auto;
  max-width: 720px;
}
.login-card{
  background: #fff;
  border-radius: 16px;
  border: 1px solid rgba(0,0,0,0.07);
  box-shadow: 0 12px 26px rgba(15, 30, 56, .08);
  padding: 14px 14px 10px 14px;
}
.login-title{
  font-size: 18px;
  font-weight: 900;
  margin: 0 0 4px 0;
}
.login-sub{
  font-size: 12.5px;
  color: rgba(0,0,0,0.6);
  margin: 0 0 10px 0;
}
</style>
        """,
        unsafe_allow_html=True,
    )


# =========================
# HERO RENDER
# =========================
def render_hero(show_source_pill: bool):
    crest_html = ""
    if LOGO_URL:
        crest_html = f'<img src="{LOGO_URL}" alt="Герб"/>'
    else:
        crest_html = '<div style="width:44px;height:44px;border-radius:10px;background:rgba(255,255,255,.10);border:1px solid rgba(255,255,255,.12);"></div>'

    pill_html = ""
    if show_source_pill:
        pill_html = """
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
    <div class="hero-crest">{crest_html}</div>
    <div class="hero-titles">
      <div class="hero-ministry">{APP_TITLE}</div>
      <div class="hero-app">{APP_SUBTITLE}</div>
      <div class="hero-sub">{APP_DESC}</div>
      {pill_html}
    </div>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


# =========================
# AUTH
# =========================
def is_authed() -> bool:
    return bool(st.session_state.get("authed", False))


def auth_screen() -> None:
    # ШАПКА НА ЭКРАНЕ ПАРОЛЯ — БЕЗ ИСТОЧНИКА ДАННЫХ (как вы требуете)
    render_hero(show_source_pill=False)

    st.markdown('<div class="login-wrap">', unsafe_allow_html=True)
    st.markdown(
        """
<div class="login-card">
  <div class="login-title">🔒 Доступ по паролю</div>
  <div class="login-sub">Введите пароль для входа в реестр.</div>
</div>
        """,
        unsafe_allow_html=True,
    )

    # Поле + кнопка
    c1, c2 = st.columns([1, 0.35], vertical_alignment="bottom")
    with c1:
        pwd = st.text_input("Пароль", type="password", label_visibility="collapsed", placeholder="Введите пароль…")
    with c2:
        btn = st.button("Войти", use_container_width=True)

    if btn:
        secret_pwd = None
        try:
            secret_pwd = st.secrets.get("APP_PASSWORD", None)
        except Exception:
            secret_pwd = None

        if secret_pwd is None:
            st.error("Не задан APP_PASSWORD в Secrets Streamlit.")
        elif pwd == str(secret_pwd):
            st.session_state["authed"] = True
            st.rerun()
        else:
            st.error("Неверный пароль.")

    st.markdown("</div>", unsafe_allow_html=True)


# =========================
# DATA
# =========================
@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    csv_url = None
    try:
        csv_url = st.secrets.get("CSV_URL", None)
    except Exception:
        csv_url = None

    if not csv_url:
        # запасной вариант: переменная окружения
        csv_url = os.environ.get("CSV_URL")

    if not csv_url:
        return pd.DataFrame()

    try:
        df = pd.read_csv(csv_url)
        # Нормализуем имена колонок (убираем пробелы по краям)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception:
        return pd.DataFrame()


def safe_str(x):
    if x is None:
        return ""
    if isinstance(x, float) and pd.isna(x):
        return ""
    if pd.isna(x):
        return ""
    return str(x).strip()


def build_options(df: pd.DataFrame, col: str):
    if col not in df.columns:
        return ["Все"]
    vals = sorted({safe_str(v) for v in df[col].dropna().tolist() if safe_str(v)})
    return ["Все"] + vals


def apply_filters(df: pd.DataFrame, sector: str, district: str, status: str, query: str) -> pd.DataFrame:
    out = df.copy()

    # Отрасль
    if sector != "Все" and COL_SECTOR in out.columns:
        out = out[out[COL_SECTOR].astype(str).str.strip() == sector]

    # Район
    if district != "Все" and COL_DISTRICT in out.columns:
        out = out[out[COL_DISTRICT].astype(str).str.strip() == district]

    # Статус
    if status != "Все" and COL_STATUS in out.columns:
        out = out[out[COL_STATUS].astype(str).str.strip() == status]

    # Поиск
    q = (query or "").strip().lower()
    if q:
        hay_cols = [c for c in [COL_NAME, COL_ADDRESS, COL_RESP, COL_DISTRICT] if c in out.columns]
        if hay_cols:
            mask = False
            for c in hay_cols:
                mask = mask | out[c].astype(str).str.lower().str.contains(q, na=False)
            out = out[mask]

    return out


def render_card(row: pd.Series):
    name = safe_str(row.get(COL_NAME, ""))
    sector = safe_str(row.get(COL_SECTOR, ""))
    district = safe_str(row.get(COL_DISTRICT, ""))
    address = safe_str(row.get(COL_ADDRESS, ""))
    resp = safe_str(row.get(COL_RESP, ""))
    status = safe_str(row.get(COL_STATUS, "—")) or "—"
    works = safe_str(row.get(COL_WORKS, "—")) or "—"

    card_url = safe_str(row.get(COL_CARD_URL, ""))
    folder_url = safe_str(row.get(COL_FOLDER_URL, ""))

    # Кнопки: если ссылки пустые — делаем disabled-стиль
    def btn_html(label, icon, url):
        if url:
            return f'<a class="a-btn" href="{url}" target="_blank" rel="noopener noreferrer">{icon} {label}</a>'
        return f'<div class="a-btn" style="opacity:.45; cursor:not-allowed;">{icon} {label}</div>'

    st.markdown(
        f"""
<div class="obj-card">
  <div class="obj-title">{name}</div>

  <div class="kv-box">
    <div class="kv-grid">
      <div class="kv-item"><div class="kv-ico">🏷️</div><div><span class="kv-label">Отрасль:</span> <span class="kv-val">{sector or "—"}</span></div></div>
      <div class="kv-item"><div class="kv-ico">📍</div><div><span class="kv-label">Район:</span> <span class="kv-val">{district or "—"}</span></div></div>
      <div class="kv-item"><div class="kv-ico">🗺️</div><div><span class="kv-label">Адрес:</span> <span class="kv-val">{address or "—"}</span></div></div>
      <div class="kv-item"><div class="kv-ico">👤</div><div><span class="kv-label">Ответственный:</span> <span class="kv-val">{resp or "—"}</span></div></div>
    </div>
  </div>

  <div class="badges">
    <div class="badge">📌 <span>Статус:</span> {status}</div>
    <div class="badge">🛠️ <span>Работы:</span> {works}</div>
  </div>

  <div class="actions">
    {btn_html("Открыть карточку", "📄", card_url)}
    {btn_html("Открыть папку", "📁", folder_url)}
  </div>

  <div class="card-note">Место под фото и дополнительные пункты (заполнишь в реестре — мы красиво выведем позже).</div>
</div>
        """,
        unsafe_allow_html=True,
    )


# =========================
# MAIN
# =========================
def main_app():
    inject_css()
    render_hero(show_source_pill=SHOW_SOURCE_PILL_IN_MAIN)

    df = load_data()
    if df.empty:
        st.error("Данные не загрузились (реестр пустой). Проверьте CSV_URL в Secrets.")
        return

    # ФИЛЬТРЫ
    st.markdown('<div class="filters-wrap">', unsafe_allow_html=True)

    # 1) Отрасль всегда от полного df
    sector_options = build_options(df, COL_SECTOR)

    # Выводим 3 селекта в ряд на десктопе (на мобиле они сами становятся столбиком)
    col1, col2, col3 = st.columns(3)
    with col1:
        sector = st.selectbox("🏷️ Отрасль", sector_options, index=0)
    # 2) Район зависит от отрасли (чтобы пустые не показывались)
    df_for_district = df
    if sector != "Все" and COL_SECTOR in df_for_district.columns:
        df_for_district = df_for_district[df_for_district[COL_SECTOR].astype(str).str.strip() == sector]
    district_options = build_options(df_for_district, COL_DISTRICT)

    with col2:
        district = st.selectbox("📍 Район", district_options, index=0)
    # 3) Статус тоже можно зависимо от отрасли/района, но вы просили только район — делаем аккуратно:
    df_for_status = df_for_district
    if district != "Все" and COL_DISTRICT in df_for_status.columns:
        df_for_status = df_for_status[df_for_status[COL_DISTRICT].astype(str).str.strip() == district]
    status_options = build_options(df_for_status, COL_STATUS)

    with col3:
        status = st.selectbox("📌 Статус", status_options, index=0)

    query = st.text_input("🔎 Поиск (наименование / адрес / ответственный)", value="", placeholder="Введите текст для поиска...")

    # Применяем фильтры
    filtered = apply_filters(df, sector, district, status, query)

    st.markdown(f'<div class="filters-meta">Показано объектов: {len(filtered)} из {len(df)}</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.divider()

    # КАРТОЧКИ (ОДНА КОЛОНКА — как вы просили)
    st.markdown('<div class="cards-wrap">', unsafe_allow_html=True)
    for _, r in filtered.iterrows():
        render_card(r)
    st.markdown("</div>", unsafe_allow_html=True)


def run():
    inject_css()

    if not is_authed():
        auth_screen()
        return

    main_app()


if __name__ == "__main__":
    run()
