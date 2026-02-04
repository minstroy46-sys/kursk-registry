import base64
import re
from pathlib import Path
from datetime import datetime, date, timedelta

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


# ---------- dates ----------
def _to_excel_serial_date(n: float) -> date | None:
    """
    Google Sheets/Excel serial date (usually from 1899-12-30).
    We use 1899-12-30 to match Sheets behavior.
    """
    try:
        base = date(1899, 12, 30)
        return base + timedelta(days=int(n))
    except Exception:
        return None


def parse_any_date(v) -> date | None:
    """
    Accepts:
    - dd.mm.yyyy
    - yyyy-mm-dd
    - pandas Timestamp
    - Excel/Sheets serial number (e.g., 45652)
    """
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except Exception:
        pass

    # already date/datetime
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()

    s = str(v).strip()
    if not s:
        return None

    # numeric serial in string
    if re.fullmatch(r"\d+(\.\d+)?", s):
        try:
            n = float(s)
            # heuristic: serial dates are usually > 30000 (1982+) and < 70000 (2091)
            if 30000 <= n <= 70000:
                return _to_excel_serial_date(n)
        except Exception:
            pass

    # dd.mm.yyyy
    for fmt in ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            continue

    # pandas fallback
    try:
        dt = pd.to_datetime(s, errors="coerce", dayfirst=True)
        if pd.isna(dt):
            return None
        return dt.date()
    except Exception:
        return None


def fmt_date_ru(d: date | None, fallback="—") -> str:
    if not d:
        return fallback
    return d.strftime("%d.%m.%Y")


def days_since(d: date | None) -> int | None:
    if not d:
        return None
    return (date.today() - d).days


def update_traffic_class(last_update_value) -> tuple[str, str]:
    """
    Returns (css_class, label_text)
    Rule:
      0..7 days -> green
      8..14 -> yellow
      15+ -> red
      missing -> gray
    """
    d = parse_any_date(last_update_value)
    if not d:
        return "tag tag-gray", "—"
    age = days_since(d)
    if age is None:
        return "tag tag-gray", fmt_date_ru(d)

    if age <= 7:
        return "tag tag-green", f"{fmt_date_ru(d)}"
    if age <= 14:
        return "tag tag-yellow", f"{fmt_date_ru(d)}"
    return "tag tag-red", f"{fmt_date_ru(d)}"


def works_traffic_class(v) -> tuple[str, str]:
    """
    If works not going -> red
    If going -> green
    Else gray
    """
    s = norm_col(v)
    if not s or s in ("—", "-", "нет данных"):
        return "tag tag-gray", "—"

    # negatives first
    if any(k in s for k in ["нет", "не вед", "не идут", "останов", "приостанов"]):
        return "tag tag-red", safe_text(v)

    if any(k in s for k in ["да", "ведут", "ведется", "идут", "выполня", "в работе"]):
        return "tag tag-green", safe_text(v)

    return "tag tag-gray", safe_text(v)


def status_class(status_text: str) -> str:
    s = norm_col(status_text)
    if "останов" in s or "приостанов" in s:
        return "tag tag-status tag-red"
    if "проектир" in s:
        return "tag tag-status tag-yellow"
    if "строитель" in s:
        return "tag tag-status tag-green"
    return "tag tag-status tag-gray"


# =============================
# DATA LOADING
# =============================
@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
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

    if df is None or df.empty:
        return pd.DataFrame()

    df.columns = [str(c).strip() for c in df.columns]
    return df


def normalize_schema(df: pd.DataFrame) -> pd.DataFrame:
    """
    Поддерживает ваш фиксированный реестр.
    Нужные колонки:
    ID, sector, district, object_name, object_type, responsible, status,
    works_in_progress, issues, last_update, card_url, folder_url,
    + паспортные поля (state_program...updated_at)
    """
    if df.empty:
        return df

    # базовые
    col_id = pick_col(df, ["id", "ID"])
    col_sector = pick_col(df, ["sector", "отрасль"])
    col_district = pick_col(df, ["district", "район"])
    col_name = pick_col(df, ["object_name", "name", "наименование_объекта", "наименование объекта"])
    col_object_type = pick_col(df, ["object_type", "тип", "тип объекта"])
    col_resp = pick_col(df, ["responsible", "ответственный"])
    col_status = pick_col(df, ["status", "статус"])
    col_works = pick_col(df, ["works_in_progress", "works", "work_flag", "работы"])
    col_issues = pick_col(df, ["issues", "проблемы", "проблемные вопросы"])
    col_last_update = pick_col(df, ["last_update", "updated_at", "обновлено", "дата обновления"])
    col_card = pick_col(df, ["card_url", "ссылка_на_карточку", "ссылка на карточку"])
    col_folder = pick_col(df, ["folder_url", "ссылка_на_папку", "ссылка на папку"])
    col_address = pick_col(df, ["address", "адрес"])

    # паспортные (как в карточке key/value)
    passport_cols = {
        "state_program": pick_col(df, ["state_program"]),
        "federal_project": pick_col(df, ["federal_project"]),
        "regional_program": pick_col(df, ["regional_program"]),
        "agreement": pick_col(df, ["agreement"]),
        "agreement_date": pick_col(df, ["agreement_date"]),
        "agreement_amount": pick_col(df, ["agreement_amount"]),
        "capacity_seats": pick_col(df, ["capacity_seats"]),
        "area_m2": pick_col(df, ["area_m2"]),
        "target_deadline": pick_col(df, ["target_deadline"]),
        "design": pick_col(df, ["design"]),
        "psd_cost": pick_col(df, ["psd_cost"]),
        "designer": pick_col(df, ["designer"]),
        "expertise": pick_col(df, ["expertise"]),
        "expertise_conclusion": pick_col(df, ["expertise_conclusion"]),
        "expertise_date": pick_col(df, ["expertise_date"]),
        "rns": pick_col(df, ["rns"]),
        "rns_date": pick_col(df, ["rns_date"]),
        "rns_expiry": pick_col(df, ["rns_expiry"]),
        "contract": pick_col(df, ["contract"]),
        "contract_date": pick_col(df, ["contract_date"]),
        "contractor": pick_col(df, ["contractor"]),
        "contract_price": pick_col(df, ["contract_price"]),
        "end_date_plan": pick_col(df, ["end_date_plan"]),
        "end_date_fact": pick_col(df, ["end_date_fact"]),
        "readiness": pick_col(df, ["readiness"]),
        "paid": pick_col(df, ["paid"]),
        "updated_at": pick_col(df, ["updated_at"]),  # если отдельно храните
    }

    out = pd.DataFrame()
    out["id"] = df[col_id] if col_id else ""
    out["sector"] = df[col_sector] if col_sector else ""
    out["district"] = df[col_district] if col_district else ""
    out["name"] = df[col_name] if col_name else ""
    out["object_type"] = df[col_object_type] if col_object_type else ""
    out["address"] = df[col_address] if col_address else ""
    out["responsible"] = df[col_resp] if col_resp else ""
    out["status"] = df[col_status] if col_status else ""
    out["works_in_progress"] = df[col_works] if col_works else ""
    out["issues"] = df[col_issues] if col_issues else ""
    out["last_update"] = df[col_last_update] if col_last_update else ""
    out["card_url"] = df[col_card] if col_card else ""
    out["folder_url"] = df[col_folder] if col_folder else ""

    # доп поля
    for k, c in passport_cols.items():
        out[k] = df[c] if c else ""

    # чистим nan
    for c in out.columns:
        out[c] = out[c].astype(str).replace({"nan": "", "None": ""})

    return out


# =============================
# STYLES (hero оставляем, улучшаем карточку + сворачивание)
# =============================
crest_b64 = read_local_crest_b64()

st.markdown(
    """
<style>
/* --- Page base --- */
.block-container { padding-top: 24px !important; max-width: 1200px; }
@media (max-width: 1200px){ .block-container { max-width: 96vw; } }
div[data-testid="stHorizontalBlock"]{ gap: 14px; }

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* --- Hero (unchanged) --- */
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
  padding: 16px 16px 12px 16px;
  box-shadow: 0 10px 22px rgba(0,0,0,.06);
  margin-bottom: 14px;
}

.card-title{
  font-size: 18px;
  line-height: 1.2;
  font-weight: 900;
  margin: 0 0 10px 0;
  color: #0f172a;
}

.card-grid{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 18px;
  margin-top: 4px;
}

.card-item{
  font-size: 14px;
  color: rgba(15, 23, 42, .92);
}
.card-item b{ color: rgba(15, 23, 42, .95); }

.card-tags{
  display:flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 10px;
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
  color: rgba(15, 23, 42, .92);
  font-weight: 750;
}

/* status tag stronger */
.tag-status{ font-weight: 900; }

/* traffic colors */
.tag-green{ background: rgba(34,197,94,.10); border-color: rgba(34,197,94,.22); }
.tag-yellow{ background: rgba(245,158,11,.12); border-color: rgba(245,158,11,.25); }
.tag-red{ background: rgba(239,68,68,.09); border-color: rgba(239,68,68,.20); }
.tag-gray{ background: rgba(15,23,42,.03); border-color: rgba(15,23,42,.10); opacity: .95; }

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
.a-btn:hover{ transform: translateY(-1px); box-shadow: 0 10px 18px rgba(0,0,0,.08); }
.a-btn.disabled{ opacity: .45; pointer-events: none; }

.hr-soft{
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dashed rgba(15, 23, 42, .14);
}

/* Details blocks inside expander */
.detail-block{
  margin-top: 10px;
  padding: 12px 12px;
  border-radius: 12px;
  border: 1px solid rgba(15, 23, 42, .10);
  background: rgba(15,23,42,.02);
}
.detail-title{
  font-weight: 900;
  margin-bottom: 8px;
}
.detail-grid{
  display:grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 18px;
}
.detail-row{ font-size: 13px; color: rgba(15,23,42,.92); }
.detail-row b{ color: rgba(15,23,42,.95); }

.issue-box{
  margin-top: 10px;
  padding: 12px;
  border-radius: 12px;
  border: 1px solid rgba(239,68,68,.20);
  background: rgba(239,68,68,.06);
  font-size: 13px;
}

@media (max-width: 900px){
  .card-grid{ grid-template-columns: 1fr; }
  .detail-grid{ grid-template-columns: 1fr; }
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
        <div class="hero-sub">Единый список объектов 2025–2028 с быстрыми фильтрами и переходом в карточку/папку.</div>
      </div>
    </div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)


# =============================
# AUTH
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
    st.error("Данные не загрузились (реестр пустой). Проверьте CSV_URL в Secrets (публичный CSV Google Sheets).")
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
# CARD RENDER
# =============================
def _money(v) -> str:
    s = safe_text(v, fallback="—")
    if s == "—":
        return s
    # пытаемся привести к числу
    try:
        x = float(str(s).replace(" ", "").replace(",", "."))
        return f"{x:,.2f}".replace(",", " ").replace(".00", "") + " ₽"
    except Exception:
        return s


def _num(v) -> str:
    s = safe_text(v, fallback="—")
    if s == "—":
        return s
    return s


def render_details(row: pd.Series):
    # Программы
    stp = safe_text(row.get("state_program", ""))
    fp = safe_text(row.get("federal_project", ""))
    rp = safe_text(row.get("regional_program", ""))

    # Соглашение
    agreement = safe_text(row.get("agreement", ""))
    agreement_date = fmt_date_ru(parse_any_date(row.get("agreement_date", "")))
    agreement_amount = _money(row.get("agreement_amount", ""))

    # Параметры
    capacity = safe_text(row.get("capacity_seats", ""))
    area_m2 = safe_text(row.get("area_m2", ""))
    target_deadline = fmt_date_ru(parse_any_date(row.get("target_deadline", "")))

    # ПСД/экспертиза
    psd_cost = _money(row.get("psd_cost", ""))
    designer = safe_text(row.get("designer", ""))
    expertise = safe_text(row.get("expertise", ""))
    expertise_concl = safe_text(row.get("expertise_conclusion", ""))
    expertise_date = fmt_date_ru(parse_any_date(row.get("expertise_date", "")))

    # РНС
    rns = safe_text(row.get("rns", ""))
    rns_date = fmt_date_ru(parse_any_date(row.get("rns_date", "")))
    rns_expiry = fmt_date_ru(parse_any_date(row.get("rns_expiry", "")))

    # Контракт
    contract = safe_text(row.get("contract", ""))
    contract_date = fmt_date_ru(parse_any_date(row.get("contract_date", "")))
    contractor = safe_text(row.get("contractor", ""))
    contract_price = _money(row.get("contract_price", ""))

    # Сроки/финансы
    end_plan = fmt_date_ru(parse_any_date(row.get("end_date_plan", "")))
    end_fact = fmt_date_ru(parse_any_date(row.get("end_date_fact", "")))
    readiness = safe_text(row.get("readiness", ""))
    paid = _money(row.get("paid", ""))

    def block(title, rows: list[tuple[str, str]]):
        rows_html = "\n".join([f'<div class="detail-row"><b>{k}</b> {v}</div>' for k, v in rows])
        st.markdown(
            f"""
<div class="detail-block">
  <div class="detail-title">{title}</div>
  <div class="detail-grid">
    {rows_html}
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

    # показываем только если есть хоть что-то
    block(
        "🏛️ Программы",
        [
            ("ГП/СП:", stp),
            ("ФП:", fp),
            ("РП:", rp),
        ],
    )

    block(
        "📑 Соглашение",
        [
            ("№:", agreement),
            ("Дата:", agreement_date),
            ("Сумма:", agreement_amount),
        ],
    )

    block(
        "📌 Параметры",
        [
            ("Мощность:", capacity),
            ("Площадь:", area_m2),
            ("Целевой срок:", target_deadline),
        ],
    )

    block(
        "🧾 ПСД / Экспертиза",
        [
            ("Стоимость ПСД:", psd_cost),
            ("Проектировщик:", designer),
            ("Экспертиза:", expertise),
            ("Дата экспертизы:", expertise_date),
            ("Заключение:", expertise_concl),
        ],
    )

    block(
        "🏗️ РНС",
        [
            ("№ РНС:", rns),
            ("Дата:", rns_date),
            ("Срок действия:", rns_expiry),
        ],
    )

    block(
        "📦 Контракт",
        [
            ("№:", contract),
            ("Дата:", contract_date),
            ("Подрядчик:", contractor),
            ("Цена:", contract_price),
        ],
    )

    block(
        "⏱️ Сроки / Финансы",
        [
            ("Окончание (план):", end_plan),
            ("Окончание (факт):", end_fact),
            ("Готовность:", _num(readiness)),
            ("Оплачено:", paid),
        ],
    )


def render_card(row: pd.Series):
    title = safe_text(row.get("name", ""), fallback="Объект")
    sector = safe_text(row.get("sector", ""), fallback="—")
    district = safe_text(row.get("district", ""), fallback="—")
    address = safe_text(row.get("address", ""), fallback="—")
    responsible = safe_text(row.get("responsible", ""), fallback="—")

    status = safe_text(row.get("status", ""), fallback="—")
    works = safe_text(row.get("works_in_progress", ""), fallback="—")

    issues = safe_text(row.get("issues", ""), fallback="—")

    card_url = safe_text(row.get("card_url", ""), fallback="")
    folder_url = safe_text(row.get("folder_url", ""), fallback="")

    # traffic tags
    upd_cls, upd_label = update_traffic_class(row.get("last_update", ""))
    works_cls, works_label = works_traffic_class(works)
    status_cls = status_class(status)

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
    <span class="{status_cls}">📌 Статус: {status}</span>
    <span class="{works_cls}">🛠️ Работы: {works_label}</span>
    <span class="{upd_cls}">🕒 Обновлено: {upd_label}</span>
  </div>

  <div class="card-actions">
    {btn_card}
    {btn_folder}
  </div>

  <div class="hr-soft"></div>
</div>
""",
        unsafe_allow_html=True,
    )

    # ВАЖНО: детали сворачиваем — чтобы список не был “простынёй”
    # По умолчанию закрыто; открывают только нужный объект.
    with st.expander("Показать паспорт/финансы/сроки", expanded=False):
        # проблемы — отдельным блоком сверху (если есть)
        if issues and issues != "—" and issues.strip() != "":
            st.markdown(
                f"""
<div class="issue-box">
  <b>⚠️ Проблемные вопросы</b><br/>
  {issues}
</div>
""",
                unsafe_allow_html=True,
            )

        render_details(row)


# =============================
# OUTPUT
# =============================
for _, r in filtered.iterrows():
    render_card(r)
