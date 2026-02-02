import os
import base64
import pandas as pd
import streamlit as st


# ----------------------------
# PAGE
# ----------------------------
st.set_page_config(
    page_title="Реестр объектов — Курская область",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ----------------------------
# HELPERS
# ----------------------------
def _img_to_b64(path: str) -> str:
    """Load local image and return base64 string. Returns empty string if not found."""
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return ""


@st.cache_data(ttl=300, show_spinner=False)
def load_registry() -> pd.DataFrame:
    """
    Priority:
    1) st.secrets["CSV_URL"] (Google Sheets CSV published)
    2) local .xlsx in repo (registry_public sheet) if exists
    """
    csv_url = None
    try:
        csv_url = st.secrets.get("CSV_URL", None)
    except Exception:
        csv_url = None

    df = pd.DataFrame()

    # 1) From Google Sheets CSV
    if csv_url:
        try:
            # keep_default_na=False to avoid "nan" strings ruining UI
            df = pd.read_csv(csv_url, dtype=str, keep_default_na=False)
        except Exception as e:
            st.warning(f"Не удалось прочитать CSV_URL из Secrets: {e}")

    # 2) Fallback to local xlsx
    if df.empty:
        # if you keep an xlsx in repo, put its name here (optional)
        for candidate in [
            "РЕЕСТР_объектов_Курская_область_2025-2028.xlsx",
            "registry.xlsx",
            "data.xlsx",
        ]:
            if os.path.exists(candidate):
                try:
                    df = pd.read_excel(candidate, sheet_name="registry_public", dtype=str)
                    df = df.fillna("")
                    break
                except Exception:
                    pass

    # Normalize columns (important!)
    df.columns = [c.strip() for c in df.columns]

    # Expected columns for your registry_public
    expected = {
        "id", "sector", "district", "name", "responsible",
        "status", "work_flag", "address", "card_url", "folder_url"
    }

    # If вдруг пришли русские заголовки — пробуем мягко переименовать
    ru_map = {
        "ID": "id",
        "Отрасль": "sector",
        "Район": "district",
        "Наименование_объекта": "name",
        "Наименование объекта": "name",
        "Ответственный": "responsible",
        "Статус": "status",
        "Работы": "work_flag",
        "Адрес": "address",
        "Ссылка_на_карточку_(Google_док)": "card_url",
        "Ссылка на карточку": "card_url",
        "Ссылка_на_папку_(Drive)": "folder_url",
        "Ссылка на папку": "folder_url",
    }

    for k, v in ru_map.items():
        if k in df.columns and v not in df.columns:
            df = df.rename(columns={k: v})

    # Ensure all expected columns exist (create empty if missing)
    for col in expected:
        if col not in df.columns:
            df[col] = ""

    # Final clean
    df = df[list(expected)].copy()
    for col in df.columns:
        df[col] = df[col].astype(str).fillna("").str.strip()

    return df


def safe_text(x: str, fallback: str = "—") -> str:
    x = (x or "").strip()
    if x.lower() == "nan" or x == "":
        return fallback
    return x


def make_pill(text: str) -> str:
    return f"""<span class="pill">{text}</span>"""


# ----------------------------
# STYLES
# ----------------------------
crest_b64 = _img_to_b64(os.path.join("assets", "gerb.png"))

st.markdown(
    """
<style>
/* --- Make content nicely wide (but still aligned) --- */
section.main > div.block-container{
    max-width: 1600px;
    padding-top: 1.2rem;
    padding-bottom: 2.5rem;
    padding-left: 2.2rem;
    padding-right: 2.2rem;
}

/* Hide default Streamlit footer/menu (Cloud overlay "Manage app" cannot be removed) */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* --- HERO --- */
.hero-wrap{
    width: 100%;
    margin: 0.4rem 0 1.0rem 0;
}
.hero{
    width: 100%;
    background: linear-gradient(180deg, #183a6e 0%, #0f2f5f 100%);
    border-radius: 16px;
    padding: 18px 20px;
    box-shadow: 0 14px 30px rgba(0,0,0,.18);
    position: relative;
    overflow: hidden;
}
.hero:before{
    content:"";
    position:absolute;
    right:-160px;
    top:-140px;
    width:520px;
    height:520px;
    background: radial-gradient(circle, rgba(255,255,255,.10) 0%, rgba(255,255,255,0) 60%);
    transform: rotate(18deg);
}
.hero:after{
    content:"";
    position:absolute;
    left:45%;
    top:0;
    width:55%;
    height:100%;
    background: linear-gradient(115deg, rgba(255,255,255,.08) 0%, rgba(255,255,255,0) 60%);
    clip-path: polygon(0 0, 100% 0, 100% 100%, 18% 100%);
    opacity: .8;
}

/* hero row */
.hero-row{
    display:flex;
    align-items:center;
    gap: 16px;
    position: relative;
    z-index: 2;
}
.hero-crest{
    width: 76px;
    height: 76px;
    border-radius: 14px;
    background: rgba(255,255,255,.08);
    border: 1px solid rgba(255,255,255,.10);
    display:flex;
    align-items:center;
    justify-content:center;
    overflow:hidden;
    flex: 0 0 auto;
}
.hero-crest img{
    width: 64px;
    height: 64px;
    object-fit: contain;
}
.hero-titles{
    flex: 1 1 auto;
    min-width: 0;
}
.hero-ministry{
    font-weight: 800;
    font-size: 24px;
    line-height: 1.15;
    color: #fff;
    margin: 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.hero-app{
    font-weight: 800;
    font-size: 18px;
    color: rgba(255,255,255,.92);
    margin-top: 4px;
}
.hero-sub{
    font-size: 13px;
    color: rgba(255,255,255,.85);
    margin-top: 6px;
}
.pill{
    display:inline-flex;
    align-items:center;
    gap: 8px;
    padding: 7px 10px;
    border-radius: 999px;
    background: rgba(255,255,255,.10);
    border: 1px solid rgba(255,255,255,.12);
    color: rgba(255,255,255,.92);
    font-size: 12px;
    margin-top: 10px;
}

/* Mobile fixes */
@media (max-width: 900px){
  section.main > div.block-container{
    padding-left: 1.0rem;
    padding-right: 1.0rem;
  }
  .hero-row{ align-items:flex-start; }
  .hero-ministry{
    white-space: normal;       /* allow wrap on phone */
    overflow: visible;
    text-overflow: unset;
    font-size: 20px;
  }
  .hero-app{ font-size: 16px; }
}
</style>
""",
    unsafe_allow_html=True
)

# ----------------------------
# HERO RENDER (DO NOT TOUCH LATER)
# ----------------------------
crest_html = ""
if crest_b64:
    crest_html = f"""<img src="data:image/png;base64,{crest_b64}" alt="Герб">"""
else:
    # graceful fallback (won't break layout)
    crest_html = """<div style="color:rgba(255,255,255,.75);font-size:12px;">герб</div>"""

hero_html = f"""
<div class="hero-wrap">
  <div class="hero">
    <div class="hero-row">
      <div class="hero-crest">{crest_html}</div>
      <div class="hero-titles">
        <div class="hero-ministry">Министерство восстановления, развития приграничья и строительства Курской области</div>
        <div class="hero-app">Реестр объектов</div>
        <div class="hero-sub">Единый список объектов 2025–2028 с быстрыми фильтрами и переходом в карточку/папку.</div>
        <div class="pill">📄 Источник данных: Google Sheets (CSV)</div>
      </div>
    </div>
  </div>
</div>
"""
st.markdown(hero_html, unsafe_allow_html=True)

# ----------------------------
# LOAD DATA
# ----------------------------
df = load_registry()

if df.empty:
    st.error("Данные не загрузились (реестр пустой). Проверьте CSV_URL в Secrets или наличие .xlsx в репозитории.")
    st.stop()

# ----------------------------
# OPTIONAL DIAGNOSTICS (OFF by default)
# ----------------------------
with st.sidebar:
    st.markdown("### Диагностика")
    show_diag = st.checkbox("Показать диагностику", value=False)
    if show_diag:
        st.write("Колонки:", list(df.columns))
        st.write("Первые строки:", df.head(3))

# ----------------------------
# FILTERS (one row: Sector | District | Status)
# ----------------------------
sector_list = sorted([x for x in df["sector"].unique() if x and x.lower() != "nan"])
district_list = sorted([x for x in df["district"].unique() if x and x.lower() != "nan"])
status_list = sorted([x for x in df["status"].unique() if x and x.lower() != "nan"])

c1, c2, c3 = st.columns([1, 1, 1])

with c1:
    sector_sel = st.selectbox("🏷️ Отрасль", ["Все"] + sector_list, index=0)
with c2:
    district_sel = st.selectbox("📍 Район", ["Все"] + district_list, index=0)
with c3:
    status_sel = st.selectbox("📌 Статус", ["Все"] + status_list, index=0)

q = st.text_input("🔎 Поиск (наименование / адрес / ответственный / id)", value="")

# Apply filters
filtered = df.copy()

if sector_sel != "Все":
    filtered = filtered[filtered["sector"] == sector_sel]
if district_sel != "Все":
    filtered = filtered[filtered["district"] == district_sel]
if status_sel != "Все":
    filtered = filtered[filtered["status"] == status_sel]

if q.strip():
    s = q.strip().lower()
    mask = (
        filtered["name"].str.lower().str.contains(s, na=False) |
        filtered["address"].str.lower().str.contains(s, na=False) |
        filtered["responsible"].str.lower().str.contains(s, na=False) |
        filtered["id"].str.lower().str.contains(s, na=False)
    )
    filtered = filtered[mask]

st.caption(f"Показано объектов: {len(filtered)} из {len(df)}")
st.divider()

# ----------------------------
# CARDS
# ----------------------------
def render_card(row: pd.Series):
    title = safe_text(row.get("name", ""), fallback="Объект")
    sector = safe_text(row.get("sector", ""))
    district = safe_text(row.get("district", ""))
    address = safe_text(row.get("address", ""))
    responsible = safe_text(row.get("responsible", ""))
    status = safe_text(row.get("status", ""), fallback="—")
    work_flag = safe_text(row.get("work_flag", ""), fallback="—")

    card_url = safe_text(row.get("card_url", ""), fallback="")
    folder_url = safe_text(row.get("folder_url", ""), fallback="")

    with st.container(border=True):
        st.markdown(f"### {title}")

        # meta
        st.markdown(
            f"""
- 🏷️ **Отрасль:** {sector}
- 📍 **Район:** {district}
- 🗺️ **Адрес:** {address}
- 👤 **Ответственный:** {responsible}
""".strip()
        )

        a, b = st.columns([1, 1])
        with a:
            st.write(f"📌 **Статус:** {status}")
        with b:
            st.write(f"🛠️ **Работы:** {work_flag}")

        b1, b2 = st.columns(2)
        with b1:
            if card_url:
                st.link_button("📄 Открыть карточку", card_url, use_container_width=True)
            else:
                st.button("📄 Открыть карточку", disabled=True, use_container_width=True)

        with b2:
            if folder_url:
                st.link_button("📁 Открыть папку", folder_url, use_container_width=True)
            else:
                st.button("📁 Открыть папку", disabled=True, use_container_width=True)


# Grid: Streamlit will auto-stack on mobile
cols = st.columns(2)
i = 0
for _, r in filtered.iterrows():
    with cols[i % 2]:
        render_card(r)
    i += 1
