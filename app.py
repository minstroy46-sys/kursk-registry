import os
import io
import base64
from typing import Optional

import pandas as pd
import requests
import streamlit as st


# =========================
# CONFIG
# =========================
st.set_page_config(
    page_title="Реестр объектов — Курская область",
    page_icon="🗂️",
    layout="wide",
)

APP_TITLE = "Министерство восстановления, развития приграничья и строительства Курской области"
APP_SUBTITLE = "Реестр объектов"
APP_DESC = "Единый список объектов 2025–2028 с быстрыми фильтрами и переходом в карточку/папку."
ASSETS_GERB_PATH = os.path.join("assets", "gerb.png")

# Secrets
CSV_URL = st.secrets.get("CSV_URL", "").strip()
APP_PASSWORD = st.secrets.get("APP_PASSWORD", "").strip()


# =========================
# STYLES (Desktop + Mobile)
# =========================
def inject_css():
    css = """
    <style>
      /* убрать лишние верхние отступы streamlit */
      .block-container { padding-top: 1.2rem; padding-bottom: 2.2rem; }
      header[data-testid="stHeader"] { background: transparent; }
      /* иногда streamlit оставляет сверху пустое место */
      div[data-testid="stToolbar"] { visibility: hidden; height: 0; position: fixed; }

      /* HERO full-width фон (растянут на всю страницу), контент центрируется */
      .hero-bg {
        width: 100%;
        background: radial-gradient(1400px 400px at 85% 30%, rgba(255,255,255,0.18), rgba(255,255,255,0) 60%),
                    linear-gradient(135deg, #0b2a4a 0%, #0f3d73 55%, #184f92 100%);
        border-radius: 18px;
        box-shadow: 0 10px 30px rgba(0,0,0,.12);
        padding: 18px 22px;
        margin: 6px auto 18px auto;
        position: relative;
        overflow: hidden;
      }
      .hero-bubbles {
        position:absolute; right:-110px; top:-70px;
        width: 420px; height: 420px;
        background: radial-gradient(circle at 30% 30%, rgba(255,255,255,.26), rgba(255,255,255,0) 60%);
        border-radius: 999px;
        filter: blur(0px);
        opacity: .9;
      }
      .hero-bubbles2 {
        position:absolute; right:-40px; top:70px;
        width: 260px; height: 260px;
        background: radial-gradient(circle at 40% 40%, rgba(255,255,255,.18), rgba(255,255,255,0) 62%);
        border-radius: 999px;
        opacity: .9;
      }
      .hero-row { display:flex; gap:16px; align-items:flex-start; }
      .hero-crest {
        width: 62px; height: 62px; flex: 0 0 62px;
        border-radius: 14px;
        background: rgba(255,255,255,.10);
        display:flex; align-items:center; justify-content:center;
        border: 1px solid rgba(255,255,255,.14);
      }
      .hero-crest img { width: 46px; height: 46px; object-fit: contain; }
      .hero-texts { color: #fff; min-width: 0; }
      .hero-ministry { font-weight: 700; font-size: 18px; line-height: 1.25; }
      .hero-app { font-weight: 700; font-size: 15px; opacity: .95; margin-top: 2px; }
      .hero-desc { font-size: 12.5px; opacity: .90; margin-top: 6px; }
      .hero-pill {
        display:inline-flex; align-items:center; gap:8px;
        margin-top: 10px;
        background: rgba(255,255,255,.12);
        border: 1px solid rgba(255,255,255,.14);
        border-radius: 999px;
        padding: 8px 12px;
        font-size: 12px;
        opacity: .98;
      }

      /* Filters wrapper */
      .filters-wrap { margin-top: 2px; margin-bottom: 10px; }
      .count-line { font-size: 12px; opacity: .75; margin: 10px 0 4px 0; }

      /* Card (1 колонка) */
      .card {
        background: rgba(255,255,255,0.92);
        border: 1px solid rgba(15, 23, 42, 0.08);
        border-radius: 16px;
        box-shadow: 0 6px 16px rgba(0,0,0,.06);
        padding: 14px 14px 12px 14px;
        margin: 14px 0;
        overflow: hidden; /* важно для мобилы */
      }
      .card-title {
        font-size: 18px;
        font-weight: 800;
        line-height: 1.2;
        margin: 2px 0 8px 0;
        color: #0f172a;
        word-break: break-word;
      }
      .card-id {
        font-size: 12px;
        opacity: .55;
        margin-top: -2px;
        margin-bottom: 10px;
      }

      .card-grid {
        display:flex;
        gap: 12px;
        flex-wrap: wrap;
        background: rgba(15, 23, 42, 0.03);
        border: 1px solid rgba(15, 23, 42, 0.06);
        border-radius: 12px;
        padding: 10px 10px;
      }
      .card-item {
        display:flex; align-items:flex-start; gap:8px;
        min-width: 220px;
        flex: 1 1 220px;
        color:#0f172a;
      }
      .card-item b { font-weight: 700; }
      .card-item .ico { width: 18px; text-align:center; margin-top: 1px; }
      .card-item .txt { min-width:0; word-break: break-word; }

      .chips {
        display:flex;
        gap: 10px;
        flex-wrap: wrap;
        margin: 10px 0 10px 0;
      }
      .chip {
        display:inline-flex; align-items:center; gap:8px;
        padding: 6px 10px;
        border-radius: 999px;
        background: rgba(59, 130, 246, 0.08);
        border: 1px solid rgba(59, 130, 246, 0.20);
        font-size: 12px;
        color: #0f172a;
      }

      .btn-row {
        display:flex;
        gap: 12px;
        flex-wrap: wrap;
        margin-top: 6px;
      }
      .btn {
        display:flex;
        align-items:center;
        justify-content:center;
        gap: 8px;
        text-decoration:none !important;
        padding: 12px 12px;
        border-radius: 12px;
        border: 1px solid rgba(15, 23, 42, 0.14);
        background: rgba(255,255,255,0.92);
        color: #0f172a !important;
        font-weight: 700;
        flex: 1 1 260px;
        min-height: 44px;
      }
      .btn:hover { background: rgba(241,245,249,1); border-color: rgba(15, 23, 42, 0.22); }

      .placeholder-note {
        margin-top: 10px;
        padding-top: 10px;
        border-top: 1px dashed rgba(15, 23, 42, 0.18);
        font-size: 12px;
        opacity: .65;
      }

      /* Login card */
      .login-wrap {
        display:flex;
        justify-content:center;
        margin-top: 10px;
      }
      .login-card {
        width: min(740px, 92vw);
        background: rgba(255,255,255,0.92);
        border: 1px solid rgba(15, 23, 42, 0.10);
        border-radius: 18px;
        box-shadow: 0 12px 28px rgba(0,0,0,.10);
        padding: 16px 16px 14px 16px;
      }
      .login-title {
        font-weight: 800;
        font-size: 16px;
        margin: 2px 0 2px 0;
        color:#0f172a;
      }
      .login-sub { font-size: 12.5px; opacity:.75; margin-bottom: 10px; }

      /* STREAMLIT WIDGETS: делаем ширину норм на мобиле */
      div[data-testid="stSelectbox"] > div, div[data-testid="stTextInput"] > div {
        border-radius: 12px !important;
      }

      /* MOBILE */
      @media (max-width: 780px) {
        .block-container { padding-left: 0.9rem; padding-right: 0.9rem; }
        .hero-bg { padding: 16px 16px; border-radius: 18px; margin-bottom: 14px; }
        .hero-row { gap: 12px; }
        .hero-crest { width: 56px; height: 56px; flex:0 0 56px; }
        .hero-crest img { width: 42px; height: 42px; }
        .hero-ministry { font-size: 16px; }
        .hero-app { font-size: 14px; }
        .hero-desc { font-size: 12px; }

        .card { padding: 12px 12px 10px 12px; border-radius: 16px; }
        .card-title { font-size: 16px; }
        .card-item { min-width: 100%; flex: 1 1 100%; } /* ключевой фикс — всё в столбик */
        .btn { flex: 1 1 100%; } /* кнопки одна под другой */
      }

      /* DARK MODE (мобильный Android часто включает) */
      @media (prefers-color-scheme: dark) {
        body, .stApp { background: #0b1220; color: rgba(255,255,255,.92); }
        .card, .login-card { background: rgba(17, 24, 39, 0.92); border-color: rgba(255,255,255,0.10); }
        .card-title { color: rgba(255,255,255,.92); }
        .card-grid { background: rgba(255,255,255,0.04); border-color: rgba(255,255,255,0.08); }
        .card-item { color: rgba(255,255,255,.90); }
        .chip { background: rgba(59,130,246,0.15); border-color: rgba(59,130,246,0.28); color: rgba(255,255,255,.92); }
        .btn { background: rgba(17,24,39,0.92); border-color: rgba(255,255,255,0.12); color: rgba(255,255,255,.92) !important; }
        .btn:hover { background: rgba(30,41,59,0.92); }
      }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


# =========================
# HELPERS
# =========================
@st.cache_data(show_spinner=False, ttl=60)
def load_bytes_from_url(url: str) -> Optional[bytes]:
    if not url:
        return None
    try:
        r = requests.get(url, timeout=25)
        r.raise_for_status()
        return r.content
    except Exception:
        return None


def load_gerb_base64() -> str:
    try:
        with open(ASSETS_GERB_PATH, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return ""


@st.cache_data(show_spinner=False, ttl=60)
def load_registry_df(csv_url: str) -> pd.DataFrame:
    # 1) Google Sheets CSV (основной источник)
    content = load_bytes_from_url(csv_url)
    if content:
        # иногда гугл отдаёт UTF-8, иногда с BOM — pandas обычно переварит
        df = pd.read_csv(io.BytesIO(content))
        return df

    # 2) fallback: если кто-то положит xlsx рядом (не обязательно)
    for name in os.listdir("."):
        if name.lower().endswith(".xlsx"):
            try:
                return pd.read_excel(name)
            except Exception:
                pass

    return pd.DataFrame()


def norm(s: str) -> str:
    return str(s).strip() if s is not None else ""


def pick_col(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    cols = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in cols:
            return cols[cand.lower()]
    return None


def prepare_df(df_raw: pd.DataFrame) -> pd.DataFrame:
    if df_raw is None or df_raw.empty:
        return pd.DataFrame()

    # Поддержка разных заголовков (на случай изменений)
    col_id = pick_col(df_raw, ["id", "ID"])
    col_sector = pick_col(df_raw, ["Отрасль", "sector"])
    col_district = pick_col(df_raw, ["Район", "district"])
    col_name = pick_col(df_raw, ["Наименование_объекта", "Наименование объекта", "name", "Объект", "object"])
    col_address = pick_col(df_raw, ["Адрес", "address"])
    col_resp = pick_col(df_raw, ["Ответственный", "responsible"])
    col_status = pick_col(df_raw, ["Статус", "status"])
    col_works = pick_col(df_raw, ["Работы", "works"])
    col_card = pick_col(df_raw, ["Ссылка_на_карточку_(Google)", "Ссылка на карточку", "card_url", "card_url_text"])
    col_folder = pick_col(df_raw, ["Ссылка_на_папку_(Drive)", "Ссылка на папку", "folder_url"])

    # Сборка унифицированного DF
    out = pd.DataFrame()
    out["id"] = df_raw[col_id] if col_id else ""
    out["sector"] = df_raw[col_sector] if col_sector else ""
    out["district"] = df_raw[col_district] if col_district else ""
    out["name"] = df_raw[col_name] if col_name else ""
    out["address"] = df_raw[col_address] if col_address else ""
    out["responsible"] = df_raw[col_resp] if col_resp else ""
    out["status"] = df_raw[col_status] if col_status else ""
    out["works"] = df_raw[col_works] if col_works else ""
    out["card_url"] = df_raw[col_card] if col_card else ""
    out["folder_url"] = df_raw[col_folder] if col_folder else ""

    # чистка
    for c in out.columns:
        out[c] = out[c].astype(str).fillna("").map(norm)
        out.loc[out[c].str.lower().isin(["nan", "none", "null"]), c] = ""

    # если name пустой — НЕ подставляем id, оставляем пустым (чтобы видно было что надо заполнить)
    # но для отображения заголовка карточки ниже подстрахуемся

    return out


def hero_html(gerb_b64: str, show_source: bool) -> str:
    crest_img = ""
    if gerb_b64:
        crest_img = f'<img alt="gerb" src="data:image/png;base64,{gerb_b64}"/>'
    else:
        crest_img = '<span style="color:rgba(255,255,255,.85);font-weight:800;">Герб</span>'

    pill = ""
    if show_source:
        pill = """
        <div class="hero-pill">
          <span style="opacity:.95;">📄</span>
          <span style="font-weight:700;">Источник данных:</span>
          <span style="opacity:.95;">Google Sheets (CSV)</span>
        </div>
        """

    return f"""
    <div class="hero-bg">
      <div class="hero-bubbles"></div>
      <div class="hero-bubbles2"></div>
      <div class="hero-row">
        <div class="hero-crest">{crest_img}</div>
        <div class="hero-texts">
          <div class="hero-ministry">{APP_TITLE}</div>
          <div class="hero-app">{APP_SUBTITLE}</div>
          <div class="hero-desc">{APP_DESC}</div>
          {pill}
        </div>
      </div>
    </div>
    """


def render_card(row: pd.Series):
    obj_id = row.get("id", "")
    name = row.get("name", "")
    sector = row.get("sector", "")
    district = row.get("district", "")
    address = row.get("address", "")
    responsible = row.get("responsible", "")
    status = row.get("status", "")
    works = row.get("works", "")
    card_url = row.get("card_url", "")
    folder_url = row.get("folder_url", "")

    title = name if name else (address if address else f"Объект {obj_id}" if obj_id else "Объект")

    # Секции: если пусто — выводим "—" (чтобы карточка не разваливалась)
    def show(v: str) -> str:
        return v if v else "—"

    # Кнопки: если ссылки нет — делаем disabled-вид (но без ломания верстки)
    def btn_html(label: str, icon: str, url: str) -> str:
        if url and url != "—":
            return f'<a class="btn" href="{url}" target="_blank" rel="noopener">{icon} {label}</a>'
        return f'<div class="btn" style="opacity:.45; cursor:not-allowed;">{icon} {label}</div>'

    html = f"""
    <div class="card">
      <div class="card-title">{title}</div>
      <div class="card-id">ID: {show(obj_id)}</div>

      <div class="card-grid">
        <div class="card-item"><div class="ico">🏷️</div><div class="txt"><b>Отрасль:</b> {show(sector)}</div></div>
        <div class="card-item"><div class="ico">📍</div><div class="txt"><b>Район:</b> {show(district)}</div></div>
        <div class="card-item"><div class="ico">🗺️</div><div class="txt"><b>Адрес:</b> {show(address)}</div></div>
        <div class="card-item"><div class="ico">👤</div><div class="txt"><b>Ответственный:</b> {show(responsible)}</div></div>
      </div>

      <div class="chips">
        <div class="chip">📌 <b>Статус:</b> {show(status)}</div>
        <div class="chip">🛠️ <b>Работы:</b> {show(works)}</div>
      </div>

      <div class="btn-row">
        {btn_html("Открыть карточку", "📄", card_url)}
        {btn_html("Открыть папку", "📁", folder_url)}
      </div>

      <div class="placeholder-note">
        Место под фото и дополнительные пункты (заполнишь в реестре — мы красиво выведем позже).
      </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# =========================
# AUTH
# =========================
def is_authed() -> bool:
    return bool(st.session_state.get("authed", False))


def do_logout():
    st.session_state["authed"] = False
    st.session_state.pop("password_try", None)


def auth_block(gerb_b64: str):
    """
    Экран входа: шапка как у вас, но БЕЗ "Источник данных".
    """
    st.markdown(hero_html(gerb_b64, show_source=False), unsafe_allow_html=True)

    st.markdown('<div class="login-wrap"><div class="login-card">', unsafe_allow_html=True)
    st.markdown('<div class="login-title">🔒 Доступ по паролю</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-sub">Введите пароль для входа в реестр.</div>', unsafe_allow_html=True)

    pwd = st.text_input("Пароль", type="password", key="password_try", placeholder="Введите пароль…", label_visibility="collapsed")

    col1, col2 = st.columns([1, 1])
    with col1:
        ok = st.button("Войти", use_container_width=True)
    with col2:
        st.caption("")

    if ok:
        if not APP_PASSWORD:
            st.error("Не задан APP_PASSWORD в Secrets. Добавь пароль в Secrets и перезапусти приложение.")
            return
        if pwd == APP_PASSWORD:
            st.session_state["authed"] = True
            st.rerun()
        else:
            st.error("Неверный пароль.")

    st.markdown('</div></div>', unsafe_allow_html=True)


# =========================
# APP
# =========================
def main():
    inject_css()
    gerb_b64 = load_gerb_base64()

    # Если пароль включен (APP_PASSWORD задан) — требуем вход
    if APP_PASSWORD and not is_authed():
        auth_block(gerb_b64)
        return

    # MAIN HEADER (с источником)
    st.markdown(hero_html(gerb_b64, show_source=True), unsafe_allow_html=True)

    # Data
    df_raw = load_registry_df(CSV_URL)
    df = prepare_df(df_raw)

    if df.empty:
        st.error("Данные не загрузились (реестр пустой). Проверьте CSV_URL в Secrets или наличие .xlsx в репозитории.")
        return

    # Filters
    st.markdown('<div class="filters-wrap">', unsafe_allow_html=True)

    # Списки фильтров
    sectors_all = sorted([s for s in df["sector"].unique().tolist() if s and s != "—"])
    statuses_all = sorted([s for s in df["status"].unique().tolist() if s and s != "—"])

    # 3 колонки фильтров (на мобиле Streamlit сам поставит вертикально)
    c1, c2, c3 = st.columns(3)

    with c1:
        sector_choice = st.selectbox("🏷️ Отрасль", options=["Все"] + sectors_all, index=0)

    # ВАЖНО: район зависит от отрасли
    df_for_districts = df.copy()
    if sector_choice != "Все":
        df_for_districts = df_for_districts[df_for_districts["sector"] == sector_choice]

    districts_all = sorted([d for d in df_for_districts["district"].unique().tolist() if d and d != "—"])

    with c2:
        district_choice = st.selectbox("📍 Район", options=["Все"] + districts_all, index=0)

    with c3:
        status_choice = st.selectbox("📌 Статус", options=["Все"] + statuses_all, index=0)

    q = st.text_input("🔎 Поиск (наименование / адрес / ответственный / id)", value="", placeholder="", label_visibility="visible")

    st.markdown('</div>', unsafe_allow_html=True)

    # Apply filters
    dff = df.copy()

    if sector_choice != "Все":
        dff = dff[dff["sector"] == sector_choice]

    if district_choice != "Все":
        dff = dff[dff["district"] == district_choice]

    if status_choice != "Все":
        dff = dff[dff["status"] == status_choice]

    if q.strip():
        qq = q.strip().lower()
        mask = (
            dff["name"].str.lower().str.contains(qq, na=False)
            | dff["address"].str.lower().str.contains(qq, na=False)
            | dff["responsible"].str.lower().str.contains(qq, na=False)
            | dff["id"].str.lower().str.contains(qq, na=False)
        )
        dff = dff[mask]

    st.markdown(f'<div class="count-line">Показано объектов: {len(dff)} из {len(df)}</div>', unsafe_allow_html=True)
    st.divider()

    # Render cards (ОДНА КОЛОНКА — как вы хотели)
    for _, row in dff.iterrows():
        render_card(row)

    # (опционально) кнопка выхода — если пароль включен
    if APP_PASSWORD:
        st.caption("")
        if st.button("Выйти", use_container_width=False):
            do_logout()
            st.rerun()


if __name__ == "__main__":
    main()
