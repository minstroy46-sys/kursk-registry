import base64
import re
from pathlib import Path
from datetime import datetime, date

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


# =============================
# CONFIG
# =============================
st.set_page_config(page_title="Реестр объектов", layout="wide")

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
    data = p.read_bytes()
    return base64.b64encode(data).decode("utf-8")


def move_prochie_to_bottom(items: list[str]) -> list[str]:
    if not items:
        return items

    def is_prochie(x: str) -> bool:
        nx = norm_col(x)
        return nx in ("прочие", "прочее")

    prochie = [x for x in items if is_prochie(x)]
    rest = [x for x in items if not is_prochie(x)]
    return rest + prochie


def parse_any_date(v) -> date | None:
    """
    Поддержка:
    - dd.mm.yyyy
    - yyyy-mm-dd
    - datetime
    - excel serial (число)
    """
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except Exception:
        pass

    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v

    s = str(v).strip()
    if not s:
        return None

    # excel serial
    try:
        if re.fullmatch(r"\d+(\.\d+)?", s):
            num = float(s)
            # Excel "1899-12-30" base in pandas
            dt = pd.to_datetime(num, unit="D", origin="1899-12-30", errors="coerce")
            if pd.notna(dt):
                return dt.date()
    except Exception:
        pass

    # dd.mm.yyyy
    for fmt in ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass

    # try pandas
    try:
        dt = pd.to_datetime(s, errors="coerce", dayfirst=True)
        if pd.notna(dt):
            return dt.date()
    except Exception:
        pass

    return None


def days_ago_color(d: date | None) -> str:
    """
    1-7 зелёный, 8-14 жёлтый, 15+ красный, нет даты — серый
    """
    if not d:
        return "tag tag-gray"
    delta = (date.today() - d).days
    if delta <= 7:
        return "tag tag-green"
    if delta <= 14:
        return "tag tag-yellow"
    return "tag tag-red"


def works_color(work_text: str) -> str:
    """
    Мягкий светофор по 'Работы':
    - если "нет", "не ведутся", "не ведется", "останов" -> красный
    - если "да", "ведутся", "ведется", "идут" -> зеленый
    - иначе серый
    """
    s = norm_col(work_text)
    if any(x in s for x in ["нет", "не вед", "останов", "приостанов"]):
        return "tag tag-red"
    if any(x in s for x in ["да", "ведут", "ведет", "идут", "выполня"]):
        return "tag tag-green"
    return "tag tag-gray"


def status_color(status_text: str) -> str:
    """
    Цвет статуса:
    - остановлено/приостановлено -> red
    - проектирование -> yellow
    - строительство -> green
    - прочее -> gray
    """
    s = norm_col(status_text)
    if "останов" in s or "приостанов" in s:
        return "green"  # рамка карточки должна быть по статусу — но вы просили "рамка зависит от статуса"
    # ВНИМАНИЕ: ниже логика рамки будет отдельно (чтобы не путать)
    return "gray"


def card_border_class(status_text: str) -> str:
    s = norm_col(status_text)
    if "останов" in s or "приостанов" in s:
        return "border-red"
    if "проектир" in s:
        return "border-yellow"
    if "строитель" in s:
        return "border-green"
    return "border-gray"


def normalize_whitespace(s: str) -> str:
    s = str(s or "")
    s = s.replace("\n", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


# Сокращения для гибкого поиска
ABBR = {
    "фап": "фельдшерско-акушерский пункт фельдшерский пункт",
    "одкб": "областная детская клиническая больница",
    "црб": "центральная районная больница",
    "фок": "физкультурно-оздоровительный комплекс",
    "мкоу": "муниципальное казенное общеобразовательное учреждение",
    "окоу": "областное казенное общеобразовательное учреждение",
}


def expand_query(q: str) -> str:
    qn = norm_col(q)
    tokens = re.findall(r"[a-zа-я0-9]+", qn, flags=re.IGNORECASE)
    expanded = [qn]
    for t in tokens:
        if t in ABBR:
            expanded.append(ABBR[t])
    return " ".join(expanded).strip()


# =============================
# DATA LOADING
# =============================
@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    # Priority: secrets CSV_URL, иначе DEFAULT_CSV_URL
    csv_url = None
    try:
        csv_url = st.secrets.get("CSV_URL", None)
    except Exception:
        csv_url = None

    if not csv_url:
        csv_url = DEFAULT_CSV_URL

    df = pd.DataFrame()
    if csv_url:
        try:
            df = pd.read_csv(csv_url)
        except Exception:
            try:
                df = pd.read_csv(csv_url, sep=";")
            except Exception:
                df = pd.DataFrame()

    # Fallback local xlsx
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
    Поддерживаем ваши реальные колонки из registry_public:
    id, sector, district, name, responsible, status, work_flag, address, card_url, folder_url, issues, updated_at, ...
    """
    if df.empty:
        return df

    col_id = pick_col(df, ["id", "ID"])
    col_sector = pick_col(df, ["sector", "отрасль"])
    col_district = pick_col(df, ["district", "район"])
    col_name = pick_col(df, ["name", "наименование_объекта", "наименование объекта", "объект"])
    col_address = pick_col(df, ["address", "адрес"])
    col_resp = pick_col(df, ["responsible", "ответственный"])
    col_status = pick_col(df, ["status", "статус"])
    col_works = pick_col(df, ["work_flag", "работы", "вид работ"])
    col_card = pick_col(df, ["card_url", "ссылка_на_карточку", "ссылка на карточку", "ссылка_на_карточку_(google)"])
    col_folder = pick_col(df, ["folder_url", "ссылка_на_папку", "ссылка на папку", "ссылка_на_папку_(drive)"])

    col_issues = pick_col(df, ["issues", "проблемные вопросы", "проблемы"])
    col_updated = pick_col(df, ["updated_at", "last_update", "обновлено", "дата обновления", "updated"])

    # дополнительные (паспорт)
    passport_cols = {
        "state_program": pick_col(df, ["state_program", "гп/сп/гп"]),
        "federal_project": pick_col(df, ["federal_project", "фп"]),
        "regional_program": pick_col(df, ["regional_program", "рп"]),
        "agreement": pick_col(df, ["agreement", "соглашение", "номер соглашения"]),
        "agreement_date": pick_col(df, ["agreement_date", "дата соглашения"]),
        "agreement_amount": pick_col(df, ["agreement_amount", "сумма соглашения"]),
        "capacity_seats": pick_col(df, ["capacity_seats", "мощность", "мест", "посещений"]),
        "area_m2": pick_col(df, ["area_m2", "площадь"]),
        "target_deadline": pick_col(df, ["target_deadline", "целевой срок"]),
        "psd_cost": pick_col(df, ["psd_cost", "стоимость псд"]),
        "designer": pick_col(df, ["designer", "проектировщик"]),
        "expertise": pick_col(df, ["expertise", "экспертиза"]),
        "expertise_conclusion": pick_col(df, ["expertise_conclusion", "заключение экспертизы"]),
        "expertise_date": pick_col(df, ["expertise_date", "дата экспертизы"]),
        "rns": pick_col(df, ["rns", "рнс"]),
        "rns_date": pick_col(df, ["rns_date", "дата рнс"]),
        "rns_expiry": pick_col(df, ["rns_expiry", "срок действия", "рнс до"]),
        "contract": pick_col(df, ["contract", "контракт", "№ контракта", "номер контракта"]),
        "contract_date": pick_col(df, ["contract_date", "дата контракта"]),
        "contractor": pick_col(df, ["contractor", "подрядчик"]),
        "contract_price": pick_col(df, ["contract_price", "цена", "стоимость контракта"]),
        "end_date_plan": pick_col(df, ["end_date_plan", "end_plan", "окончание (план)"]),
        "end_date_fact": pick_col(df, ["end_date_fact", "end_fact", "окончание (факт)"]),
        "readiness": pick_col(df, ["readiness", "готовность"]),
        "paid": pick_col(df, ["paid", "оплачено"]),
    }

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
    out["issues"] = df[col_issues] if col_issues else ""
    out["updated_at"] = df[col_updated] if col_updated else ""

    for k, c in passport_cols.items():
        out[k] = df[c] if c else ""

    for c in out.columns:
        out[c] = out[c].astype(str).replace({"nan": "", "None": ""})

    return out


# =============================
# STYLES (LIGHT + DARK)
# =============================
crest_b64 = read_local_crest_b64()

st.markdown(
    """
<style>
/* ====== THEME TOKENS ====== */
:root{
  --bg: #f6f8fb;
  --card: #ffffff;
  --text: rgba(15, 23, 42, .94);
  --muted: rgba(15, 23, 42, .70);
  --stroke: rgba(15, 23, 42, .12);
  --stroke2: rgba(15, 23, 42, .10);
  --shadow: 0 12px 24px rgba(0,0,0,.06);
  --shadow2: 0 20px 40px rgba(0,0,0,.10);

  --green_bg: rgba(34, 197, 94, .12);
  --green_st: rgba(34, 197, 94, .25);

  --yellow_bg: rgba(245, 158, 11, .14);
  --yellow_st: rgba(245, 158, 11, .28);

  --red_bg: rgba(239, 68, 68, .10);
  --red_st: rgba(239, 68, 68, .22);

  --chip_bg: rgba(15, 23, 42, .04);
  --chip_st: rgba(15, 23, 42, .10);

  --hero1: #0b2a57;
  --hero2: #1b4c8f;
}

/* Dark mode */
@media (prefers-color-scheme: dark){
  :root{
    --bg: #0b1220;
    --card: #0f172a;
    --text: rgba(255,255,255,.92);
    --muted: rgba(255,255,255,.70);
    --stroke: rgba(255,255,255,.14);
    --stroke2: rgba(255,255,255,.10);
    --shadow: 0 12px 24px rgba(0,0,0,.35);
    --shadow2: 0 20px 46px rgba(0,0,0,.55);

    --chip_bg: rgba(255,255,255,.06);
    --chip_st: rgba(255,255,255,.12);

    --hero1: #0b2a57;
    --hero2: #173a72;
  }
}

/* ====== PAGE ====== */
html, body, [data-testid="stAppViewContainer"]{
  background: var(--bg) !important;
}
.block-container { padding-top: 18px !important; max-width: 1180px; }
div[data-testid="stHorizontalBlock"]{ gap: 14px; }

/* Hide Streamlit default UI */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* ====== HERO ====== */
.hero-wrap{ width:100%; display:flex; justify-content:center; margin-bottom: 12px; }
.hero{
  width: 100%;
  border-radius: 18px;
  padding: 18px 18px;
  background: radial-gradient(1200px 380px at 22% 30%, rgba(60,130,255,.22), rgba(0,0,0,0) 55%),
              linear-gradient(135deg, var(--hero1), var(--hero2));
  box-shadow: var(--shadow2);
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
@media (max-width: 900px){
  .hero-ministry{ font-size: 16px; }
  .hero-row{ align-items:center; }
}

/* ====== FILTER PANEL ====== */
.filter-panel{
  background: var(--card);
  border: 1px solid var(--stroke2);
  border-radius: 14px;
  padding: 12px 12px 6px 12px;
  box-shadow: var(--shadow);
  margin-bottom: 12px;
}

/* Make inputs nicer */
div[data-testid="stSelectbox"] > div,
div[data-testid="stTextInput"] > div{
  border-radius: 12px !important;
}

/* ====== CARD ====== */
.card{
  background: var(--card);
  border-radius: 16px;
  padding: 14px 14px 12px 14px;
  box-shadow: var(--shadow);
  margin-bottom: 14px;
  border: 2px solid transparent;
}

.border-green{ border-color: rgba(34,197,94,.55) !important; }
.border-yellow{ border-color: rgba(245,158,11,.55) !important; }
.border-red{ border-color: rgba(239,68,68,.50) !important; }
.border-gray{ border-color: var(--stroke) !important; }

.title-bar{
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid var(--stroke2);
  background: linear-gradient(135deg, rgba(60,130,255,.10), rgba(0,0,0,0));
  margin-bottom: 10px;
}
.card-title{
  font-size: 18px;
  line-height: 1.20;
  font-weight: 900;
  margin: 0;
  color: var(--text);
}

.card-grid{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 18px;
  margin-top: 6px;
}
.card-item{
  font-size: 14px;
  color: var(--text);
}
.card-item b{
  color: var(--text);
}

.chips{
  display:flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 8px;
}
.chip{
  display:inline-flex;
  align-items:center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid var(--chip_st);
  background: var(--chip_bg);
  font-size: 13px;
  color: var(--text);
}

.tag{
  display:inline-flex;
  align-items:center;
  gap: 7px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid var(--stroke);
  background: var(--chip_bg);
  font-size: 13px;
  color: var(--text);
  font-weight: 800;
}
.tag-green{ background: var(--green_bg); border-color: var(--green_st); }
.tag-yellow{ background: var(--yellow_bg); border-color: var(--yellow_st); }
.tag-red{ background: var(--red_bg); border-color: var(--red_st); }
.tag-gray{ background: var(--chip_bg); border-color: var(--chip_st); color: var(--text); font-weight: 700; }

.actions{
  display:flex;
  gap: 12px;
  margin-top: 10px;
}
.a-btn{
  flex: 1 1 0;
  display:flex;
  justify-content:center;
  align-items:center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid var(--stroke);
  background: rgba(255,255,255,.06);
  text-decoration:none !important;
  color: var(--text) !important;
  font-weight: 900;
  font-size: 14px;
  transition: .12s ease-in-out;
}
.a-btn:hover{
  transform: translateY(-1px);
  box-shadow: 0 14px 24px rgba(0,0,0,.10);
}
@media (prefers-color-scheme: light){
  .a-btn{ background: rgba(255,255,255,.95); }
}

.hr-soft{ height:1px; background: var(--stroke2); margin: 10px 0 10px 0; }

/* ===== PASSPORT (details) ===== */
.pass-wrap{
  margin-top: 10px;
  border-radius: 14px;
  border: 1px solid var(--stroke2);
  overflow: hidden;
}
.pass-summary{
  padding: 10px 12px;
  background: rgba(60,130,255,.08);
  cursor: pointer;
  user-select: none;
  color: var(--text);
  font-weight: 900;
  font-size: 14px;
}
.pass-body{
  padding: 12px;
}
.section{
  padding: 10px 0;
  border-top: 1px dashed var(--stroke2);
}
.section:first-child{ border-top: none; padding-top: 0; }
.section-title{
  font-weight: 900;
  margin-bottom: 6px;
  color: var(--text);
}
.row{
  color: var(--text);
  font-size: 13px;
  margin: 4px 0;
}
.row b{ color: var(--text); }

.issues-box{
  margin-top: 8px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(239,68,68,.25);
  background: rgba(239,68,68,.08);
  color: var(--text);
  font-size: 13px;
  line-height: 1.35;
}

.pass-footer{
  display:flex;
  justify-content:flex-end;
  padding-top: 10px;
}
.btn-mini{
  border: 1px solid var(--stroke);
  background: rgba(255,255,255,.06);
  color: var(--text);
  font-weight: 900;
  padding: 8px 10px;
  border-radius: 10px;
  cursor: pointer;
}
@media (prefers-color-scheme: light){
  .btn-mini{ background: rgba(255,255,255,.92); }
}

/* Mobile */
@media (max-width: 900px){
  .card-grid{ grid-template-columns: 1fr; }
  .card-title{ font-size: 17px; }
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
        <div class="hero-sub">Единый список объектов 2025–2028 с быстрыми фильтрами и переходом в карточку.</div>
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
        pwd = st.text_input("Пароль", type="password")
        if st.button("Войти"):
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
    st.error("Данные не загрузились. Проверьте CSV_URL в Secrets или корректность публикации листа в CSV.")
    st.stop()

df = normalize_schema(raw)

# списки фильтров
sectors = sorted([x for x in df["sector"].unique().tolist() if str(x).strip()])
districts = sorted([x for x in df["district"].unique().tolist() if str(x).strip()])
statuses = sorted([x for x in df["status"].unique().tolist() if str(x).strip()])

sectors = move_prochie_to_bottom(sectors)

sectors = ["Все"] + sectors
districts = ["Все"] + districts
statuses = ["Все"] + statuses


# =============================
# FILTERS (без st.form -> поиск НЕ требует Enter)
# =============================
st.markdown('<div class="filter-panel">', unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns([1.1, 1.1, 1.1, 1.4])
with c1:
    sector_sel = st.selectbox("🏷️ Отрасль", sectors, index=0, key="f_sector")
with c2:
    district_sel = st.selectbox("📍 Район", districts, index=0, key="f_district")
with c3:
    status_sel = st.selectbox("📌 Статус", statuses, index=0, key="f_status")
with c4:
    q = st.text_input(
        "🔎 Поиск (название / адрес / ответственный / сокращения: ФАП, ОДКБ, ЦРБ, ФОК)",
        value="",
        key="f_search",
        placeholder="Например: фап, одкб, курск, саморядово…",
    ).strip()

st.markdown("</div>", unsafe_allow_html=True)


# =============================
# FILTER LOGIC
# =============================
filtered = df.copy()

if sector_sel != "Все":
    filtered = filtered[filtered["sector"].astype(str) == str(sector_sel)]
if district_sel != "Все":
    filtered = filtered[filtered["district"].astype(str) == str(district_sel)]
if status_sel != "Все":
    filtered = filtered[filtered["status"].astype(str) == str(status_sel)]

if q:
    eq = expand_query(q)

    def row_match(r):
        s = " ".join(
            [
                str(r.get("name", "")),
                str(r.get("address", "")),
                str(r.get("responsible", "")),
                str(r.get("sector", "")),
                str(r.get("district", "")),
            ]
        )
        s = norm_col(s)
        return all(token in s for token in norm_col(eq).split()) if len(eq.split()) > 1 and any(t in ABBR for t in norm_col(q).split()) else (norm_col(q) in s or any(norm_col(x) in s for x in eq.split()))

    filtered = filtered[filtered.apply(row_match, axis=1)]

st.caption(f"Показано объектов: {len(filtered)} из {len(df)}")


# =============================
# RENDER
# =============================
def money_fmt(v: str) -> str:
    s = safe_text(v, fallback="—")
    if s == "—":
        return s
    ss = s.replace(" ", "").replace("\u00a0", "")
    try:
        num = float(ss.replace(",", "."))
        return f"{num:,.2f}".replace(",", " ").replace(".00", "") + " ₽"
    except Exception:
        return s


def readiness_fmt(v: str) -> str:
    s = safe_text(v, fallback="—")
    if s == "—":
        return s
    ss = s.replace(",", ".").strip()
    try:
        num = float(ss)
        # если 0.38 -> 38%
        if 0 <= num <= 1:
            num = num * 100
        return f"{num:.0f}%"
    except Exception:
        # если уже "38%" — оставим
        if "%" in s:
            return s
        return s


def render_passport(row: pd.Series, det_id: str):
    issues = normalize_whitespace(row.get("issues", ""))
    has_issues = bool(issues)

    sp = safe_text(row.get("state_program", ""), "—")
    fp = safe_text(row.get("federal_project", ""), "—")
    rp = safe_text(row.get("regional_program", ""), "—")

    agreement = safe_text(row.get("agreement", ""), "—")
    agreement_date = safe_text(row.get("agreement_date", ""), "—")
    agreement_amount = money_fmt(row.get("agreement_amount", ""))

    capacity = safe_text(row.get("capacity_seats", ""), "—")
    area = safe_text(row.get("area_m2", ""), "—")
    target = safe_text(row.get("target_deadline", ""), "—")

    psd_cost = money_fmt(row.get("psd_cost", ""))
    designer = safe_text(row.get("designer", ""), "—")
    expertise = safe_text(row.get("expertise", ""), "—")
    expertise_concl = safe_text(row.get("expertise_conclusion", ""), "—")
    expertise_date = safe_text(row.get("expertise_date", ""), "—")

    rns = safe_text(row.get("rns", ""), "—")
    rns_date = safe_text(row.get("rns_date", ""), "—")
    rns_exp = safe_text(row.get("rns_expiry", ""), "—")

    contract = safe_text(row.get("contract", ""), "—")
    contract_date = safe_text(row.get("contract_date", ""), "—")
    contractor = safe_text(row.get("contractor", ""), "—")
    contract_price = money_fmt(row.get("contract_price", ""))

    end_plan = safe_text(row.get("end_date_plan", ""), "—")
    end_fact = safe_text(row.get("end_date_fact", ""), "—")
    readiness = readiness_fmt(row.get("readiness", ""))
    paid = money_fmt(row.get("paid", ""))

    issues_html = f"""
      <div class="section">
        <div class="section-title">⚠️ Проблемные вопросы</div>
        <div class="issues-box">{issues}</div>
      </div>
    """ if has_issues else ""

    html = f"""
    <details class="pass-wrap" id="{det_id}">
      <summary class="pass-summary">📋 Паспорт объекта и контрольные показатели — нажмите, чтобы раскрыть</summary>
      <div class="pass-body">

        {issues_html}

        <div class="section">
          <div class="section-title">🏛️ Программы</div>
          <div class="row"><b>ГП/СП:</b> {sp}</div>
          <div class="row"><b>ФП:</b> {fp}</div>
          <div class="row"><b>РП:</b> {rp}</div>
        </div>

        <div class="section">
          <div class="section-title">🧾 Соглашение</div>
          <div class="row"><b>№:</b> {agreement}</div>
          <div class="row"><b>Дата:</b> {agreement_date}</div>
          <div class="row"><b>Сумма:</b> {agreement_amount}</div>
        </div>

        <div class="section">
          <div class="section-title">📦 Параметры</div>
          <div class="row"><b>Мощность:</b> {capacity}</div>
          <div class="row"><b>Площадь:</b> {area}</div>
          <div class="row"><b>Целевой срок:</b> {target}</div>
        </div>

        <div class="section">
          <div class="section-title">🧩 ПСД / Экспертиза</div>
          <div class="row"><b>Стоимость ПСД:</b> {psd_cost}</div>
          <div class="row"><b>Проектировщик:</b> {designer}</div>
          <div class="row"><b>Экспертиза:</b> {expertise}</div>
          <div class="row"><b>Заключение:</b> {expertise_concl}</div>
          <div class="row"><b>Дата экспертизы:</b> {expertise_date}</div>
        </div>

        <div class="section">
          <div class="section-title">🏗️ РНС</div>
          <div class="row"><b>№ РНС:</b> {rns}</div>
          <div class="row"><b>Дата:</b> {rns_date}</div>
          <div class="row"><b>Срок действия:</b> {rns_exp}</div>
        </div>

        <div class="section">
          <div class="section-title">🧱 Контракт</div>
          <div class="row"><b>№:</b> {contract}</div>
          <div class="row"><b>Дата:</b> {contract_date}</div>
          <div class="row"><b>Подрядчик:</b> {contractor}</div>
          <div class="row"><b>Цена:</b> {contract_price}</div>
        </div>

        <div class="section">
          <div class="section-title">⏱️ Сроки / Финансы</div>
          <div class="row"><b>Окончание (план):</b> {end_plan}</div>
          <div class="row"><b>Окончание (факт):</b> {end_fact}</div>
          <div class="row"><b>Готовность:</b> {readiness}</div>
          <div class="row"><b>Оплачено:</b> {paid}</div>
        </div>

        <div class="pass-footer">
          <button class="btn-mini" onclick="document.getElementById('{det_id}').open=false;">Свернуть паспорт</button>
        </div>

      </div>
    </details>
    """
    components.html(html, height=40, scrolling=False)


def render_card(row: pd.Series, idx: int):
    title = safe_text(row.get("name", ""), fallback="Объект")
    sector = safe_text(row.get("sector", ""), fallback="—")
    district = safe_text(row.get("district", ""), fallback="—")
    address = safe_text(row.get("address", ""), fallback="—")
    responsible = safe_text(row.get("responsible", ""), fallback="—")

    status = safe_text(row.get("status", ""), fallback="—")
    work_flag = safe_text(row.get("work_flag", ""), fallback="—")

    updated_raw = row.get("updated_at", "")
    upd_date = parse_any_date(updated_raw)
    upd_show = upd_date.strftime("%d.%m.%Y") if upd_date else "—"

    card_url = safe_text(row.get("card_url", ""), fallback="")
    # folder_url не используем (по требованию)

    border = card_border_class(status)

    # теги
    # статус: зеленый/желтый/красный/серый — по смыслу статуса
    s_norm = norm_col(status)
    if "останов" in s_norm or "приостанов" in s_norm:
        status_tag = "tag tag-red"
    elif "проектир" in s_norm:
        status_tag = "tag tag-yellow"
    elif "строитель" in s_norm:
        status_tag = "tag tag-green"
    else:
        status_tag = "tag tag-gray"

    works_tag = works_color(work_flag)
    upd_tag = days_ago_color(upd_date)

    # корректный href: только если это URL
    def is_http_url(x: str) -> bool:
        xx = str(x or "").strip()
        return xx.startswith("http://") or xx.startswith("https://")

    btn_card = (
        f'<a class="a-btn" href="{card_url}" target="_blank" rel="noopener noreferrer">📄 Открыть карточку</a>'
        if is_http_url(card_url)
        else '<span class="a-btn" style="opacity:.45;pointer-events:none;">📄 Карточка не привязана</span>'
    )

    st.markdown(
        f"""
<div class="card {border}">
  <div class="title-bar">
    <h3 class="card-title">{title}</h3>
  </div>

  <div class="chips">
    <span class="chip">🏷️ {sector}</span>
    <span class="chip">📍 {district}</span>
  </div>

  <div class="card-grid">
    <div class="card-item">🗺️ <b>Адрес:</b> {address}</div>
    <div class="card-item">👤 <b>Ответственный:</b> {responsible}</div>
  </div>

  <div class="chips" style="margin-top:10px;">
    <span class="{status_tag}">📌 Статус: {status}</span>
    <span class="{works_tag}">🛠️ Работы: {work_flag if work_flag else "—"}</span>
    <span class="{upd_tag}">🕘 Обновлено: {upd_show}</span>
  </div>

  <div class="actions">
    {btn_card}
  </div>

</div>
""",
        unsafe_allow_html=True,
    )

    # Паспорт отдельным блоком с нормальным “свернуть снизу”
    det_id = f"det_pass_{idx}"
    render_passport(row, det_id)


# =============================
# OUTPUT
# =============================
for i, (_, r) in enumerate(filtered.iterrows()):
    render_card(r, i)
