import base64
import re
from pathlib import Path
from datetime import datetime, date

import pandas as pd
import streamlit as st


# =============================
# CONFIG
# =============================
st.set_page_config(page_title="Реестр объектов", layout="wide")

# Ваш CSV (по умолчанию). Можно переопределить в Secrets: CSV_URL
DEFAULT_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQwA5g3ZuBmZlY3vQMbc7nautnpK7c4ioKtTYU_mTskZb6A6nJ_yeokKIvfbVBFH1jTPpzOgoBMD89n/pub?gid=1858741677&single=true&output=csv"


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
    if s.lower() in ("nan", "none", "null", "#n/a", "#ref!"):
        return fallback
    return s if s else fallback


def norm_col(s: str) -> str:
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = s.replace("ё", "е")
    s = re.sub(r"\s+", " ", s)
    return s


def pick_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    cols = {norm_col(c): c for c in df.columns}
    for cand in candidates:
        nc = norm_col(cand)
        if nc in cols:
            return cols[nc]
    # contains fallback
    for cand in candidates:
        nc = norm_col(cand)
        for c in df.columns:
            if nc and nc in norm_col(c):
                return c
    return None


def read_local_crest_b64() -> str | None:
    p = Path(__file__).parent / "assets" / "gerb.png"
    if not p.exists():
        return None
    return base64.b64encode(p.read_bytes()).decode("utf-8")


def move_prochie_to_bottom(items: list[str]) -> list[str]:
    if not items:
        return items

    def is_prochie(x: str) -> bool:
        nx = norm_col(x)
        return nx in ("прочие", "прочее")

    prochie = [x for x in items if is_prochie(x)]
    rest = [x for x in items if not is_prochie(x)]
    return rest + prochie


def parse_date_any(v) -> date | None:
    """Понимает dd.mm.yyyy, yyyy-mm-dd, datetime, excel-serial (число), и т.п."""
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except Exception:
        pass

    # already datetime/date
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v

    s = str(v).strip()
    if not s or s.lower() in ("nan", "none", "null", "#n/a", "#ref!"):
        return None

    # Excel serial (например 45652)
    # Если пришло как "45652.0"
    if re.fullmatch(r"\d+(\.\d+)?", s):
        try:
            num = float(s)
            if 20000 <= num <= 80000:  # грубая защита от "не дата"
                # Excel serial: 1899-12-30
                dt = pd.to_datetime(num, unit="D", origin="1899-12-30", errors="coerce")
                if pd.notna(dt):
                    return dt.date()
        except Exception:
            pass

    # dd.mm.yyyy or dd/mm/yyyy
    for fmt in ("%d.%m.%Y", "%d.%m.%y", "%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass

    # ISO
    try:
        dt = pd.to_datetime(s, errors="coerce", dayfirst=True)
        if pd.notna(dt):
            return dt.date()
    except Exception:
        pass

    return None


def fmt_date(v) -> str:
    d = parse_date_any(v)
    return d.strftime("%d.%m.%Y") if d else "—"


def money_fmt(v) -> str:
    s = safe_text(v, fallback="—")
    if s == "—":
        return s
    # убрать пробелы/запятые
    t = str(s).replace("\u00a0", " ").replace(" ", "").replace(",", ".")
    try:
        x = float(t)
        # без копеек, с пробелами
        return f"{x:,.0f}".replace(",", " ") + " ₽"
    except Exception:
        return s


def status_class(status_text: str) -> str:
    s = norm_col(status_text)
    if "останов" in s or "приостанов" in s:
        return "tag-status tag-red"
    if "проектир" in s:
        return "tag-status tag-yellow"
    if "строитель" in s:
        return "tag-status tag-green"
    return "tag-status"


def works_class(works_text: str) -> str:
    s = norm_col(works_text)
    if not s or s == "—":
        return "tag-gray"
    # "нет", "не ведутся", "не ведутся работы"
    if "не вед" in s or s in ("нет", "не идут", "не осуществляется"):
        return "tag-red"
    if s in ("да", "ведутся", "идут", "ведется", "выполняются") or "ведут" in s or "идут" in s:
        return "tag-green"
    return "tag-gray"


def updated_class(updated_value) -> tuple[str, str]:
    """
    Возвращает (css_class, label_text)
    """
    d = parse_date_any(updated_value)
    if not d:
        return ("tag-gray", "—")
    days = (date.today() - d).days
    if days <= 7:
        return ("tag-green", d.strftime("%d.%m.%Y"))
    if days <= 14:
        return ("tag-yellow", d.strftime("%d.%m.%Y"))
    return ("tag-red", d.strftime("%d.%m.%Y"))


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

    if not csv_url:
        csv_url = DEFAULT_CSV_URL

    try:
        df = pd.read_csv(csv_url)
    except Exception:
        try:
            df = pd.read_csv(csv_url, sep=";")
        except Exception:
            df = pd.DataFrame()

    # Priority 2: local XLSX in repo (if exists)
    if df.empty:
        candidates = [
            "РЕЕСТР_объектов_Курская_область_2025-2028.xlsx",
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
    Сохраняем базовые поля + “паспорт/финансы/сроки”.
    """
    if df.empty:
        return df

    # базовые
    col_id = pick_col(df, ["id", "ID"])
    col_sector = pick_col(df, ["sector", "отрасль"])
    col_district = pick_col(df, ["district", "район"])
    col_name = pick_col(df, ["object_name", "name", "наименование", "объект"])
    col_address = pick_col(df, ["address", "адрес"])
    col_resp = pick_col(df, ["responsible", "ответственный"])
    col_status = pick_col(df, ["status", "статус"])
    col_works = pick_col(df, ["works_in_progress", "work_flag", "работы", "works"])
    col_issues = pick_col(df, ["issues", "проблемы", "проблемные вопросы"])
    col_updated = pick_col(df, ["updated_at", "last_update", "обновлено", "дата обновления"])

    col_card = pick_col(df, ["card_url", "ссылка на карточку", "ссылка_на_карточку"])
    col_folder = pick_col(df, ["folder_url", "ссылка на папку", "ссылка_на_папку"])

    # паспорт/финансы/сроки (как у вас в EXPORT)
    col_state_program = pick_col(df, ["state_program"])
    col_federal_project = pick_col(df, ["federal_project"])
    col_regional_program = pick_col(df, ["regional_program"])

    col_agreement = pick_col(df, ["agreement"])
    col_agreement_date = pick_col(df, ["agreement_date"])
    col_agreement_amount = pick_col(df, ["agreement_amount"])

    col_capacity_seats = pick_col(df, ["capacity_seats"])
    col_area_m2 = pick_col(df, ["area_m2"])
    col_target_deadline = pick_col(df, ["target_deadline"])

    col_design = pick_col(df, ["design"])
    col_psd_cost = pick_col(df, ["psd_cost"])
    col_designer = pick_col(df, ["designer"])

    col_expertise = pick_col(df, ["expertise"])
    col_expertise_conclusion = pick_col(df, ["expertise_conclusion"])
    col_expertise_date = pick_col(df, ["expertise_date"])

    col_rns = pick_col(df, ["rns"])
    col_rns_date = pick_col(df, ["rns_date"])
    col_rns_expiry = pick_col(df, ["rns_expiry"])

    col_contract = pick_col(df, ["contract"])
    col_contract_date = pick_col(df, ["contract_date"])
    col_contractor = pick_col(df, ["contractor"])
    col_contract_price = pick_col(df, ["contract_price"])

    col_end_plan = pick_col(df, ["end_date_plan"])
    col_end_fact = pick_col(df, ["end_date_fact"])
    col_readiness = pick_col(df, ["readiness"])
    col_paid = pick_col(df, ["paid"])

    out = pd.DataFrame()

    def get(c):
        return df[c] if c else ""

    out["id"] = get(col_id)
    out["sector"] = get(col_sector)
    out["district"] = get(col_district)
    out["name"] = get(col_name)
    out["address"] = get(col_address)
    out["responsible"] = get(col_resp)
    out["status"] = get(col_status)
    out["works_in_progress"] = get(col_works)
    out["issues"] = get(col_issues)
    out["updated_at"] = get(col_updated)
    out["card_url"] = get(col_card)
    out["folder_url"] = get(col_folder)

    out["state_program"] = get(col_state_program)
    out["federal_project"] = get(col_federal_project)
    out["regional_program"] = get(col_regional_program)

    out["agreement"] = get(col_agreement)
    out["agreement_date"] = get(col_agreement_date)
    out["agreement_amount"] = get(col_agreement_amount)

    out["capacity_seats"] = get(col_capacity_seats)
    out["area_m2"] = get(col_area_m2)
    out["target_deadline"] = get(col_target_deadline)

    out["design"] = get(col_design)
    out["psd_cost"] = get(col_psd_cost)
    out["designer"] = get(col_designer)

    out["expertise"] = get(col_expertise)
    out["expertise_conclusion"] = get(col_expertise_conclusion)
    out["expertise_date"] = get(col_expertise_date)

    out["rns"] = get(col_rns)
    out["rns_date"] = get(col_rns_date)
    out["rns_expiry"] = get(col_rns_expiry)

    out["contract"] = get(col_contract)
    out["contract_date"] = get(col_contract_date)
    out["contractor"] = get(col_contractor)
    out["contract_price"] = get(col_contract_price)

    out["end_date_plan"] = get(col_end_plan)
    out["end_date_fact"] = get(col_end_fact)
    out["readiness"] = get(col_readiness)
    out["paid"] = get(col_paid)

    # normalize basic
    for c in out.columns:
        out[c] = out[c].astype(str).replace({"nan": "", "None": "", "NaT": ""})

    return out


# =============================
# STYLES
# =============================
crest_b64 = read_local_crest_b64()

st.markdown(
    """
<style>
.block-container { padding-top: 24px !important; max-width: 1200px; }
@media (max-width: 1200px){ .block-container { max-width: 96vw; } }
div[data-testid="stHorizontalBlock"]{ gap: 14px; }

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* --- HERO --- */
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
.hero-row{ display:flex; align-items:flex-start; gap: 16px; position: relative; z-index: 2; }
.hero-crest{
  width: 74px; height: 74px; border-radius: 14px;
  background: rgba(255,255,255,.10);
  display:flex; align-items:center; justify-content:center;
  border: 1px solid rgba(255,255,255,.16);
  flex: 0 0 auto;
}
.hero-crest img{ width: 56px; height: 56px; object-fit: contain; filter: drop-shadow(0 6px 10px rgba(0,0,0,.35)); }
.hero-ministry{ color: rgba(255,255,255,.95); font-weight: 900; font-size: 20px; line-height: 1.15; }
.hero-app{ margin-top: 6px; color: rgba(255,255,255,.92); font-weight: 800; font-size: 16px; }
.hero-sub{ margin-top: 6px; color: rgba(255,255,255,.78); font-size: 13px; }
@media (max-width: 900px){ .hero-ministry{ font-size: 16px; } .hero-row{ align-items:center; } }

/* ===== Cards ===== */
.card{
  background: #ffffff;
  border: 1px solid rgba(15, 23, 42, .10);
  border-radius: 16px;
  padding: 16px 16px 12px 16px;
  box-shadow: 0 10px 22px rgba(0,0,0,.06);
  margin-bottom: 14px;
  position: relative;
  overflow: hidden;
}
.card:before{
  content:"";
  position:absolute;
  left:0; top:0; bottom:0;
  width: 6px;
  background: rgba(59,130,246,.25);
}
.card[data-accent="green"]:before{ background: rgba(34,197,94,.30); }
.card[data-accent="yellow"]:before{ background: rgba(245,158,11,.28); }
.card[data-accent="red"]:before{ background: rgba(239,68,68,.28); }

.card-title{
  font-size: 20px;
  line-height: 1.20;
  font-weight: 900;
  margin: 2px 0 8px 0;
  color: #0f172a;
  letter-spacing: -0.2px;
}
.card-subchips{
  display:flex;
  gap: 8px;
  flex-wrap: wrap;
  margin: 0 0 10px 0;
}
.chip{
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
.chip-id{
  background: rgba(37,99,235,.10);
  border-color: rgba(37,99,235,.18);
  font-weight: 800;
}

.card-grid{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 18px;
  margin-top: 4px;
}
.card-item{ font-size: 14px; color: rgba(15, 23, 42, .92); }
.card-item b{ color: rgba(15, 23, 42, .95); }

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
.tag-status{ font-weight: 900; }
.tag-green{ background: rgba(34,197,94,.10); border-color: rgba(34,197,94,.22); }
.tag-yellow{ background: rgba(245,158,11,.12); border-color: rgba(245,158,11,.25); }
.tag-red{ background: rgba(239,68,68,.10); border-color: rgba(239,68,68,.22); }
.tag-gray{ background: rgba(15,23,42,.04); border-color: rgba(15,23,42,.10); }

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
  border-radius: 12px;
  border: 1px solid rgba(15, 23, 42, .12);
  background: rgba(255,255,255,.95);
  text-decoration:none !important;
  color: rgba(15, 23, 42, .92) !important;
  font-weight: 800;
  font-size: 14px;
  transition: .12s ease-in-out;
}
.a-btn:hover{ transform: translateY(-1px); box-shadow: 0 10px 18px rgba(0,0,0,.08); }
.a-btn.disabled{ opacity: .45; pointer-events: none; }

/* Expander styling */
div[data-testid="stExpander"] details{
  border-radius: 14px !important;
  border: 1px solid rgba(15, 23, 42, .10) !important;
  background: rgba(15, 23, 42, .02) !important;
}
div[data-testid="stExpander"] summary{
  font-weight: 900 !important;
  font-size: 14px !important;
}
div[data-testid="stExpander"] summary:hover{
  background: rgba(37,99,235,.06) !important;
}

/* Details grid */
.detail-grid{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 18px;
  margin-top: 8px;
}
.detail-row{
  font-size: 13px;
  color: rgba(15,23,42,.85);
  line-height: 1.35;
}
.detail-row b{ color: rgba(15,23,42,.95); }
.hr-soft{ height:1px; background: rgba(15,23,42,.08); margin: 10px 0; }

.warn-box{
  background: rgba(239,68,68,.06);
  border: 1px solid rgba(239,68,68,.18);
  border-radius: 12px;
  padding: 10px 12px;
  font-size: 13px;
  color: rgba(15,23,42,.92);
}

/* Mobile */
@media (max-width: 900px){
  .card-grid{ grid-template-columns: 1fr; }
  .detail-grid{ grid-template-columns: 1fr; }
  .card-title{ font-size: 18px; }
}
</style>
""",
    unsafe_allow_html=True,
)


# =============================
# HERO
# =============================
crest_html = (
    f'<img src="data:image/png;base64,{crest_b64}" alt="Герб"/>'
    if crest_b64
    else '<span style="color:rgba(255,255,255,.8);font-weight:800;font-size:12px;">герб</span>'
)

st.markdown(
    f"""
<div class="hero-wrap">
  <div class="hero">
    <div class="hero-row">
      <div class="hero-crest">{crest_html}</div>
      <div class="hero-titles">
        <div class="hero-ministry">Министерство восстановления, развития приграничья и строительства Курской области</div>
        <div class="hero-app">Реестр объектов</div>
        <div class="hero-sub">Единый список объектов 2025–2028 с фильтрами и переходом в карточку/папку.</div>
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
    st.error("Данные не загрузились. Проверьте CSV_URL (Secrets) или публикацию CSV из Google Sheets.")
    st.stop()

df = normalize_schema(raw)

# filters lists
sectors = sorted([x for x in df["sector"].unique().tolist() if str(x).strip()])
districts = sorted([x for x in df["district"].unique().tolist() if str(x).strip()])
statuses = sorted([x for x in df["status"].unique().tolist() if str(x).strip()])

sectors = move_prochie_to_bottom(sectors)

sectors = ["Все"] + sectors
districts = ["Все"] + districts
statuses = ["Все"] + statuses


# =============================
# FILTERS
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
        s = " ".join([str(r.get("name", "")), str(r.get("address", "")), str(r.get("responsible", "")), str(r.get("id", ""))]).lower()
        return q in s

    filtered = filtered[filtered.apply(row_match, axis=1)]

st.caption(f"Показано объектов: {len(filtered)} из {len(df)}")
st.divider()


# =============================
# CARD RENDER
# =============================
def render_card(row: pd.Series):
    title = safe_text(row.get("name", ""), fallback="Объект")
    sector = safe_text(row.get("sector", ""), fallback="—")
    district = safe_text(row.get("district", ""), fallback="—")
    address = safe_text(row.get("address", ""), fallback="—")
    responsible = safe_text(row.get("responsible", ""), fallback="—")
    obj_id = safe_text(row.get("id", ""), fallback="—")

    status = safe_text(row.get("status", ""), fallback="—")
    works = safe_text(row.get("works_in_progress", ""), fallback="—")
    issues = safe_text(row.get("issues", ""), fallback="—")
    updated_raw = row.get("updated_at", "")

    card_url = safe_text(row.get("card_url", ""), fallback="")
    folder_url = safe_text(row.get("folder_url", ""), fallback="")

    # updated traffic light
    upd_cls, upd_txt = updated_class(updated_raw)

    # works traffic light
    w_cls = works_class(works)

    # status accent for left stripe
    scls = status_class(status)
    accent = "blue"
    if "tag-red" in scls:
        accent = "red"
    elif "tag-yellow" in scls:
        accent = "yellow"
    elif "tag-green" in scls:
        accent = "green"

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

    # HEADER (короткая часть)
    st.markdown(
        f"""
<div class="card" data-accent="{accent}">
  <div class="card-title">{title}</div>

  <div class="card-subchips">
    <span class="chip chip-id">🆔 {obj_id}</span>
    <span class="chip">🏷️ {sector}</span>
    <span class="chip">📍 {district}</span>
  </div>

  <div class="card-grid">
    <div class="card-item">🗺️ <b>Адрес:</b> {address}</div>
    <div class="card-item">👤 <b>Ответственный:</b> {responsible}</div>
  </div>

  <div class="card-tags">
    <span class="tag {scls}">📌 <b>Статус:</b> {status}</span>
    <span class="tag {w_cls}">🛠️ <b>Работы:</b> {works}</span>
    <span class="tag {upd_cls}">⏱️ <b>Обновлено:</b> {upd_txt}</span>
  </div>

  <div class="card-actions">
    {btn_card}
    {btn_folder}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    # DETAILS (в expander)
    with st.expander("📎 Паспорт объекта и контрольные показатели — нажмите, чтобы раскрыть", expanded=False):
        # Проблемы
        if issues != "—":
            st.markdown(
                f"""
<div class="warn-box">
  ⚠️ <b>Проблемные вопросы:</b><br/>
  {issues}
</div>
""",
                unsafe_allow_html=True,
            )
        else:
            st.caption("Проблемные вопросы: —")

        st.markdown('<div class="hr-soft"></div>', unsafe_allow_html=True)

        # Разделы в 2 колонки
        def two_col_section(title_txt: str, left_rows: list[tuple[str, str]], right_rows: list[tuple[str, str]]):
            left_html = "".join([f'<div class="detail-row"><b>{k}</b> {v}</div>' for k, v in left_rows if v != "—"])
            right_html = "".join([f'<div class="detail-row"><b>{k}</b> {v}</div>' for k, v in right_rows if v != "—"])
            if not left_html and not right_html:
                return
            st.markdown(
                f"""
<div class="detail-row" style="font-weight:900; font-size:14px; margin-bottom:6px;">{title_txt}</div>
<div class="detail-grid">
  <div>{left_html if left_html else '<div class="detail-row">—</div>'}</div>
  <div>{right_html if right_html else '<div class="detail-row">—</div>'}</div>
</div>
<div class="hr-soft"></div>
""",
                unsafe_allow_html=True,
            )

        # Программы
        two_col_section(
            "🏛️ Программы",
            [
                ("ГП/СП:", safe_text(row.get("state_program"))),
                ("РП:", safe_text(row.get("regional_program"))),
            ],
            [
                ("ФП:", safe_text(row.get("federal_project"))),
            ],
        )

        # Соглашение
        two_col_section(
            "🧾 Соглашение",
            [
                ("№:", safe_text(row.get("agreement"))),
                ("Сумма:", money_fmt(row.get("agreement_amount"))),
            ],
            [
                ("Дата:", fmt_date(row.get("agreement_date"))),
            ],
        )

        # Параметры
        two_col_section(
            "📦 Параметры",
            [
                ("Мощность:", safe_text(row.get("capacity_seats"))),
                ("Целевой срок:", fmt_date(row.get("target_deadline"))),
            ],
            [
                ("Площадь:", safe_text(row.get("area_m2"))),
            ],
        )

        # ПСД / Экспертиза
        two_col_section(
            "📑 ПСД / Экспертиза",
            [
                ("Стоимость ПСД:", money_fmt(row.get("psd_cost"))),
                ("Экспертиза:", safe_text(row.get("expertise"))),
                ("Заключение:", safe_text(row.get("expertise_conclusion"))),
            ],
            [
                ("Проектировщик:", safe_text(row.get("designer"))),
                ("Дата экспертизы:", fmt_date(row.get("expertise_date"))),
                ("Проектирование:", safe_text(row.get("design"))),
            ],
        )

        # РНС
        two_col_section(
            "🏗️ РНС",
            [
                ("№ РНС:", safe_text(row.get("rns"))),
                ("Срок действия:", fmt_date(row.get("rns_expiry"))),
            ],
            [
                ("Дата:", fmt_date(row.get("rns_date"))),
            ],
        )

        # Контракт
        two_col_section(
            "🧱 Контракт",
            [
                ("№:", safe_text(row.get("contract"))),
                ("Подрядчик:", safe_text(row.get("contractor"))),
            ],
            [
                ("Дата:", fmt_date(row.get("contract_date"))),
                ("Цена:", money_fmt(row.get("contract_price"))),
            ],
        )

        # Сроки / Финансы
        two_col_section(
            "⏳ Сроки / Финансы",
            [
                ("Окончание (план):", fmt_date(row.get("end_date_plan"))),
                ("Готовность:", safe_text(row.get("readiness"))),
            ],
            [
                ("Окончание (факт):", fmt_date(row.get("end_date_fact"))),
                ("Оплачено:", money_fmt(row.get("paid"))),
            ],
        )


# =============================
# OUTPUT
# =============================
for _, r in filtered.iterrows():
    render_card(r)
