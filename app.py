import os
import base64
import pandas as pd
import streamlit as st


# ----------------------------
# CONFIG
# ----------------------------
st.set_page_config(
    page_title="Реестр объектов",
    page_icon="📌",
    layout="wide",
)

APP_TITLE = "Министерство восстановления, развития приграничья и строительства Курской области"
APP_SUBTITLE = "Реестр объектов"
APP_DESC = "Единый список объектов 2025–2028 с быстрыми фильтрами и переходом в карточку/папку."
DATA_PILL_TEXT = "Источник данных: Google Sheets (CSV)"


# ----------------------------
# HELPERS
# ----------------------------
def _read_asset_b64(path: str) -> str | None:
    """Read local image and return base64 string."""
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def get_secret(key: str, default: str = "") -> str:
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


def normalize_str(x):
    if pd.isna(x):
        return ""
    return str(x).strip()


def safe_col(df: pd.DataFrame, name: str) -> pd.Series:
    if name in df.columns:
        return df[name].fillna("").astype(str)
    return pd.Series([""] * len(df))


def load_data() -> pd.DataFrame:
    """
    Load data:
    - Prefer CSV_URL from secrets
    - If not exists, try local .xlsx
    """
    csv_url = get_secret("CSV_URL", "").strip()

    if csv_url:
        try:
            df = pd.read_csv(csv_url)
            return df
        except Exception as e:
            st.error(f"Не удалось загрузить CSV_URL. Ошибка: {e}")
            return pd.DataFrame()

    # fallback: local xlsx if exists
    for fname in ["registry.xlsx", "data.xlsx", "реестр.xlsx", "reestr.xlsx"]:
        if os.path.exists(fname):
            try:
                df = pd.read_excel(fname)
                return df
            except Exception as e:
                st.error(f"Не удалось прочитать {fname}. Ошибка: {e}")
                return pd.DataFrame()

    return pd.DataFrame()


def apply_global_css():
    st.markdown(
        """
        <style>
        /* Base */
        .block-container { padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1180px; }
        @media (min-width: 1400px){ .block-container { max-width: 1240px; } }

        /* Remove Streamlit default top padding a bit on mobile */
        @media (max-width: 768px){
          .block-container { padding-top: 0.8rem; }
        }

        /* Hero (Header) */
        .hero-wrap{
          margin: 8px auto 18px auto;
          border-radius: 18px;
          background: linear-gradient(135deg, #0b2b52 0%, #1b4c8c 55%, #2a5ea3 100%);
          position: relative;
          overflow: hidden;
          box-shadow: 0 18px 40px rgba(0,0,0,0.18);
        }
        .hero-wrap:before{
          content:'';
          position:absolute;
          right:-80px; top:-60px;
          width:320px; height:320px;
          background: rgba(255,255,255,0.14);
          border-radius: 50%;
          filter: blur(0px);
        }
        .hero-wrap:after{
          content:'';
          position:absolute;
          right:40px; top:70px;
          width:220px; height:220px;
          background: rgba(255,255,255,0.10);
          border-radius: 50%;
        }
        .hero{
          padding: 18px 18px;
          position: relative;
          z-index: 2;
        }
        .hero-row{
          display:flex;
          gap:14px;
          align-items:flex-start;
        }
        .hero-crest{
          width:56px; height:56px;
          border-radius: 12px;
          background: rgba(255,255,255,0.10);
          display:flex; align-items:center; justify-content:center;
          flex: 0 0 56px;
          border: 1px solid rgba(255,255,255,0.10);
        }
        .hero-crest img{ width:40px; height:40px; object-fit:contain; }

        .hero-titles{ flex: 1; min-width: 0; }
        .hero-ministry{
          color: rgba(255,255,255,0.95);
          font-weight: 800;
          line-height: 1.15;
          font-size: 18px;
          margin-top: 2px;
        }
        .hero-app{
          color: rgba(255,255,255,0.92);
          font-weight: 700;
          font-size: 14px;
          margin-top: 6px;
        }
        .hero-sub{
          color: rgba(255,255,255,0.82);
          font-size: 13px;
          margin-top: 6px;
          max-width: 920px;
        }
        .hero-pill{
          display:inline-flex;
          align-items:center;
          gap:10px;
          margin-top: 10px;
          padding: 8px 12px;
          border-radius: 999px;
          background: rgba(255,255,255,0.10);
          border: 1px solid rgba(255,255,255,0.12);
          color: rgba(255,255,255,0.92);
          font-size: 12.5px;
          width: fit-content;
        }

        /* Mobile header tweaks */
        @media (max-width: 768px){
          .hero-wrap{ border-radius: 16px; }
          .hero{ padding: 16px 14px; }
          .hero-ministry{ font-size: 20px; }
          .hero-sub{ font-size: 13.5px; }
        }

        /* Login card */
        .login-shell{
          margin: 12px auto 0 auto;
          max-width: 560px;
        }
        .login-card{
          background: rgba(255,255,255,0.85);
          border: 1px solid rgba(0,0,0,0.06);
          border-radius: 16px;
          padding: 16px 16px 8px 16px;
          box-shadow: 0 14px 30px rgba(0,0,0,0.12);
        }
        .login-title{
          font-weight: 800;
          font-size: 16px;
          margin-bottom: 4px;
        }
        .login-desc{
          color: rgba(0,0,0,0.60);
          font-size: 13px;
          margin-bottom: 12px;
        }

        /* Cards */
        .obj-card{
          border: 1px solid rgba(0,0,0,0.08);
          border-radius: 16px;
          padding: 16px 16px 14px 16px;
          background: #ffffff;
          box-shadow: 0 10px 22px rgba(0,0,0,0.06);
          margin-bottom: 14px;
        }
        .obj-title{
          font-size: 20px;
          font-weight: 900;
          line-height: 1.15;
          margin-bottom: 10px;
        }
        .obj-grid{
          border: 1px solid rgba(0,0,0,0.06);
          background: rgba(0,0,0,0.02);
          border-radius: 14px;
          padding: 12px;
          margin-bottom: 10px;
        }
        .kv{
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 10px 14px;
          align-items: start;
        }
        .kv-item{
          display:flex;
          gap: 8px;
          align-items:flex-start;
          min-width: 0;
        }
        .kv-ico{ width: 18px; flex: 0 0 18px; margin-top: 2px; }
        .kv-label{
          font-weight: 800;
          color: rgba(0,0,0,0.70);
          white-space: nowrap;
        }
        .kv-val{
          color: rgba(0,0,0,0.82);
          overflow-wrap:anywhere;
        }

        .obj-tags{
          display:flex;
          gap: 10px;
          flex-wrap: wrap;
          margin: 6px 0 10px 0;
        }
        .pill{
          display:inline-flex;
          align-items:center;
          gap:8px;
          padding: 7px 12px;
          border-radius: 999px;
          background: rgba(34, 91, 170, 0.08);
          border: 1px solid rgba(34, 91, 170, 0.20);
          font-size: 12.5px;
          font-weight: 800;
          color: rgba(0,0,0,0.70);
        }

        .obj-actions{
          display:grid;
          grid-template-columns: 1fr 1fr;
          gap: 10px;
          margin-top: 6px;
        }
        .btn-like{
          display:flex;
          justify-content:center;
          align-items:center;
          gap:10px;
          padding: 12px 14px;
          border-radius: 12px;
          border: 1px solid rgba(0,0,0,0.12);
          background: rgba(0,0,0,0.02);
          font-weight: 800;
          text-decoration: none !important;
          color: rgba(0,0,0,0.80) !important;
        }
        .btn-like:hover{
          background: rgba(34, 91, 170, 0.08);
          border-color: rgba(34, 91, 170, 0.30);
        }

        .obj-foot{
          margin-top: 10px;
          padding-top: 10px;
          border-top: 1px dashed rgba(0,0,0,0.12);
          color: rgba(0,0,0,0.55);
          font-size: 12.5px;
        }

        /* Mobile: cards in one column, actions stacked */
        @media (max-width: 768px){
          .kv{ grid-template-columns: 1fr; }
          .obj-actions{ grid-template-columns: 1fr; }
          .obj-title{ font-size: 18px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero(show_pill: bool):
    crest_b64 = _read_asset_b64("assets/gerb.png") or ""
    crest_img_html = ""
    if crest_b64:
        crest_img_html = f'<img src="data:image/png;base64,{crest_b64}" alt="герб"/>'

    pill_html = ""
    if show_pill:
        pill_html = f"""
        <div class="hero-pill">
          <span style="opacity:.95;">🗂</span>
          <span style="font-weight:800;">Источник данных:</span>
          <span style="opacity:.95;">Google Sheets (CSV)</span>
        </div>
        """

    hero_html = f"""
    <div class="hero-wrap">
      <div class="hero">
        <div class="hero-row">
          <div class="hero-crest">{crest_img_html}</div>
          <div class="hero-titles">
            <div class="hero-ministry">{APP_TITLE}</div>
            <div class="hero-app">{APP_SUBTITLE}</div>
            <div class="hero-sub">{APP_DESC}</div>
            {pill_html}
          </div>
        </div>
      </div>
    </div>
    """
    st.markdown(hero_html, unsafe_allow_html=True)


def password_gate() -> bool:
    """
    Returns True if user is authenticated.
    Uses st.session_state["auth_ok"].
    """
    if "auth_ok" not in st.session_state:
        st.session_state["auth_ok"] = False

    app_password = get_secret("APP_PASSWORD", "").strip()
    # If no password set -> allow access (but лучше задавать всегда)
    if not app_password:
        st.session_state["auth_ok"] = True
        return True

    if st.session_state["auth_ok"]:
        return True

    # Login UI
    st.markdown('<div class="login-shell">', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="login-card">
          <div class="login-title">🔒 Доступ по паролю</div>
          <div class="login-desc">Введите пароль для входа в реестр.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    pwd = st.text_input("Пароль", type="password", placeholder="Введите пароль…", label_visibility="collapsed")
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
    with col_btn2:
        if st.button("Войти", use_container_width=True):
            if pwd == app_password:
                st.session_state["auth_ok"] = True
                st.rerun()
            else:
                st.error("Неверный пароль.")
    st.markdown("</div>", unsafe_allow_html=True)

    return False


def build_filters(df: pd.DataFrame):
    # предполагаемые названия колонок (как у вас):
    # Отрасль, Район, Статус, Наименование_объекта/Наименование объекта/Наименование, Адрес, Ответственный
    col_sector = "Отрасль" if "Отрасль" in df.columns else None
    col_area = "Район" if "Район" in df.columns else None

    # статус может быть "Статус" или "Стадия/состояние" — подстрахуемся
    if "Статус" in df.columns:
        col_status = "Статус"
    elif "Стадия/состояние" in df.columns:
        col_status = "Стадия/состояние"
    else:
        col_status = None

    # фильтры
    sectors = ["Все"]
    if col_sector:
        sectors += sorted([x for x in df[col_sector].fillna("").astype(str).unique().tolist() if x.strip()])

    # умный список районов (будет пересчитан после выбора отрасли)
    st.markdown("####")  # небольшой отступ под шапкой

    c1, c2, c3 = st.columns([1, 1, 1])

    with c1:
        sector_sel = st.selectbox("🏷️ Отрасль", options=sectors, index=0)

    # пересчитываем районы по отрасли
    df_for_area = df.copy()
    if col_sector and sector_sel != "Все":
        df_for_area = df_for_area[df_for_area[col_sector].astype(str) == sector_sel]

    areas = ["Все"]
    if col_area:
        areas += sorted([x for x in df_for_area[col_area].fillna("").astype(str).unique().tolist() if x.strip()])

    with c2:
        area_sel = st.selectbox("📍 Район", options=areas, index=0)

    statuses = ["Все"]
    if col_status:
        statuses += sorted([x for x in df[col_status].fillna("").astype(str).unique().tolist() if x.strip()])

    with c3:
        status_sel = st.selectbox("📌 Статус", options=statuses, index=0)

    q = st.text_input("🔎 Поиск (наименование / адрес / ответственный)", value="")

    return sector_sel, area_sel, status_sel, q, col_sector, col_area, col_status


def filter_df(df: pd.DataFrame, sector_sel, area_sel, status_sel, q, col_sector, col_area, col_status):
    out = df.copy()

    if col_sector and sector_sel != "Все":
        out = out[out[col_sector].astype(str) == sector_sel]

    if col_area and area_sel != "Все":
        out = out[out[col_area].astype(str) == area_sel]

    if col_status and status_sel != "Все":
        out = out[out[col_status].astype(str) == status_sel]

    q = normalize_str(q)
    if q:
        # поля для поиска: наименование, адрес, ответственный
        name_col = None
        for cand in ["Наименование_объекта", "Наименование объекта", "Наименование", "Название", "name"]:
            if cand in out.columns:
                name_col = cand
                break

        addr_col = "Адрес" if "Адрес" in out.columns else None
        resp_col = "Ответственный" if "Ответственный" in out.columns else None
        id_col = "ID" if "ID" in out.columns else None

        hay = pd.Series([""] * len(out))
        if name_col:
            hay = hay + " " + out[name_col].fillna("").astype(str)
        if addr_col:
            hay = hay + " " + out[addr_col].fillna("").astype(str)
        if resp_col:
            hay = hay + " " + out[resp_col].fillna("").astype(str)
        if id_col:
            hay = hay + " " + out[id_col].fillna("").astype(str)

        out = out[hay.str.contains(q, case=False, na=False)]

    return out


def render_object_card(row: pd.Series):
    # колонки (как в вашем реестре)
    name_col = None
    for cand in ["Наименование_объекта", "Наименование объекта", "Наименование", "Название", "name"]:
        if cand in row.index:
            name_col = cand
            break

    sector = normalize_str(row.get("Отрасль", ""))
    area = normalize_str(row.get("Район", ""))
    addr = normalize_str(row.get("Адрес", ""))
    resp = normalize_str(row.get("Ответственный", ""))

    # статус и работы — как раньше у вас
    status = normalize_str(row.get("Статус", row.get("Стадия/состояние", "")))
    works = normalize_str(row.get("Работы", row.get("Вид работ", "")))

    # ссылки
    card_url = normalize_str(row.get("Ссылка_на_карточку_(Google)", row.get("Ссылка_на_карточку", row.get("card_url", ""))))
    folder_url = normalize_str(row.get("Ссылка_на_папку_(Drive)", row.get("Ссылка_на_папку", row.get("folder_url", ""))))

    title = normalize_str(row.get(name_col, "Без названия")) if name_col else "Объект"

    # Если нет работ/статуса — ставим прочерк
    status_show = status if status else "—"
    works_show = works if works else "—"

    # карточка
    html = f"""
    <div class="obj-card">
      <div class="obj-title">{title}</div>

      <div class="obj-grid">
        <div class="kv">
          <div class="kv-item">
            <div class="kv-ico">🏷️</div>
            <div><span class="kv-label">Отрасль:</span> <span class="kv-val">{sector if sector else "—"}</span></div>
          </div>

          <div class="kv-item">
            <div class="kv-ico">📍</div>
            <div><span class="kv-label">Район:</span> <span class="kv-val">{area if area else "—"}</span></div>
          </div>

          <div class="kv-item">
            <div class="kv-ico">🗺️</div>
            <div><span class="kv-label">Адрес:</span> <span class="kv-val">{addr if addr else "—"}</span></div>
          </div>

          <div class="kv-item">
            <div class="kv-ico">👤</div>
            <div><span class="kv-label">Ответственный:</span> <span class="kv-val">{resp if resp else "—"}</span></div>
          </div>
        </div>
      </div>

      <div class="obj-tags">
        <div class="pill">📌 Статус: {status_show}</div>
        <div class="pill">🛠️ Работы: {works_show}</div>
      </div>

      <div class="obj-actions">
        {f'<a class="btn-like" href="{card_url}" target="_blank" rel="noopener noreferrer">📄 Открыть карточку</a>' if card_url else '<div class="btn-like" style="opacity:.45; cursor:not-allowed;">📄 Карточка не указана</div>'}
        {f'<a class="btn-like" href="{folder_url}" target="_blank" rel="noopener noreferrer">📁 Открыть папку</a>' if folder_url else '<div class="btn-like" style="opacity:.45; cursor:not-allowed;">📁 Папка не указана</div>'}
      </div>

      <div class="obj-foot">
        Место под фото и дополнительные пункты (заполнишь в реестре — мы красиво выведем позже).
      </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# ----------------------------
# APP
# ----------------------------
apply_global_css()

# Шапка: на экране пароля pill НЕ показываем
authed = password_gate()
render_hero(show_pill=authed)

if not authed:
    # Ничего больше не рисуем
    st.stop()

# Данные
df = load_data()
if df.empty:
    st.warning("Данные не загрузились (реестр пустой). Проверьте CSV_URL в Secrets или наличие .xlsx в репозитории.")
    st.stop()

# Фильтры
sector_sel, area_sel, status_sel, q, col_sector, col_area, col_status = build_filters(df)
filtered = filter_df(df, sector_sel, area_sel, status_sel, q, col_sector, col_area, col_status)

# Счетчик
st.caption(f"Показано объектов: {len(filtered)} из {len(df)}")
st.markdown("<hr/>", unsafe_allow_html=True)

# Рендер карточек: одна колонка (как ты просил)
for _, row in filtered.iterrows():
    render_object_card(row)
