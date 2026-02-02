import os
import pandas as pd
import streamlit as st

# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------
st.set_page_config(
    page_title="Реестр объектов — Курская область",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ------------------------------------------------------------
# CSS (hero + cards + mobile)
# ------------------------------------------------------------
CSS = """
<style>
/* Make main container a bit wider but centered */
.block-container{
  max-width: 1200px !important;
  padding-top: 1.5rem !important;
  padding-bottom: 3rem !important;
}

/* Remove extra top padding added by Streamlit header area */
header[data-testid="stHeader"] { height: 0rem; }

/* HERO */
.hero-wrap{
  width:100%;
  display:flex;
  justify-content:center;
  margin: 0.5rem 0 1.2rem 0;
}
.hero{
  width:100%;
  border-radius: 18px;
  padding: 22px 22px;
  background: linear-gradient(135deg, #0b2a4b 0%, #1b4f8c 55%, #2a66b0 100%);
  position: relative;
  overflow:hidden;
  box-shadow: 0 18px 40px rgba(0,0,0,.18);
}
.hero:before{
  content:"";
  position:absolute;
  right:-120px;
  top:-120px;
  width:360px;
  height:360px;
  background: rgba(255,255,255,.16);
  border-radius: 50%;
}
.hero:after{
  content:"";
  position:absolute;
  right:-40px;
  bottom:-150px;
  width:280px;
  height:280px;
  background: rgba(255,255,255,.10);
  border-radius: 50%;
}
.hero-row{
  position: relative;
  z-index:2;
  display:flex;
  gap:16px;
  align-items:flex-start;
}
.hero-crest{
  width:56px;
  height:56px;
  border-radius: 12px;
  background: rgba(255,255,255,.12);
  display:flex;
  align-items:center;
  justify-content:center;
  flex: 0 0 auto;
  border: 1px solid rgba(255,255,255,.12);
}
.hero-crest img{
  width:40px;
  height:40px;
  object-fit: contain;
  filter: drop-shadow(0 6px 10px rgba(0,0,0,.35));
}
.hero-titles{
  color: rgba(255,255,255,.92);
  width: 100%;
  min-width: 0;
}
.hero-ministry{
  font-size: 18px;
  line-height: 1.25;
  font-weight: 800;
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
  margin-bottom: 10px;
}
.hero-pill{
  display:inline-flex;
  align-items:center;
  gap:8px;
  padding: 8px 10px;
  border-radius: 999px;
  background: rgba(255,255,255,.12);
  border: 1px solid rgba(255,255,255,.14);
  font-size: 12px;
  color: rgba(255,255,255,.92);
  max-width: 100%;
}
.hero-pill b{ font-weight: 800; }
.hero-pill span{
  opacity: .95;
}

/* FILTERS */
.filters-wrap{
  margin-top: 0.6rem;
  margin-bottom: 0.6rem;
}
.small-muted{
  opacity: .65;
  font-size: 12px;
}

/* CARD */
.card{
  border-radius: 18px;
  background: rgba(255,255,255,.92);
  border: 1px solid rgba(0,0,0,.06);
  box-shadow: 0 10px 22px rgba(0,0,0,.08);
  padding: 16px 16px 14px 16px;
  margin: 14px 0;
}
.card-title{
  font-size: 20px;
  font-weight: 900;
  line-height: 1.25;
  margin: 2px 0 10px 0;
  color: rgba(0,0,0,.86);
}
.kv{
  border-radius: 14px;
  background: rgba(0,0,0,.035);
  border: 1px solid rgba(0,0,0,.05);
  padding: 12px;
}
.kv-grid{
  display:grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px 14px;
}
.kv-item{
  display:flex;
  gap:10px;
  align-items:flex-start;
}
.kv-ico{
  width: 22px;
  text-align:center;
  flex: 0 0 22px;
  font-size: 16px;
  line-height: 1.2;
  margin-top: 1px;
}
.kv-label{
  font-weight: 800;
  color: rgba(0,0,0,.76);
  margin-right: 6px;
  white-space: nowrap;
}
.kv-val{
  color: rgba(0,0,0,.78);
}
.tags{
  display:flex;
  flex-wrap:wrap;
  gap:8px;
  margin-top: 10px;
}
.tag{
  display:inline-flex;
  align-items:center;
  gap:8px;
  padding: 7px 12px;
  border-radius: 999px;
  background: rgba(31,102,176,.10);
  border: 1px solid rgba(31,102,176,.18);
  color: rgba(0,0,0,.72);
  font-weight: 700;
  font-size: 12.5px;
}
.btn-row{
  display:grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 12px;
}
a.btn{
  display:flex;
  justify-content:center;
  align-items:center;
  gap:10px;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid rgba(0,0,0,.12);
  background: rgba(255,255,255,.72);
  text-decoration:none !important;
  color: rgba(0,0,0,.86) !important;
  font-weight: 900;
}
a.btn:hover{
  background: rgba(255,255,255,.92);
  border-color: rgba(0,0,0,.18);
}
.placeholder{
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dashed rgba(0,0,0,.14);
  color: rgba(0,0,0,.48);
  font-size: 12.5px;
}

/* LOGIN CARD */
.login-wrap{
  display:flex;
  justify-content:center;
  margin-top: 14px;
}
.login-card{
  width: min(720px, 96%);
  border-radius: 18px;
  background: rgba(255,255,255,.92);
  border: 1px solid rgba(0,0,0,.06);
  box-shadow: 0 16px 36px rgba(0,0,0,.10);
  padding: 16px 16px 10px 16px;
}

/* RESPONSIVE */
@media (max-width: 920px){
  .btn-row{ grid-template-columns: 1fr; }
  .kv-grid{ grid-template-columns: 1fr; }
  .hero-row{ align-items:flex-start; }
  .hero-ministry{ font-size: 17px; }
  .card-title{ font-size: 18px; }
}

/* DARK MODE SUPPORT */
@media (prefers-color-scheme: dark){
  .card, .login-card{
    background: rgba(18,22,30,.72);
    border: 1px solid rgba(255,255,255,.08);
    box-shadow: 0 14px 30px rgba(0,0,0,.35);
  }
  .card-title{ color: rgba(255,255,255,.92); }
  .kv{
    background: rgba(255,255,255,.06);
    border: 1px solid rgba(255,255,255,.07);
  }
  .kv-label{ color: rgba(255,255,255,.82); }
  .kv-val{ color: rgba(255,255,255,.78); }
  .tag{
    background: rgba(42,102,176,.18);
    border: 1px solid rgba(42,102,176,.28);
    color: rgba(255,255,255,.86);
  }
  a.btn{
    background: rgba(255,255,255,.06);
    border: 1px solid rgba(255,255,255,.10);
    color: rgba(255,255,255,.92) !important;
  }
  a.btn:hover{
    background: rgba(255,255,255,.10);
    border-color: rgba(255,255,255,.16);
  }
  .placeholder{
    border-top: 1px dashed rgba(255,255,255,.18);
    color: rgba(255,255,255,.55);
  }
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------
def get_secret(key: str, default: str = "") -> str:
    try:
        return str(st.secrets.get(key, default))
    except Exception:
        return default


def hero_html(show_source: bool) -> str:
    # crest file is in repo: assets/gerb.png
    crest_path = "assets/gerb.png"

    pill = ""
    if show_source:
        pill = """
        <div class="hero-pill">🗂️ <b>Источник данных:</b> <span>Google Sheets (CSV)</span></div>
        """

    return f"""
    <div class="hero-wrap">
      <div class="hero">
        <div class="hero-row">
          <div class="hero-crest">
            <img src="{crest_path}" />
          </div>
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


def normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    # Try to map common column names into expected keys
    # Expected keys used further: sector, district, status, name, address, responsible, card_url, folder_url
    colmap = {c.strip(): c for c in df.columns}

    def pick(*variants):
        for v in variants:
            if v in colmap:
                return colmap[v]
        return None

    c_sector = pick("Отрасль", "Сфера", "Тип", "Категория", "sector")
    c_district = pick("Район", "Муниципалитет", "district", "Муниципальное образование")
    c_status = pick("Статус", "Состояние", "status")
    c_name = pick("Наименование", "Название", "Объект", "name")
    c_address = pick("Адрес", "address")
    c_resp = pick("Ответственный", "Куратор", "responsible")
    c_card = pick("Ссылка на карточку", "Карточка", "card_url", "Ссылка_карточка")
    c_folder = pick("Ссылка на папку", "Папка", "folder_url", "Ссылка_папка")
    c_id = pick("ID", "id", "Код", "Шифр")

    out = pd.DataFrame()
    out["sector"] = df[c_sector] if c_sector else ""
    out["district"] = df[c_district] if c_district else ""
    out["status"] = df[c_status] if c_status else ""
    out["name"] = df[c_name] if c_name else ""
    out["address"] = df[c_address] if c_address else ""
    out["responsible"] = df[c_resp] if c_resp else ""
    out["card_url"] = df[c_card] if c_card else ""
    out["folder_url"] = df[c_folder] if c_folder else ""
    out["_id"] = df[c_id] if c_id else ""

    # Strings + clean
    for c in out.columns:
        out[c] = out[c].fillna("").astype(str).str.strip()

    # Optional: drop empty names
    out = out[out["name"].str.len() > 0].copy()
    return out


@st.cache_data(show_spinner=False, ttl=300)
def load_data(csv_url: str) -> pd.DataFrame:
    # Primary: CSV_URL from secrets
    if csv_url:
        df = pd.read_csv(csv_url)
        return df

    # Fallback: try local xlsx in repo (optional)
    for fp in ("registry.xlsx", "реестр.xlsx", "data.xlsx"):
        if os.path.exists(fp):
            return pd.read_excel(fp)

    return pd.DataFrame()


def render_card(row: pd.Series):
    name = row["name"]
    sector = row["sector"] or "—"
    district = row["district"] or "—"
    address = row["address"] or "—"
    responsible = row["responsible"] or "—"
    status = row["status"] or "—"

    card_url = row["card_url"].strip()
    folder_url = row["folder_url"].strip()

    # small helpers for icons
    def kv_item(icon, label, val):
        return f"""
        <div class="kv-item">
          <div class="kv-ico">{icon}</div>
          <div><span class="kv-label">{label}</span><span class="kv-val">{val}</span></div>
        </div>
        """

    btn_card = ""
    if card_url:
        btn_card = f"""<a class="btn" href="{card_url}" target="_blank" rel="noopener">📄 Открыть карточку</a>"""
    else:
        btn_card = """<a class="btn" href="#" onclick="return false;" style="opacity:.55; cursor:not-allowed;">📄 Открыть карточку</a>"""

    btn_folder = ""
    if folder_url:
        btn_folder = f"""<a class="btn" href="{folder_url}" target="_blank" rel="noopener">📁 Открыть папку</a>"""
    else:
        btn_folder = """<a class="btn" href="#" onclick="return false;" style="opacity:.55; cursor:not-allowed;">📁 Открыть папку</a>"""

    html = f"""
    <div class="card">
      <div class="card-title">{name}</div>
      <div class="kv">
        <div class="kv-grid">
          {kv_item("🏷️", "Отрасль:", sector)}
          {kv_item("📍", "Район:", district)}
          {kv_item("🗺️", "Адрес:", address)}
          {kv_item("👤", "Ответственный:", responsible)}
        </div>
      </div>

      <div class="tags">
        <div class="tag">📌 Статус: {status}</div>
      </div>

      <div class="btn-row">
        {btn_card}
        {btn_folder}
      </div>

      <div class="placeholder">
        Место под фото и дополнительные пункты (заполнишь в реестре — мы красиво выведем позже).
      </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def do_login_screen(app_password: str):
    # Shapka: WITHOUT source pill on password screen
    st.markdown(hero_html(show_source=False), unsafe_allow_html=True)

    st.markdown('<div class="login-wrap"><div class="login-card">', unsafe_allow_html=True)
    st.markdown("### 🔒 Доступ по паролю")
    st.markdown('<div class="small-muted">Введите пароль для входа в реестр.</div>', unsafe_allow_html=True)

    pwd = st.text_input("Пароль", type="password", label_visibility="collapsed", placeholder="Введите пароль…")
    colA, colB, colC = st.columns([1, 1, 1])
    with colB:
        if st.button("Войти", use_container_width=True):
            if pwd == app_password and app_password != "":
                st.session_state["authed"] = True
                st.rerun()
            else:
                st.error("Неверный пароль.")

    st.markdown("</div></div>", unsafe_allow_html=True)


# ------------------------------------------------------------
# AUTH
# ------------------------------------------------------------
APP_PASSWORD = get_secret("APP_PASSWORD", "")
if "authed" not in st.session_state:
    st.session_state["authed"] = False

# If password is set, require auth
if APP_PASSWORD:
    if not st.session_state["authed"]:
        do_login_screen(APP_PASSWORD)
        st.stop()

# ------------------------------------------------------------
# MAIN APP
# ------------------------------------------------------------
# Shapka with source pill
st.markdown(hero_html(show_source=True), unsafe_allow_html=True)

# Load & normalize
CSV_URL = get_secret("CSV_URL", "")
raw = load_data(CSV_URL)

if raw.empty:
    st.error("Данные не загрузились (реестр пустой). Проверьте CSV_URL в Secrets или наличие xlsx в репозитории.")
    st.stop()

df = normalize_cols(raw)

if df.empty:
    st.error("Данные прочитаны, но после нормализации список пустой (проверьте названия колонок и заполненность 'Наименование').")
    st.stop()

# ------------------------------------------------------------
# FILTERS (district depends on sector)
# ------------------------------------------------------------
st.markdown('<div class="filters-wrap">', unsafe_allow_html=True)

# Base options
all_sectors = sorted([x for x in df["sector"].unique() if x.strip()])  # remove empty
all_statuses = sorted([x for x in df["status"].unique() if x.strip()])

# Layout: 3 filters in a row (on mobile they stack automatically)
c1, c2, c3 = st.columns([1, 1, 1])

with c1:
    sector_opt = ["Все"] + all_sectors
    sector_sel = st.selectbox("🏷️ Отрасль", sector_opt, index=0)

# Filter df by sector first
dff = df.copy()
if sector_sel != "Все":
    dff = dff[dff["sector"] == sector_sel]

# District options depend on dff
districts = sorted([x for x in dff["district"].unique() if x.strip()])
with c2:
    district_opt = ["Все"] + districts
    district_sel = st.selectbox("📍 Район", district_opt, index=0)

if district_sel != "Все":
    dff = dff[dff["district"] == district_sel]

# Status options depend on current filtered set (optional but nice)
statuses = sorted([x for x in dff["status"].unique() if x.strip()])
with c3:
    status_opt = ["Все"] + statuses if statuses else ["Все"]
    status_sel = st.selectbox("📌 Статус", status_opt, index=0)

if status_sel != "Все":
    dff = dff[dff["status"] == status_sel]

# Search
search = st.text_input("🔎 Поиск (наименование / адрес / ответственный)", value="")

if search.strip():
    s = search.strip().lower()
    dff = dff[
        dff["name"].str.lower().str.contains(s, na=False)
        | dff["address"].str.lower().str.contains(s, na=False)
        | dff["responsible"].str.lower().str.contains(s, na=False)
        | dff["_id"].str.lower().str.contains(s, na=False)
    ]

st.markdown("</div>", unsafe_allow_html=True)

# Count
st.markdown(
    f'<div class="small-muted">Показано объектов: <b>{len(dff)}</b> из <b>{len(df)}</b></div>',
    unsafe_allow_html=True
)
st.divider()

# ------------------------------------------------------------
# LIST (ONE COLUMN)
# ------------------------------------------------------------
# Sort to keep stable output
dff = dff.reset_index(drop=True)

for _, row in dff.iterrows():
    render_card(row)
