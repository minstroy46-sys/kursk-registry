import base64
import re
from pathlib import Path

import pandas as pd
import streamlit as st


# =============================
# CONFIG
# =============================
st.set_page_config(page_title="Реестр объектов", layout="wide")


# =============================
# HELPERS
# =============================
def safe_text(v, fallback="—"):
    if v is None:
        return fallback
    try:
        if pd.isna(v):
            return fallback
    except Exception:
        pass
    s = str(v).strip()
    return s if s else fallback


def norm_col(s: str) -> str:
    """Normalize text/column names to compare them reliably."""
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = s.replace("ё", "е")
    s = re.sub(r"\s+", " ", s)
    return s


def pick_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Pick first matching column from candidates by normalized name."""
    cols = {norm_col(c): c for c in df.columns}
    for cand in candidates:
        nc = norm_col(cand)
        if nc in cols:
            return cols[nc]
    # also try contains matching
    for cand in candidates:
        nc = norm_col(cand)
        for c in df.columns:
            if nc and nc in norm_col(c):
                return c
    return None


def read_local_crest_b64() -> str | None:
    """Read assets/gerb.png and return base64 string."""
    p = Path(__file__).parent / "assets" / "gerb.png"
    if not p.exists():
        return None
    data = p.read_bytes()
    return base64.b64encode(data).decode("utf-8")


def move_prochie_to_bottom(items: list[str]) -> list[str]:
    """
    В списке отраслей переместить 'Прочие' (и близкие варианты) в самый низ.
    Работает без ломания оригинального написания.
    """
    if not items:
        return items

    def is_prochie(x: str) -> bool:
        nx = norm_col(x)
        return nx in ("прочие", "прочее")

    prochie = [x for x in items if is_prochie(x)]
    rest = [x for x in items if not is_prochie(x)]
    return rest + prochie


# =============================
# DATA LOADING
# =============================
@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    # Priority 1: CSV_URL from secrets
    csv_url = None
    try:
        csv_url = st.secrets.get("CSV_URL", None)
    except Exception:
        csv_url = None

    df = pd.DataFrame()

    if csv_url:
        try:
            df = pd.read_csv(csv_url)
        except Exception:
            # sometimes google gives ; separator or encoding issues
            try:
                df = pd.read_csv(csv_url, sep=";")
            except Exception:
                df = pd.DataFrame()

    # Priority 2: local XLSX in repo (if exists)
    if df.empty:
        candidates = [
            "РЕЕСТР_объектов_Курская_область_2025-2028.xlsx",
            "РЕЕСТР_объектов_Курская_область_2025-2028 (7).xlsx",
            "registry.xlsx",
            "data.xlsx",
        ]
        for name in candidates:
            p = Path(__file__).parent / name
            if p.exists():
                try:
                    df = pd.read_excel(p, sheet_name=0)
                    break
                except Exception:
                    pass

    if df is None or df.empty:
        return pd.DataFrame()

    df.columns = [str(c).strip() for c in df.columns]
    return df


def normalize_schema(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create unified columns:
    id, sector, district, name, address, responsible, status, work_flag, card_url, folder_url
    by mapping from Russian headers or already-normalized headers.
    """
    if df.empty:
        return df

    col_id = pick_col(df, ["id", "ID"])
    col_sector = pick_col(df, ["отрасль", "sector"])
    col_district = pick_col(df, ["район", "district"])
    col_name = pick_col(df, ["наименование_объекта", "наименование объекта", "объект", "name"])
    col_address = pick_col(df, ["адрес", "address"])
    col_resp = pick_col(df, ["ответственный", "responsible"])
    col_status = pick_col(df, ["статус", "status"])
    col_works = pick_col(df, ["работы", "works", "вид работ", "work_flag"])
    col_card = pick_col(
        df,
        ["ссылка_на_карточку_(google)", "ссылка на карточку", "card_url", "ссылка_на_карточку"],
    )
    col_folder = pick_col(
        df,
        ["ссылка_на_папку_(drive)", "ссылка на папку", "folder_url", "ссылка_на_папку"],
    )

    out = pd.DataFrame()
    out["id"] = df[col_id] if col_id else ""
    out["sector"] = df[col_sector] if col_sector else ""
    out["district"] = df[col_district] if col_district else ""
    out["name"] = df[col_name] if col_name else ""
    out["address"] = df[col_address] if col_address else ""
    out["responsible"] = df[col_resp] if col_resp else ""
    out["status"] = df[col_status] if col_status else ""
    out["work_flag"] = df[col_works] if col_works else ""
    out["card_url"] = df[col_card] if col_card else ""
    out["folder_url"] = df[col_folder] if col_folder else ""

    for c in out.columns:
        out[c] = out[c].astype(str).replace({"nan": "", "None": ""})

    return out


# =============================
# STYLES (ШАПКУ НЕ ТРОГАЕМ — оставляем как есть)
# =============================
crest_b64 = read_local_crest_b64()  # can be None

st.markdown(
    """
<style>
/* --- Page base --- */
.block-container { padding-top: 24px !important; max-width: 1200px; }
@media (max-width: 1200px){ .block-container { max-width: 96vw; } }

div[data-testid="stHorizontalBlock"]{ gap: 14px; }

/* Hide Streamlit footer/menu (не 100% гарантия на Cloud, но обычно помогает) */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* --- Hero (existing) --- */
.hero-wrap{ width:100%; display:flex; justify-content:center; margin-bottom: 14px; }
.hero{
  width: 100%;
  border-radius: 18px;
  padding: 18px 18px;
  background: radial-gradient(1200px 380px at 22% 30%, rgba(60,130,255,.22), rgba(0,0,0,0) 55%),
              linear-gradient(135deg, #0b2a57, #1b4c8f);
  box-shadow: 0 18px 34px rgba(0,0,0,.18);
  position: relative;
  overflow: hidden;
}
.hero:after{
  content:"";
  position:absolute;
  inset:-40px -120px auto auto;
  width: 520px; height: 320px;
  background: rgba(255,255,255,.08);
  transform: rotate(14deg);
  border-radius: 32px;
}
.hero-row{
  display:flex;
  align-items:flex-start;
  gap: 16px;
  position: relative;
  z-index: 2;
}
.hero-crest{
  width: 74px; height: 74px;
  border-radius: 14px;
  background: rgba(255,255,255,.10);
  display:flex;
  align-items:center;
  justify-content:center;
  border: 1px solid rgba(255,255,255,.16);
  flex: 0 0 auto;
}
.hero-crest img{
  width: 56px; height: 56px; object-fit: contain;
  filter: drop-shadow(0 6px 10px rgba(0,0,0,.35));
}
.hero-titles{ flex: 1 1 auto; min-width: 0; }
.hero-ministry{
  color: rgba(255,255,255,.95);
  font-weight: 900;
  font-size: 20px;
  line-height: 1.15;
}
.hero-app{
  margin-top: 6px;
  color: rgba(255,255,255,.92);
  font-weight: 800;
  font-size: 16px;
}
.hero-sub{
  margin-top: 6px;
  color: rgba(255,255,255,.78);
  font-size: 13px;
}
.pill{
  margin-top: 10px;
  display:inline-flex;
  align-items:center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(255,255,255,.16);
  background: rgba(255,255,255,.08);
  color: rgba(255,255,255,.90);
  font-size: 12px;
  font-weight: 700;
}

/* make title stay on one line as much as possible */
@media (max-width: 900px){
  .hero-ministry{ font-size: 16px; }
  .hero-row{ align-items:center; }
}

/* =========================
   CARDS (ONLY DESIGN CHANGE)
   ========================= */
.card{
  background: #ffffff;
  border: 1px solid rgba(15, 23, 42, .10);
  border-radius: 14px;
  padding: 16px 16px 14px 16px;
  box-shadow: 0 10px 22px rgba(0,0,0,.06);
  margin-bottom: 14px;
}

.card-title{
  font-size: 20px;
  line-height: 1.15;
  font-weight: 800;
  margin: 0 0 10px 0;
  color: #0f172a;
}

.card-grid{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 18px;
  margin-top: 6px;
}

.card-item{
  font-size: 14px;
  color: rgba(15, 23, 42, .92);
}
.card-item b{
  color: rgba(15, 23, 42, .95);
}

.card-tags{
  display:flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 12px;
}

.tag{
  display:inline-flex;
  align-items:center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(15, 23, 42, .10);
  background: rgba(15, 23, 42, .03);
  font-size: 13px;
  color: rgba(15, 23, 42, .90);
}

.card-actions{
  display:flex;
  gap: 12px;
  margin-top: 12px;
}

.a-btn{
  flex: 1 1 0;
  display:flex;
  justify-content:center;
  align-items:center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid rgba(15, 23, 42, .12);
  background: rgba(255,255,255,.95);
  text-decoration:none !important;
  color: rgba(15, 23, 42, .92) !important;
  font-weight: 700;
  font-size: 14px;
  transition: .12s ease-in-out;
}

.a-btn:hover{
  transform: translateY(-1px);
  box-shadow: 0 10px 18px rgba(0,0,0,.08);
}

.a-btn.disabled{
  opacity: .45;
  pointer-events: none;
}

.card-extra{
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed rgba(15, 23, 42, .14);
  font-size: 13px;
  color: rgba(15, 23, 42, .70);
}

/* Mobile: one column inside card grid */
@media (max-width: 900px){
  .card-grid{ grid-template-columns: 1fr; }
  .card-title{ font-size: 18px; }
}
</style>
""",
    unsafe_allow_html=True,
)


# =============================
# HERO (unchanged)
# =============================
crest_html = ""
if crest_b64:
    crest_html = f'<img src="data:image/png;base64,{crest_b64}" alt="Герб"/>'
else:
    crest_html = '<span style="color:rgba(255,255,255,.8);font-weight:800;font-size:12px;">герб</span>'

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
        <div class="pill">📄 Источник данных: Google Sheets (CSV)</div>
      </div>
    </div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)


# =============================
# AUTH (PASSWORD GATE)
# =============================
def get_app_password() -> str | None:
    try:
        return st.secrets.get("APP_PASSWORD", None)
    except Exception:
        return None


APP_PASSWORD = get_app_password()

# Если пароль задан в Secrets — включаем доступ по паролю
if APP_PASSWORD:
    if "auth_ok" not in st.session_state:
        st.session_state.auth_ok = False

    if not st.session_state.auth_ok:
        st.markdown("### 🔐 Доступ к реестру")
        st.write("Введите пароль для просмотра данных.")

        with st.form("login_form", clear_on_submit=False):
            pwd = st.text_input("Пароль", type="password")
            submitted = st.form_submit_button("Войти")

        if submitted:
            if pwd == APP_PASSWORD:
                st.session_state.auth_ok = True
                st.success("Доступ разрешён.")
                st.rerun()
            else:
                st.error("Неверный пароль.")

        st.stop()


# =============================
# LOAD + PREPARE
# =============================
raw = load_data()
if raw.empty:
    st.error("Данные не загрузились (реестр пустой). Проверьте CSV_URL в Secrets или наличие .xlsx в репозитории.")
    st.stop()

df = normalize_schema(raw)

# unique lists
sectors = sorted([x for x in df["sector"].unique().tolist() if str(x).strip()])
districts = sorted([x for x in df["district"].unique().tolist() if str(x).strip()])
statuses = sorted([x for x in df["status"].unique().tolist() if str(x).strip()])

# Прочие — в самый низ списка отраслей
sectors = move_prochie_to_bottom(sectors)

sectors = ["Все"] + sectors
districts = ["Все"] + districts
statuses = ["Все"] + statuses


# =============================
# FILTERS (unchanged logic)
# =============================
c1, c2, c3 = st.columns(3)
with c1:
    sector_sel = st.selectbox("🏷️ Отрасль", sectors, index=0, key="f_sector")
with c2:
    district_sel = st.selectbox("📍 Район", districts, index=0, key="f_district")
with c3:
    status_sel = st.selectbox("📌 Статус", statuses, index=0, key="f_status")

q = st.text_input("🔎 Поиск (наименование / адрес / ответственный / id)", value="", key="f_search").strip().lower()

filtered = df.copy()

if sector_sel != "Все":
    filtered = filtered[filtered["sector"].astype(str) == str(sector_sel)]
if district_sel != "Все":
    filtered = filtered[filtered["district"].astype(str) == str(district_sel)]
if status_sel != "Все":
    filtered = filtered[filtered["status"].astype(str) == str(status_sel)]

if q:

    def row_match(r):
        s = " ".join(
            [
                str(r.get("name", "")),
                str(r.get("address", "")),
                str(r.get("responsible", "")),
                str(r.get("id", "")),
            ]
        ).lower()
        return q in s

    filtered = filtered[filtered.apply(row_match, axis=1)]

st.caption(f"Показано объектов: {len(filtered)} из {len(df)}")
st.divider()


# =============================
# CARD RENDER (ONLY DESIGN CHANGE)
# =============================
def render_card(row: pd.Series):
    title = safe_text(row.get("name", ""), fallback="Объект")
    sector = safe_text(row.get("sector", ""), fallback="—")
    district = safe_text(row.get("district", ""), fallback="—")
    address = safe_text(row.get("address", ""), fallback="—")
    responsible = safe_text(row.get("responsible", ""), fallback="—")

    status = safe_text(row.get("status", ""), fallback="—")
    work_flag = safe_text(row.get("work_flag", ""), fallback="—")

    card_url = safe_text(row.get("card_url", ""), fallback="")
    folder_url = safe_text(row.get("folder_url", ""), fallback="")

    btn_card = (
        f'<a class="a-btn" href="{card_url}" target="_blank">📄 Открыть карточку</a>'
        if card_url and card_url != "—"
        else '<span class="a-btn disabled">📄 Открыть карточку</span>'
    )
    btn_folder = (
        f'<a class="a-btn" href="{folder_url}" target="_blank">📁 Открыть папку</a>'
        if folder_url and folder_url != "—"
        else '<span class="a-btn disabled">📁 Открыть папку</span>'
    )

    st.markdown(
        f"""
<div class="card">
  <div class="card-title">{title}</div>

  <div class="card-grid">
    <div class="card-item">🏷️ <b>Отрасль:</b> {sector}</div>
    <div class="card-item">📍 <b>Район:</b> {district}</div>
    <div class="card-item">🗺️ <b>Адрес:</b> {address}</div>
    <div class="card-item">👤 <b>Ответственный:</b> {responsible}</div>
  </div>

  <div class="card-tags">
    <span class="tag">📌 <b>Статус:</b> {status}</span>
    <span class="tag">🛠️ <b>Работы:</b> {work_flag}</span>
  </div>

  <div class="card-actions">
    {btn_card}
    {btn_folder}
  </div>

  <div class="card-extra">
    Место под фото и дополнительные пункты (заполнишь в реестре — мы красиво выведем позже).
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


# =============================
# OUTPUT: ONE COLUMN
# =============================
for _, r in filtered.iterrows():
    render_card(r)
