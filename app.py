import os
import html
import pandas as pd
import streamlit as st


# ---------------------------
# PAGE CONFIG
# ---------------------------
st.set_page_config(
    page_title="Реестр объектов — Курская область",
    page_icon="📋",
    layout="wide",
)

# ---------------------------
# CSS (фикс шапки + адаптив)
# ---------------------------
APP_CSS = """
<style>
  /* ширина контейнера */
  .block-container{
    padding-top: 18px;
    padding-bottom: 48px;
    max-width: 1250px;
  }

  /* чуть приглушим фон */
  body{
    background: #f6f8fb;
  }

  /* скрыть стандартный футер/меню (не убирает кнопку Manage app на Cloud) */
  footer {visibility: hidden;}
  #MainMenu {visibility: hidden;}

  /* HERO */
  .hero{
    position: relative;
    border-radius: 18px;
    padding: 18px 22px;
    background: linear-gradient(135deg, #26477f 0%, #17335e 55%, #10294b 100%);
    box-shadow: 0 18px 40px rgba(0,0,0,0.18);
    overflow: hidden;
    margin-bottom: 16px;
  }
  .hero:after{
    content:"";
    position:absolute;
    top:-80px;
    right:-140px;
    width: 520px;
    height: 380px;
    background: rgba(255,255,255,0.08);
    transform: rotate(18deg);
    border-radius: 60px;
  }
  .hero-inner{
    position: relative;
    display:flex;
    gap:16px;
    align-items:center;
  }
  .hero-logo{
    width:78px;
    height:78px;
    min-width:78px;
    border-radius:14px;
    background: rgba(255,255,255,0.08);
    display:flex;
    align-items:center;
    justify-content:center;
    border: 1px solid rgba(255,255,255,0.12);
  }
  .hero-logo img{
    width:58px;
    height:58px;
    object-fit:contain;
    filter: drop-shadow(0 10px 16px rgba(0,0,0,0.25));
  }
  .hero-titles{
    flex: 1;
    color:#fff;
    line-height: 1.15;
  }
  .hero-ministry{
    font-size: 22px;
    font-weight: 800;
    letter-spacing: 0.2px;
    margin: 0 0 6px 0;
  }
  .hero-app{
    font-size: 18px;
    font-weight: 700;
    opacity: 0.92;
    margin: 0 0 8px 0;
  }
  .hero-sub{
    font-size: 13px;
    opacity: 0.86;
    margin: 0 0 10px 0;
  }
  .hero-pill{
    display:inline-flex;
    align-items:center;
    gap:8px;
    font-size: 12px;
    padding: 6px 10px;
    border-radius: 999px;
    background: rgba(255,255,255,0.10);
    border: 1px solid rgba(255,255,255,0.18);
    width: fit-content;
  }

  /* FILTER LABEL ICONS */
  .lbl{
    font-weight: 700;
  }

  /* CARD */
  .card{
    border-radius: 16px;
    background: #ffffff;
    border: 1px solid rgba(16,24,40,0.08);
    box-shadow: 0 10px 24px rgba(16,24,40,0.06);
    padding: 14px 14px 12px 14px;
    margin-bottom: 14px;
  }
  .card-title{
    font-size: 16px;
    font-weight: 800;
    margin-bottom: 10px;
    color: #0f172a;
  }
  .meta{
    border-radius: 12px;
    background: #f4f6f9;
    border: 1px solid rgba(16,24,40,0.06);
    padding: 10px 10px;
  }
  .meta-row{
    display:flex;
    gap:8px;
    margin: 4px 0;
    align-items:flex-start;
    color:#0f172a;
    font-size: 13px;
  }
  .meta-ico{
    width: 18px;
    min-width: 18px;
    opacity: 0.95;
    line-height: 1.2;
    margin-top: 1px;
  }
  .badges{
    display:flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 10px;
  }
  .badge{
    display:inline-flex;
    align-items:center;
    gap:6px;
    padding: 5px 10px;
    border-radius: 999px;
    border: 1px solid rgba(2,6,23,0.10);
    background: rgba(2,6,23,0.02);
    font-size: 12px;
    color: #0f172a;
  }

  /* small screens */
  @media (max-width: 700px){
    .block-container{
      padding-left: 12px;
      padding-right: 12px;
      padding-top: 10px;
    }
    .hero{
      padding: 14px 14px;
    }
    .hero-inner{
      gap:12px;
      align-items:flex-start;
    }
    .hero-logo{
      width:66px;
      height:66px;
      min-width:66px;
    }
    .hero-logo img{
      width:50px;
      height:50px;
    }
    .hero-ministry{
      font-size: 16px;
      line-height: 1.15;
    }
    .hero-app{
      font-size: 14px;
    }
    .hero-sub{
      font-size: 12px;
    }
  }
</style>
"""
st.markdown(APP_CSS, unsafe_allow_html=True)


# ---------------------------
# DATA LOADING
# ---------------------------
@st.cache_data(ttl=300, show_spinner=False)
def load_data() -> pd.DataFrame:
    """
    Источник:
    1) st.secrets["CSV_URL"] (Google Sheets CSV / любой CSV)
    2) локальный xlsx (для тестов)
    """
    csv_url = None
    try:
        csv_url = st.secrets.get("CSV_URL")
    except Exception:
        csv_url = None

    if csv_url:
        df0 = pd.read_csv(csv_url)
    else:
        # локально (если вы запускаете у себя)
        local_xlsx = "РЕЕСТР_объектов_Курская_область_2025-2028.xlsx"
        if os.path.exists(local_xlsx):
            df0 = pd.read_excel(local_xlsx)
        else:
            # fallback: попробуем открыть ваш текущий файл в репозитории, если он там есть
            df0 = pd.DataFrame()

    return df0


def norm(s: str) -> str:
    return str(s).strip()


def safe_text(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, float) and pd.isna(v):
        return "—"
    s = str(v).strip()
    return s if s and s.lower() != "nan" else "—"


def first_existing_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    cols = list(df.columns)
    for c in candidates:
        if c in cols:
            return c
    # попробуем поиск по нижнему регистру
    lower_map = {str(x).strip().lower(): x for x in cols}
    for c in candidates:
        if c.lower() in lower_map:
            return lower_map[c.lower()]
    return None


def build_registry(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    ВАЖНО: ваш файл содержит:
    - 'объект' = ID/код (ZDR-001)
    - 'Наименование_объекта' = НАИМЕНОВАНИЕ
    - 'Адрес' = адрес
    """
    if df_raw is None or df_raw.empty:
        return pd.DataFrame(columns=[
            "id", "code", "name", "sector", "district", "address",
            "responsible", "status", "works", "card_url", "folder_url"
        ])

    col_id = first_existing_col(df_raw, ["ID", "id"])
    col_code = first_existing_col(df_raw, ["объект", "code"])
    col_name = first_existing_col(df_raw, ["Наименование_объекта", "наименование_объекта", "name", "Название", "Наименование"])
    col_sector = first_existing_col(df_raw, ["Отрасль", "sector"])
    col_district = first_existing_col(df_raw, ["Район", "district"])
    col_address = first_existing_col(df_raw, ["Адрес", "address"])
    col_resp = first_existing_col(df_raw, ["Ответственный", "responsible"])
    col_status = first_existing_col(df_raw, ["Статус", "status"])
    col_works = first_existing_col(df_raw, ["Работы_ведутся", "Работы", "works"])
    col_card = first_existing_col(df_raw, ["Ссылка_на_карточку_(Google)", "card_url", "Ссылка на карточку"])
    col_folder = first_existing_col(df_raw, ["Ссылка_на_папку_(Drive)", "folder_url", "Ссылка на папку"])

    out = pd.DataFrame()
    out["id"] = df_raw[col_id] if col_id else ""
    out["code"] = df_raw[col_code] if col_code else ""
    out["name"] = df_raw[col_name] if col_name else ""
    out["sector"] = df_raw[col_sector] if col_sector else ""
    out["district"] = df_raw[col_district] if col_district else ""
    out["address"] = df_raw[col_address] if col_address else ""
    out["responsible"] = df_raw[col_resp] if col_resp else ""
    out["status"] = df_raw[col_status] if col_status else ""
    out["works"] = df_raw[col_works] if col_works else ""
    out["card_url"] = df_raw[col_card] if col_card else ""
    out["folder_url"] = df_raw[col_folder] if col_folder else ""

    # приводим к строкам
    for c in out.columns:
        out[c] = out[c].astype(str).replace({"nan": "", "None": ""}).fillna("").map(lambda x: str(x).strip())

    return out


def order_districts(values: list[str]) -> list[str]:
    """
    Курск первым, Курский район вторым, остальное по алфавиту.
    """
    vals = [v for v in values if v and v != "—"]
    vals_unique = sorted(set(vals), key=lambda x: x.lower())

    def pop_val(name: str):
        nonlocal vals_unique
        for i, v in enumerate(vals_unique):
            if v.strip().lower() == name.strip().lower():
                vals_unique.pop(i)
                return v
        return None

    first = pop_val("Курск")
    second = pop_val("Курский район")

    ordered = []
    if first:
        ordered.append(first)
    if second:
        ordered.append(second)
    ordered.extend(vals_unique)
    return ordered


# ---------------------------
# HERO
# ---------------------------
def render_hero():
    crest_path = os.path.join("assets", "gerb.png")
    crest_html = ""
    if os.path.exists(crest_path):
        crest_html = f'<div class="hero-logo"><img src="data:image/png;base64,{img_to_b64(crest_path)}"/></div>'
    else:
        crest_html = '<div class="hero-logo">🏛️</div>'

    hero_html = f"""
    <div class="hero">
      <div class="hero-inner">
        {crest_html}
        <div class="hero-titles">
          <div class="hero-ministry">Министерство восстановления, развития приграничья и строительства Курской области</div>
          <div class="hero-app">Реестр объектов</div>
          <div class="hero-sub">Единый список объектов 2025–2028 с быстрыми фильтрами и переходом в карточку/папку.</div>
          <div class="hero-pill">📄 Источник данных: Google Sheets (CSV)</div>
        </div>
      </div>
    </div>
    """
    st.markdown(hero_html, unsafe_allow_html=True)


def img_to_b64(path: str) -> str:
    import base64
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# ---------------------------
# UI
# ---------------------------
df_raw = load_data()
df = build_registry(df_raw)

render_hero()

# FILTERS
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown('<span class="lbl">🏷️ Отрасль</span>', unsafe_allow_html=True)
    sectors = ["Все"] + sorted([s for s in df["sector"].unique() if s and s != "—"], key=lambda x: x.lower())
    sector_sel = st.selectbox("", sectors, index=0, key="sector_sel")

with col2:
    st.markdown('<span class="lbl">📍 Район</span>', unsafe_allow_html=True)
    districts = ["Все"] + order_districts([d for d in df["district"].unique() if d and d != "—"])
    district_sel = st.selectbox("", districts, index=0, key="district_sel")

with col3:
    st.markdown('<span class="lbl">📌 Статус</span>', unsafe_allow_html=True)
    statuses = ["Все"] + sorted([s for s in df["status"].unique() if s and s != "—"], key=lambda x: x.lower())
    status_sel = st.selectbox("", statuses, index=0, key="status_sel")

st.markdown('<span class="lbl">🔎 Поиск (наименование / адрес / ответственный / id)</span>', unsafe_allow_html=True)
q = st.text_input("", value="", key="search_q")

# APPLY FILTERS
f = df.copy()

if sector_sel != "Все":
    f = f[f["sector"].str.lower() == sector_sel.lower()]

if district_sel != "Все":
    f = f[f["district"].str.lower() == district_sel.lower()]

if status_sel != "Все":
    f = f[f["status"].str.lower() == status_sel.lower()]

if q.strip():
    qq = q.strip().lower()
    f = f[
        f["name"].str.lower().str.contains(qq, na=False)
        | f["address"].str.lower().str.contains(qq, na=False)
        | f["responsible"].str.lower().str.contains(qq, na=False)
        | f["code"].str.lower().str.contains(qq, na=False)
        | f["id"].str.lower().str.contains(qq, na=False)
    ]

st.caption(f"Показано объектов: {len(f)} из {len(df)}")
st.divider()


# ---------------------------
# CARD RENDER
# ---------------------------
def render_card(row: pd.Series, key_suffix: str):
    # берём ТОЛЬКО название объекта
    title = safe_text(row.get("name"))
    if title == "—":
        title = "Объект"

    sector = safe_text(row.get("sector"))
    district = safe_text(row.get("district"))
    address = safe_text(row.get("address"))
    resp = safe_text(row.get("responsible"))
    status = safe_text(row.get("status"))
    works = safe_text(row.get("works"))

    card_url = (row.get("card_url") or "").strip()
    folder_url = (row.get("folder_url") or "").strip()

    # экранируем текст для HTML
    def esc(x: str) -> str:
        return html.escape(x, quote=True)

    card_html = f"""
    <div class="card">
      <div class="card-title">{esc(title)}</div>

      <div class="meta">
        <div class="meta-row"><span class="meta-ico">🏷️</span><span><b>Отрасль:</b> {esc(sector)}</span></div>
        <div class="meta-row"><span class="meta-ico">📍</span><span><b>Район:</b> {esc(district)}</span></div>
        <div class="meta-row"><span class="meta-ico">🗺️</span><span><b>Адрес:</b> {esc(address)}</span></div>
        <div class="meta-row"><span class="meta-ico">👤</span><span><b>Ответственный:</b> {esc(resp)}</span></div>
      </div>

      <div class="badges">
        <span class="badge">📌 <b>Статус:</b> {esc(status)}</span>
        <span class="badge">🛠️ <b>Работы:</b> {esc(works)}</span>
      </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

    b1, b2 = st.columns(2)
    with b1:
        if card_url and card_url.lower().startswith("http"):
            st.link_button("📄 Открыть карточку", card_url, use_container_width=True, key=f"card_{key_suffix}")
        else:
            st.button("📄 Открыть карточку", use_container_width=True, disabled=True, key=f"card_dis_{key_suffix}")

    with b2:
        if folder_url and folder_url.lower().startswith("http"):
            st.link_button("📁 Открыть папку", folder_url, use_container_width=True, key=f"folder_{key_suffix}")
        else:
            st.button("📁 Открыть папку", use_container_width=True, disabled=True, key=f"folder_dis_{key_suffix}")


# GRID (2 cols)
items = list(f.itertuples(index=False))
for i in range(0, len(items), 2):
    c1, c2 = st.columns(2)
    with c1:
        r = pd.Series(items[i]._asdict())
        render_card(r, key_suffix=f"{i}_l")
    with c2:
        if i + 1 < len(items):
            r = pd.Series(items[i + 1]._asdict())
            render_card(r, key_suffix=f"{i}_r")
