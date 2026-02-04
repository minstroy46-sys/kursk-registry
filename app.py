import base64
import re
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

# =============================
# CONFIG
# =============================
st.set_page_config(page_title="Реестр объектов", layout="wide")

# Если в Secrets нет CSV_URL — используем этот (ваш опубликованный CSV)
CSV_URL_DEFAULT = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQwA5g3ZuBmZlY3vQMbc7nautnpK7c4ioKtTYU_mTskZb6A6nJ_yeokKIvfbVBFH1jTPpzOgoBMD89n/pub?gid=1858741677&single=true&output=csv"


# =============================
# HELPERS
# =============================
BAD_VALUES = {"#ref!", "#n/a", "#error!", "nan", "none"}

def safe_text(v, fallback="—"):
    if v is None:
        return fallback
    try:
        if pd.isna(v):
            return fallback
    except Exception:
        pass
    s = str(v).strip()
    if not s:
        return fallback
    if s.strip().lower() in BAD_VALUES:
        return fallback
    return s


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
    """В списке отраслей переместить 'Прочие' (и близкие варианты) в самый низ."""
    if not items:
        return items

    def is_prochie(x: str) -> bool:
        nx = norm_col(x)
        return nx in ("прочие", "прочее")

    prochie = [x for x in items if is_prochie(x)]
    rest = [x for x in items if not is_prochie(x)]
    return rest + prochie


def status_class(status_text: str) -> str:
    """
    CSS-класс для подсветки статуса:
    - остановлено/приостановлено -> красный
    - проектирование -> желтый
    - строительство -> зеленый
    """
    s = norm_col(status_text)
    if "останов" in s or "приостанов" in s:
        return "status status-red"
    if "проектир" in s:
        return "status status-yellow"
    if "строитель" in s:
        return "status status-green"
    return "status"


def fmt_money(v) -> str:
    """Аккуратно форматируем деньги: 882623791.57 -> 882 623 791,57 ₽"""
    s = safe_text(v, fallback="—")
    if s == "—":
        return "—"
    # пытаемся распарсить число из строки
    try:
        x = float(str(v).replace(" ", "").replace("\u00a0", "").replace(",", "."))
        # если это "почти целое"
        if abs(x - round(x)) < 1e-9:
            return f"{int(round(x)):,}".replace(",", " ") + " ₽"
        else:
            # 2 знака после запятой
            part = f"{x:,.2f}".replace(",", " ").replace(".", ",")
            return part + " ₽"
    except Exception:
        return s


def fmt_number(v) -> str:
    s = safe_text(v, fallback="—")
    if s == "—":
        return "—"
    try:
        x = float(str(v).replace(" ", "").replace("\u00a0", "").replace(",", "."))
        if abs(x - round(x)) < 1e-9:
            return f"{int(round(x)):,}".replace(",", " ")
        return f"{x:,.2f}".replace(",", " ").replace(".", ",")
    except Exception:
        return s


def fmt_percent(v) -> str:
    s = safe_text(v, fallback="—")
    if s == "—":
        return "—"
    try:
        x = float(str(v).replace(" ", "").replace("\u00a0", "").replace(",", "."))
        # встречаются 0..1 или 0..100
        if 0 <= x <= 1:
            return f"{round(x * 100)}%"
        return f"{round(x)}%"
    except Exception:
        return s


def looks_like_gs_serial_date(x: float) -> bool:
    # Google Sheets serial date обычно ~ 40000..60000 (2010..2064)
    return 20000 <= x <= 80000


def gs_serial_to_date(x: float) -> datetime:
    # Google Sheets / Excel epoch:
    # В pandas обычно используют 1899-12-30 для Excel serial.
    return datetime(1899, 12, 30) + timedelta(days=float(x))


def fmt_date(v) -> str:
    """
    Приводим дату к dd.mm.yyyy.
    Поддержка:
    - нормальные строки (2026-02-04, 04.02.2026 и т.п.)
    - serial number из Google Sheets (например 45652)
    """
    if v is None:
        return "—"
    s = safe_text(v, fallback="—")
    if s == "—":
        return "—"

    # 1) если число (или строка-число) — пробуем serial date
    try:
        x = float(str(v).replace(" ", "").replace("\u00a0", "").replace(",", "."))
        if looks_like_gs_serial_date(x):
            d = gs_serial_to_date(x)
            return d.strftime("%d.%m.%Y")
    except Exception:
        pass

    # 2) пробуем распарсить как дату-строку
    try:
        dt = pd.to_datetime(s, dayfirst=True, errors="coerce")
        if not pd.isna(dt):
            return pd.Timestamp(dt).strftime("%d.%m.%Y")
    except Exception:
        pass

    return s


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
        csv_url = CSV_URL_DEFAULT

    # CSV from published google sheets
    df = pd.DataFrame()
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


def normalize_schema_keep_all(df: pd.DataFrame) -> pd.DataFrame:
    """
    НЕ режем таблицу (это важно!) — оставляем все колонки.
    Только приводим к единым именам базовые поля, чтобы фильтры/карточки работали стабильно.
    """
    if df.empty:
        return df

    df = df.copy()

    # найдем возможные русские варианты и переименуем в наши "эталонные" колонки
    col_id = pick_col(df, ["id", "ID", "код", "шифр"])
    col_sector = pick_col(df, ["sector", "отрасль"])
    col_district = pick_col(df, ["district", "район", "муниципалитет"])
    col_name = pick_col(df, ["object_name", "name", "наименование_объекта", "наименование объекта", "объект"])
    col_obj_type = pick_col(df, ["object_type", "тип объекта", "вид объекта"])
    col_resp = pick_col(df, ["responsible", "ответственный"])
    col_status = pick_col(df, ["status", "статус"])
    col_works = pick_col(df, ["works_in_progress", "work_flag", "работы", "вид работ"])
    col_issues = pick_col(df, ["issues", "проблемы", "проблемные вопросы"])
    col_last_update = pick_col(df, ["last_update", "updated_at", "обновлено", "дата обновления"])
    col_card = pick_col(df, ["card_url", "ссылка_на_карточку_(google)", "ссылка на карточку", "ссылка_на_карточку"])
    col_folder = pick_col(df, ["folder_url", "ссылка_на_папку_(drive)", "ссылка на папку", "ссылка_на_папку"])
    col_address = pick_col(df, ["address", "адрес"])

    rename_map = {}
    if col_id and col_id != "id":
        rename_map[col_id] = "id"
    if col_sector and col_sector != "sector":
        rename_map[col_sector] = "sector"
    if col_district and col_district != "district":
        rename_map[col_district] = "district"
    if col_name and col_name != "object_name":
        # у вас в реестре эталон: object_name
        rename_map[col_name] = "object_name"
    if col_obj_type and col_obj_type != "object_type":
        rename_map[col_obj_type] = "object_type"
    if col_resp and col_resp != "responsible":
        rename_map[col_resp] = "responsible"
    if col_status and col_status != "status":
        rename_map[col_status] = "status"
    if col_works and col_works != "works_in_progress":
        rename_map[col_works] = "works_in_progress"
    if col_issues and col_issues != "issues":
        rename_map[col_issues] = "issues"
    if col_last_update and col_last_update != "last_update":
        rename_map[col_last_update] = "last_update"
    if col_card and col_card != "card_url":
        rename_map[col_card] = "card_url"
    if col_folder and col_folder != "folder_url":
        rename_map[col_folder] = "folder_url"
    if col_address and col_address != "address":
        rename_map[col_address] = "address"

    if rename_map:
        df = df.rename(columns=rename_map)

    # гарантируем наличие базовых колонок (чтобы код не падал)
    for must in [
        "id",
        "sector",
        "district",
        "object_name",
        "object_type",
        "responsible",
        "status",
        "works_in_progress",
        "issues",
        "last_update",
        "card_url",
        "folder_url",
        "address",
    ]:
        if must not in df.columns:
            df[must] = ""

    # на всякий случай заменим NaN -> ""
    for c in df.columns:
        df[c] = df[c].astype(str).replace({"nan": "", "None": ""})

    return df


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

/* Hide Streamlit footer/menu */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* --- Hero --- */
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
@media (max-width: 900px){
  .hero-ministry{ font-size: 16px; }
  .hero-row{ align-items:center; }
}

/* =========================
   CARDS
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
  font-weight: 900;
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

.tag.status{ font-weight: 900; }

.tag.status-green{
  background: rgba(34, 197, 94, .10);
  border-color: rgba(34, 197, 94, .22);
}
.tag.status-yellow{
  background: rgba(245, 158, 11, .12);
  border-color: rgba(245, 158, 11, .25);
}
.tag.status-red{
  background: rgba(239, 68, 68, .09);
  border-color: rgba(239, 68, 68, .20);
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
  font-weight: 800;
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

/* Extra sections inside card */
.card-sep{
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px dashed rgba(15, 23, 42, .14);
}
.section-title{
  font-weight: 900;
  font-size: 13px;
  color: rgba(15, 23, 42, .80);
  margin-bottom: 8px;
}
.section-grid{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 18px;
}
.rowline{
  font-size: 13px;
  color: rgba(15, 23, 42, .82);
}
.rowline b{ color: rgba(15, 23, 42, .92); }

.note{
  margin-top: 8px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(239, 68, 68, .18);
  background: rgba(239, 68, 68, .06);
  color: rgba(15, 23, 42, .86);
  font-size: 13px;
  white-space: pre-wrap;
}

@media (max-width: 900px){
  .card-grid{ grid-template-columns: 1fr; }
  .section-grid{ grid-template-columns: 1fr; }
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
    st.error("Данные не загрузились (реестр пустой). Проверьте CSV_URL в Secrets или корректность опубликованной ссылки CSV.")
    st.stop()

df = normalize_schema_keep_all(raw)

# ВАЖНО: чтобы сейчас подтягивалась только «одна карточка», включите этот флажок.
# (показываем только те строки, где заполнено хоть что-то из «паспорта» — например agreement/state_program/contract_price)
ONLY_FILLED_PASSPORT = True

passport_cols_hint = [
    "state_program", "federal_project", "regional_program",
    "agreement", "agreement_date", "agreement_amount",
    "capacity_seats", "area_m2", "target_deadline",
    "psd_cost", "designer", "expertise", "expertise_date",
    "rns", "rns_date", "contract", "contract_date",
    "contractor", "contract_price", "end_date_plan", "end_date_fact",
    "readiness", "paid", "issues", "works_in_progress", "updated_at"
]

for c in passport_cols_hint:
    if c not in df.columns:
        df[c] = ""

if ONLY_FILLED_PASSPORT:
    def has_passport(row):
        for c in ["agreement", "agreement_amount", "contract_price", "state_program", "federal_project", "regional_program"]:
            if safe_text(row.get(c, ""), fallback="—") != "—":
                return True
        return False
    df = df[df.apply(has_passport, axis=1)].copy()

# списки для фильтров
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
        s = " ".join(
            [
                str(r.get("object_name", "")),
                str(r.get("address", "")),
                str(r.get("responsible", "")),
                str(r.get("id", "")),
            ]
        ).lower()
        return q in s
    filtered = filtered[filtered.apply(row_match, axis=1)]

st.caption(f"Показано объектов: {len(filtered)}")
st.divider()

# =============================
# CARD RENDER
# =============================
def render_card(row: pd.Series):
    title = safe_text(row.get("object_name", ""), fallback="Объект")
    sector = safe_text(row.get("sector", ""), fallback="—")
    district = safe_text(row.get("district", ""), fallback="—")
    address = safe_text(row.get("address", ""), fallback="—")
    responsible = safe_text(row.get("responsible", ""), fallback="—")
    status = safe_text(row.get("status", ""), fallback="—")

    works = safe_text(row.get("works_in_progress", ""), fallback="—")
    issues = safe_text(row.get("issues", ""), fallback="—")
    updated_at = safe_text(row.get("updated_at", ""), fallback=safe_text(row.get("last_update", ""), fallback="—"))

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

    # паспорт/финансы/сроки — из реестра
    state_program = safe_text(row.get("state_program", ""), fallback="—")
    federal_project = safe_text(row.get("federal_project", ""), fallback="—")
    regional_program = safe_text(row.get("regional_program", ""), fallback="—")

    agreement = safe_text(row.get("agreement", ""), fallback="—")
    agreement_date = fmt_date(row.get("agreement_date", ""))
    agreement_amount = fmt_money(row.get("agreement_amount", ""))

    capacity_seats = fmt_number(row.get("capacity_seats", ""))
    area_m2 = safe_text(row.get("area_m2", ""), fallback="—")
    target_deadline = fmt_date(row.get("target_deadline", ""))

    psd_cost = fmt_money(row.get("psd_cost", ""))
    designer = safe_text(row.get("designer", ""), fallback="—")
    expertise = safe_text(row.get("expertise", ""), fallback="—")
    expertise_conclusion = safe_text(row.get("expertise_conclusion", ""), fallback="—")
    expertise_date = fmt_date(row.get("expertise_date", ""))

    rns = safe_text(row.get("rns", ""), fallback="—")
    rns_date = fmt_date(row.get("rns_date", ""))
    rns_expiry = fmt_date(row.get("rns_expiry", ""))

    contract = safe_text(row.get("contract", ""), fallback="—")
    contract_date = fmt_date(row.get("contract_date", ""))
    contractor = safe_text(row.get("contractor", ""), fallback="—")
    contract_price = fmt_money(row.get("contract_price", ""))

    end_plan = fmt_date(row.get("end_date_plan", ""))
    end_fact = fmt_date(row.get("end_date_fact", ""))

    readiness = fmt_percent(row.get("readiness", ""))
    paid = fmt_money(row.get("paid", ""))

    # показываем "обновлено" как дату, если вдруг serial
    updated_at_fmt = fmt_date(updated_at) if updated_at != "—" else "—"

    # Небольшая логика: если блоки пустые — не показываем лишнее
    has_programs = any(x != "—" for x in [state_program, federal_project, regional_program])
    has_agreement = any(x != "—" for x in [agreement, agreement_date, agreement_amount])
    has_capacity = any(x != "—" for x in [capacity_seats, area_m2, target_deadline])
    has_psd = any(x != "—" for x in [psd_cost, designer, expertise, expertise_date])
    has_rns = any(x != "—" for x in [rns, rns_date, rns_expiry])
    has_contract = any(x != "—" for x in [contract, contract_date, contractor, contract_price])
    has_terms = any(x != "—" for x in [end_plan, end_fact, readiness, paid])

    # Проблемы показываем отдельно, если есть текст
    issues_html = ""
    if issues != "—":
        issues_html = f"""
<div class="card-sep">
  <div class="section-title">⚠️ Проблемные вопросы</div>
  <div class="note">{issues}</div>
</div>
"""

    # Паспорт/финансы/сроки (компактно)
    passport_lines = []
    if has_programs:
        passport_lines.append(f"""
<div class="card-sep">
  <div class="section-title">🏛️ Программы</div>
  <div class="section-grid">
    <div class="rowline"><b>ГП/СП:</b> {state_program}</div>
    <div class="rowline"><b>ФП:</b> {federal_project}</div>
    <div class="rowline"><b>РП:</b> {regional_program}</div>
  </div>
</div>
""")

    if has_agreement:
        passport_lines.append(f"""
<div class="card-sep">
  <div class="section-title">📑 Соглашение</div>
  <div class="section-grid">
    <div class="rowline"><b>№:</b> {agreement}</div>
    <div class="rowline"><b>Дата:</b> {agreement_date}</div>
    <div class="rowline"><b>Сумма:</b> {agreement_amount}</div>
  </div>
</div>
""")

    if has_capacity:
        passport_lines.append(f"""
<div class="card-sep">
  <div class="section-title">🏗️ Параметры</div>
  <div class="section-grid">
    <div class="rowline"><b>Мощность:</b> {capacity_seats}</div>
    <div class="rowline"><b>Площадь:</b> {area_m2}</div>
    <div class="rowline"><b>Целевой срок:</b> {target_deadline}</div>
  </div>
</div>
""")

    if has_psd:
        passport_lines.append(f"""
<div class="card-sep">
  <div class="section-title">🧾 ПСД / Экспертиза</div>
  <div class="section-grid">
    <div class="rowline"><b>Стоимость ПСД:</b> {psd_cost}</div>
    <div class="rowline"><b>Проектировщик:</b> {designer}</div>
    <div class="rowline"><b>Экспертиза:</b> {expertise}</div>
    <div class="rowline"><b>Дата экспертизы:</b> {expertise_date}</div>
  </div>
  <div class="rowline" style="margin-top:8px;"><b>Заключение:</b> {expertise_conclusion}</div>
</div>
""")

    if has_rns:
        passport_lines.append(f"""
<div class="card-sep">
  <div class="section-title">🏛️ РНС</div>
  <div class="section-grid">
    <div class="rowline"><b>№ РНС:</b> {rns}</div>
    <div class="rowline"><b>Дата:</b> {rns_date}</div>
    <div class="rowline"><b>Срок действия:</b> {rns_expiry}</div>
  </div>
</div>
""")

    if has_contract:
        passport_lines.append(f"""
<div class="card-sep">
  <div class="section-title">💼 Контракт</div>
  <div class="section-grid">
    <div class="rowline"><b>№:</b> {contract}</div>
    <div class="rowline"><b>Дата:</b> {contract_date}</div>
    <div class="rowline"><b>Подрядчик:</b> {contractor}</div>
    <div class="rowline"><b>Цена:</b> {contract_price}</div>
  </div>
</div>
""")

    if has_terms:
        passport_lines.append(f"""
<div class="card-sep">
  <div class="section-title">📅 Сроки / Финансы</div>
  <div class="section-grid">
    <div class="rowline"><b>Окончание (план):</b> {end_plan}</div>
    <div class="rowline"><b>Окончание (факт):</b> {end_fact}</div>
    <div class="rowline"><b>Готовность:</b> {readiness}</div>
    <div class="rowline"><b>Оплачено:</b> {paid}</div>
  </div>
</div>
""")

    passport_html = "\n".join(passport_lines)

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
    <span class="tag {status_class(status)} status">📌 <b>Статус:</b> {status}</span>
    <span class="tag">🛠️ <b>Работы:</b> {works}</span>
    <span class="tag">🕒 <b>Обновлено:</b> {updated_at_fmt}</span>
  </div>

  <div class="card-actions">
    {btn_card}
    {btn_folder}
  </div>

  {issues_html}
  {passport_html}
</div>
""",
        unsafe_allow_html=True,
    )


# =============================
# OUTPUT
# =============================
if filtered.empty:
    st.info("По текущим фильтрам ничего не найдено.")
else:
    for _, r in filtered.iterrows():
        render_card(r)
