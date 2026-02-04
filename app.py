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
    """В списке отраслей переместить 'Прочие' в самый низ."""
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


def excel_serial_to_date_str(x) -> str | None:
    """
    Google Sheets/Excel иногда отдают дату как число (serial):
    45902 -> 02.09.2025
    Возвращает строку dd.mm.yyyy или None если не похоже на дату.
    """
    if x is None:
        return None
    try:
        if pd.isna(x):
            return None
    except Exception:
        pass

    # уже дата/таймстамп
    if isinstance(x, (datetime, pd.Timestamp)):
        return x.strftime("%d.%m.%Y")

    # строка-число / число / float
    try:
        s = str(x).strip().replace(",", ".")
        if s == "":
            return None
        v = float(s)
        # адекватный диапазон serial дат (примерно 1990..2100)
        if 30000 <= v <= 80000:
            base = datetime(1899, 12, 30)  # Excel/Sheets base
            d = base + timedelta(days=int(round(v)))
            return d.strftime("%d.%m.%Y")
    except Exception:
        return None

    return None


def fmt_date(x) -> str:
    """Красиво показать дату: если serial — конвертируем; если пусто — '—'."""
    if x is None:
        return "—"
    try:
        if pd.isna(x):
            return "—"
    except Exception:
        pass

    s = str(x).strip()
    if not s:
        return "—"

    conv = excel_serial_to_date_str(x)
    return conv if conv else s


def fmt_money(x) -> str:
    """Деньги: 882623791.57 -> 882 623 792 ₽"""
    if x is None:
        return "—"
    try:
        if pd.isna(x):
            return "—"
    except Exception:
        pass
    s = str(x).strip()
    if not s:
        return "—"
    try:
        v = float(str(x).replace(" ", "").replace("\u00A0", "").replace(",", "."))
        return f"{v:,.0f}".replace(",", " ") + " ₽"
    except Exception:
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

    df = pd.DataFrame()

    if csv_url:
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
            "РЕЕСТР_объектов_Курская_область_2025-2028 (17).xlsx",
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
    Оставляем твою логику (единые поля для фильтра/поиска),
    но ДОБАВЛЯЕМ все расширенные поля (для карточки).
    """
    if df.empty:
        return df

    # базовые поля (как у тебя)
    col_id = pick_col(df, ["id", "ID"])
    col_sector = pick_col(df, ["sector", "отрасль"])
    col_district = pick_col(df, ["district", "район"])
    col_name = pick_col(df, ["object_name", "наименование_объекта", "наименование объекта"])
    col_object_type = pick_col(df, ["object_type", "объект", "тип", "тип объекта"])
    col_resp = pick_col(df, ["responsible", "ответственный"])
    col_status = pick_col(df, ["status", "статус"])
    col_works = pick_col(df, ["works_in_progress", "работы_ведутся", "работы ведутся"])
    col_issues = pick_col(df, ["issues", "проблемные_вопросы", "проблемные вопросы"])
    col_last_update = pick_col(df, ["last_update", "дата_последнего_обновления", "дата последнего обновления"])

    col_card = pick_col(df, ["card_url", "ссылка_на_карточку_(google)", "ссылка на карточку"])
    col_folder = pick_col(df, ["folder_url", "ссылка_на_папку_(drive)", "ссылка на папку"])
    col_card_text = pick_col(df, ["card_url_text"])
    col_folder_text = pick_col(df, ["folder_url_text"])
    col_address = pick_col(df, ["address", "адрес"])

    # расширенные поля (точно по твоей зафиксированной структуре)
    col_state_program = pick_col(df, ["state_program"])
    col_federal_project = pick_col(df, ["federal_project"])
    col_regional_program = pick_col(df, ["regional_program"])

    col_agreement = pick_col(df, ["agreement"])
    col_agreement_date = pick_col(df, ["agreement_date"])
    col_agreement_amount = pick_col(df, ["agreement_amount"])

    col_capacity = pick_col(df, ["capacity_seats"])
    col_area = pick_col(df, ["area_m2"])
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

    col_updated_at = pick_col(df, ["updated_at"])

    out = pd.DataFrame()

    # базовая “витрина” (как у тебя было)
    out["id"] = df[col_id] if col_id else ""
    out["sector"] = df[col_sector] if col_sector else ""
    out["district"] = df[col_district] if col_district else ""
    out["name"] = df[col_name] if col_name else ""
    out["object_type"] = df[col_object_type] if col_object_type else ""
    out["address"] = df[col_address] if col_address else ""
    out["responsible"] = df[col_resp] if col_resp else ""
    out["status"] = df[col_status] if col_status else ""
    out["work_flag"] = df[col_works] if col_works else ""
    out["issues"] = df[col_issues] if col_issues else ""
    out["last_update"] = df[col_last_update] if col_last_update else ""

    out["card_url"] = df[col_card] if col_card else ""
    out["folder_url"] = df[col_folder] if col_folder else ""
    out["card_url_text"] = df[col_card_text] if col_card_text else ""
    out["folder_url_text"] = df[col_folder_text] if col_folder_text else ""

    # расширение (для карточки)
    out["state_program"] = df[col_state_program] if col_state_program else ""
    out["federal_project"] = df[col_federal_project] if col_federal_project else ""
    out["regional_program"] = df[col_regional_program] if col_regional_program else ""

    out["agreement"] = df[col_agreement] if col_agreement else ""
    out["agreement_date"] = df[col_agreement_date] if col_agreement_date else ""
    out["agreement_amount"] = df[col_agreement_amount] if col_agreement_amount else ""

    out["capacity_seats"] = df[col_capacity] if col_capacity else ""
    out["area_m2"] = df[col_area] if col_area else ""
    out["target_deadline"] = df[col_target_deadline] if col_target_deadline else ""

    out["design"] = df[col_design] if col_design else ""
    out["psd_cost"] = df[col_psd_cost] if col_psd_cost else ""
    out["designer"] = df[col_designer] if col_designer else ""

    out["expertise"] = df[col_expertise] if col_expertise else ""
    out["expertise_conclusion"] = df[col_expertise_conclusion] if col_expertise_conclusion else ""
    out["expertise_date"] = df[col_expertise_date] if col_expertise_date else ""

    out["rns"] = df[col_rns] if col_rns else ""
    out["rns_date"] = df[col_rns_date] if col_rns_date else ""
    out["rns_expiry"] = df[col_rns_expiry] if col_rns_expiry else ""

    out["contract"] = df[col_contract] if col_contract else ""
    out["contract_date"] = df[col_contract_date] if col_contract_date else ""
    out["contractor"] = df[col_contractor] if col_contractor else ""
    out["contract_price"] = df[col_contract_price] if col_contract_price else ""

    out["end_date_plan"] = df[col_end_plan] if col_end_plan else ""
    out["end_date_fact"] = df[col_end_fact] if col_end_fact else ""

    out["readiness"] = df[col_readiness] if col_readiness else ""
    out["paid"] = df[col_paid] if col_paid else ""

    out["updated_at"] = df[col_updated_at] if col_updated_at else ""

    # чистим nan/None в строки
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

/* Hide Streamlit footer/menu */
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

.tag.status{ font-weight: 800; }

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
  color: rgba(15, 23, 42, .78);
}

/* Mobile */
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
    st.error("Данные не загрузились (реестр пустой). Проверьте CSV_URL в Secrets или наличие .xlsx в репозитории.")
    st.stop()

df = normalize_schema(raw)

# unique lists
sectors = sorted([x for x in df["sector"].unique().tolist() if str(x).strip()])
districts = sorted([x for x in df["district"].unique().tolist() if str(x).strip()])
statuses = sorted([x for x in df["status"].unique().tolist() if str(x).strip()])

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
# CARD RENDER (расширили, но НЕ ломаем)
# =============================
def render_card(row: pd.Series):
    title = safe_text(row.get("name", ""), fallback="Объект")
    sector = safe_text(row.get("sector", ""), fallback="—")
    district = safe_text(row.get("district", ""), fallback="—")
    address = safe_text(row.get("address", ""), fallback="—")
    responsible = safe_text(row.get("responsible", ""), fallback="—")

    status = safe_text(row.get("status", ""), fallback="—")
    work_flag = safe_text(row.get("work_flag", ""), fallback="—")
    issues = safe_text(row.get("issues", ""), fallback="—")

    card_url = safe_text(row.get("card_url", ""), fallback="")
    folder_url = safe_text(row.get("folder_url", ""), fallback="")

    # расширенные (с форматированием)
    state_program = safe_text(row.get("state_program", ""))
    federal_project = safe_text(row.get("federal_project", ""))
    regional_program = safe_text(row.get("regional_program", ""))

    agreement = safe_text(row.get("agreement", ""))
    agreement_date = fmt_date(row.get("agreement_date", ""))
    agreement_amount = fmt_money(row.get("agreement_amount", ""))

    capacity = safe_text(row.get("capacity_seats", ""))
    area = safe_text(row.get("area_m2", ""))
    target_deadline = fmt_date(row.get("target_deadline", ""))

    design = safe_text(row.get("design", ""))
    psd_cost = fmt_money(row.get("psd_cost", ""))
    designer = safe_text(row.get("designer", ""))

    expertise = safe_text(row.get("expertise", ""))
    expertise_conclusion = safe_text(row.get("expertise_conclusion", ""))
    expertise_date = fmt_date(row.get("expertise_date", ""))

    rns = safe_text(row.get("rns", ""))
    rns_date = fmt_date(row.get("rns_date", ""))
    rns_expiry = fmt_date(row.get("rns_expiry", ""))

    contract = safe_text(row.get("contract", ""))
    contract_date = fmt_date(row.get("contract_date", ""))
    contractor = safe_text(row.get("contractor", ""))
    contract_price = fmt_money(row.get("contract_price", ""))

    end_plan = fmt_date(row.get("end_date_plan", ""))
    end_fact = fmt_date(row.get("end_date_fact", ""))

    readiness = safe_text(row.get("readiness", ""))
    paid = fmt_money(row.get("paid", ""))

    updated_at = fmt_date(row.get("updated_at", ""))

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

    # показываем блоки только если есть смысл (чтобы было лаконично)
    def has_any(*vals) -> bool:
        return any(v not in ("", "—", None) for v in vals)

    program_block = ""
    if has_any(state_program, federal_project, regional_program):
        program_block = f"""
        <div class="card-extra">
          <b>Программы:</b><br/>
          {("• Госпрограмма: " + state_program + "<br/>") if state_program != "—" else ""}
          {("• Федпроект: " + federal_project + "<br/>") if federal_project != "—" else ""}
          {("• Регпрограмма: " + regional_program) if regional_program != "—" else ""}
        </div>
        """

    docs_block = ""
    if has_any(agreement, agreement_date, agreement_amount, rns, rns_date, rns_expiry, expertise, expertise_date):
        docs_block = f"""
        <div class="card-extra">
          <b>Документы / этапы:</b><br/>
          {("• Соглашение: " + agreement + "<br/>") if agreement != "—" else ""}
          {("• Дата соглашения: " + agreement_date + "<br/>") if agreement_date != "—" else ""}
          {("• Сумма соглашения: " + agreement_amount + "<br/>") if agreement_amount != "—" else ""}

          {("• Экспертиза: " + expertise + "<br/>") if expertise != "—" else ""}
          {("• Заключение: " + expertise_conclusion + "<br/>") if expertise_conclusion != "—" else ""}
          {("• Дата экспертизы: " + expertise_date + "<br/>") if expertise_date != "—" else ""}

          {("• РНС: " + rns + "<br/>") if rns != "—" else ""}
          {("• Дата РНС: " + rns_date + "<br/>") if rns_date != "—" else ""}
          {("• РНС до: " + rns_expiry) if rns_expiry != "—" else ""}
        </div>
        """

    contract_block = ""
    if has_any(contract, contract_date, contractor, contract_price, end_plan, end_fact, paid, readiness):
        contract_block = f"""
        <div class="card-extra">
          <b>Контракт / сроки / финансы:</b><br/>
          {("• Контракт: " + contract + "<br/>") if contract != "—" else ""}
          {("• Дата контракта: " + contract_date + "<br/>") if contract_date != "—" else ""}
          {("• Подрядчик: " + contractor + "<br/>") if contractor != "—" else ""}
          {("• Цена контракта: " + contract_price + "<br/>") if contract_price != "—" else ""}
          {("• Срок окончания (план): " + end_plan + "<br/>") if end_plan != "—" else ""}
          {("• Срок окончания (факт): " + end_fact + "<br/>") if end_fact != "—" else ""}
          {("• Готовность: " + readiness + "<br/>") if readiness != "—" else ""}
          {("• Оплачено: " + paid) if paid != "—" else ""}
        </div>
        """

    design_block = ""
    if has_any(design, psd_cost, designer, capacity, area, target_deadline):
        design_block = f"""
        <div class="card-extra">
          <b>Паспорт:</b><br/>
          {("• Мощность: " + capacity + "<br/>") if capacity != "—" else ""}
          {("• Площадь: " + area + "<br/>") if area != "—" else ""}
          {("• Срок достижения результата: " + target_deadline + "<br/>") if target_deadline != "—" else ""}
          {("• Проектирование: " + design + "<br/>") if design != "—" else ""}
          {("• Стоимость ПСД: " + psd_cost + "<br/>") if psd_cost != "—" else ""}
          {("• Проектировщик: " + designer) if designer != "—" else ""}
        </div>
        """

    issues_block = ""
    if issues not in ("—", "", None):
        issues_block = f"""
        <div class="card-extra">
          <b>Проблемные вопросы:</b><br/>{issues}
        </div>
        """

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
    <span class="tag {status_class(status)}">📌 <b>Статус:</b> {status}</span>
    <span class="tag">🛠️ <b>Работы:</b> {work_flag}</span>
    <span class="tag">🗓️ <b>Обновлено:</b> {updated_at}</span>
  </div>

  <div class="card-actions">
    {btn_card}
    {btn_folder}
  </div>

  {program_block}
  {design_block}
  {docs_block}
  {contract_block}
  {issues_block}
</div>
""",
        unsafe_allow_html=True,  # КРИТИЧНО: иначе будут видны теги как текст
    )


# =============================
# OUTPUT: ONE COLUMN
# =============================
for _, r in filtered.iterrows():
    render_card(r)
