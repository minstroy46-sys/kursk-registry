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


# =============================
# DATE PARSING (Google Sheets serial / strings)
# =============================
def _to_excel_serial_date(n: float) -> date | None:
    try:
        base = date(1899, 12, 30)  # Google Sheets serial base
        return base + timedelta(days=int(n))
    except Exception:
        return None


def parse_any_date(v) -> date | None:
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except Exception:
        pass

    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()

    s = str(v).strip()
    if not s:
        return None

    # numeric serial?
    if re.fullmatch(r"\d+(\.\d+)?", s):
        try:
            n = float(s)
            if 30000 <= n <= 70000:
                return _to_excel_serial_date(n)
        except Exception:
            pass

    for fmt in ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            continue

    try:
        dt = pd.to_datetime(s, errors="coerce", dayfirst=True)
        if pd.isna(dt):
            return None
        return dt.date()
    except Exception:
        return None


def fmt_date_ru(d: date | None, fallback="—") -> str:
    return d.strftime("%d.%m.%Y") if d else fallback


def days_since(d: date | None) -> int | None:
    if not d:
        return None
    return (date.today() - d).days


def update_traffic_class(last_update_value) -> tuple[str, str]:
    d = parse_any_date(last_update_value)
    if not d:
        return "tag tag-gray", "—"
    age = days_since(d)
    if age is None:
        return "tag tag-gray", fmt_date_ru(d)

    if age <= 7:
        return "tag tag-green", fmt_date_ru(d)
    if age <= 14:
        return "tag tag-yellow", fmt_date_ru(d)
    return "tag tag-red", fmt_date_ru(d)


def works_traffic_class(v) -> tuple[str, str]:
    s = norm_col(v)
    if not s or s in ("—", "-", "нет данных"):
        return "tag tag-gray", "—"

    if any(k in s for k in ["нет", "не вед", "не идут", "останов", "приостанов"]):
        return "tag tag-red", safe_text(v)

    if any(k in s for k in ["да", "ведут", "ведется", "идут", "выполня", "в работе"]):
        return "tag tag-green", safe_text(v)

    return "tag tag-gray", safe_text(v)


def status_tone(status_text: str) -> str:
    s = norm_col(status_text)
    if "останов" in s or "приостанов" in s:
        return "red"
    if "проектир" in s:
        return "yellow"
    if "строитель" in s:
        return "green"
    return "gray"


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

    if not csv_url:
        return pd.DataFrame()

    # Try CSV
    try:
        df = pd.read_csv(csv_url)
    except Exception:
        try:
            df = pd.read_csv(csv_url, sep=";")
        except Exception:
            return pd.DataFrame()

    df.columns = [str(c).strip() for c in df.columns]
    return df


def normalize_schema(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    col_id = pick_col(df, ["id"])
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

    # паспортные поля (как в твоей структуре)
    passport_cols = [
        "state_program", "federal_project", "regional_program",
        "agreement", "agreement_date", "agreement_amount",
        "capacity_seats", "area_m2", "target_deadline",
        "design", "psd_cost", "designer",
        "expertise", "expertise_conclusion", "expertise_date",
        "rns", "rns_date", "rns_expiry",
        "contract", "contract_date", "contractor", "contract_price",
        "end_date_plan", "end_date_fact",
        "readiness", "paid",
        "updated_at",
    ]

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

    for k in passport_cols:
        c = pick_col(df, [k])
        out[k] = df[c] if c else ""

    for c in out.columns:
        out[c] = out[c].astype(str).replace({"nan": "", "None": ""})

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

/* --- Card --- */
.card{
  background: linear-gradient(180deg, rgba(15,23,42,.015), rgba(255,255,255,1) 36%);
  border: 1px solid rgba(15, 23, 42, .10);
  border-radius: 16px;
  padding: 0;
  box-shadow: 0 10px 22px rgba(0,0,0,.06);
  margin-bottom: 14px;
  overflow: hidden;
}

.card-accent{
  height: 100%;
  width: 6px;
  position: absolute;
  left: 0; top: 0; bottom: 0;
  border-radius: 16px 0 0 16px;
  opacity: .9;
}

.card-inner{
  position: relative;
  padding: 14px 16px 12px 16px;
}

.card-title{
  font-size: 18px;
  line-height: 1.2;
  font-weight: 950;
  margin: 0;
  color: #0f172a;
}

.card-subchips{
  margin-top: 8px;
  display:flex;
  gap: 8px;
  flex-wrap: wrap;
}

.chip{
  display:inline-flex;
  align-items:center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(15,23,42,.10);
  background: rgba(15,23,42,.03);
  font-size: 12.5px;
  color: rgba(15,23,42,.92);
  font-weight: 850;
}
.chip-muted{ background: rgba(15,23,42,.02); opacity: .95; }

.card-grid{
  display:grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 18px;
  margin-top: 10px;
}
.card-item{ font-size: 14px; color: rgba(15,23,42,.92); }
.card-item b{ color: rgba(15,23,42,.95); }

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
  color: rgba(15, 23, 42, .92);
  font-weight: 900;
}
.tag-status{ font-weight: 950; }

.tag-green{ background: rgba(34,197,94,.10); border-color: rgba(34,197,94,.22); }
.tag-yellow{ background: rgba(245,158,11,.12); border-color: rgba(245,158,11,.25); }
.tag-red{ background: rgba(239,68,68,.09); border-color: rgba(239,68,68,.20); }
.tag-gray{ background: rgba(15,23,42,.03); border-color: rgba(15,23,42,.10); opacity: .95; }

.card-actions{ display:flex; gap: 12px; margin-top: 12px; }

.a-btn{
  flex: 1 1 0;
  display:flex;
  justify-content:center;
  align-items:center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(15, 23, 42, .12);
  background: rgba(255,255,255,.98);
  text-decoration:none !important;
  color: rgba(15, 23, 42, .92) !important;
  font-weight: 950;
  font-size: 14px;
  transition: .12s ease-in-out;
}
.a-btn:hover{ transform: translateY(-1px); box-shadow: 0 10px 18px rgba(0,0,0,.08); }
.a-btn.disabled{ opacity: .45; pointer-events: none; }

.hr-soft{
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed rgba(15, 23, 42, .14);
}

/* --- Expander --- */
div[data-testid="stExpander"] details{
  border-radius: 14px !important;
  border: 1px solid rgba(15,23,42,.10) !important;
  background: rgba(15,23,42,.018) !important;
}
div[data-testid="stExpander"] details summary{
  padding: 12px 12px !important;
  border-radius: 14px !important;
  font-weight: 950 !important;
  color: rgba(15,23,42,.94) !important;
  list-style: none !important;
}
div[data-testid="stExpander"] details summary:hover{
  background: rgba(60,130,255,.06) !important;
}
div[data-testid="stExpander"] details summary::-webkit-details-marker { display:none; }
div[data-testid="stExpander"] details summary:before{
  content: "▸";
  display:inline-block;
  margin-right: 10px;
  font-weight: 950;
  transform: translateY(-1px);
  opacity: .75;
}
div[data-testid="stExpander"] details[open] summary:before{ content:"▾"; }

.detail-block{
  margin-top: 10px;
  padding: 12px 12px;
  border-radius: 12px;
  border: 1px solid rgba(15, 23, 42, .10);
  background: rgba(255,255,255,.92);
}
.detail-title{ font-weight: 950; margin-bottom: 8px; }
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
    st.error("Данные не загрузились. Проверьте CSV_URL в Secrets (публичный CSV Google Sheets).")
    st.stop()

df = normalize_schema(raw)

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
# DETAIL RENDER
# =============================
def _money(v) -> str:
    s = safe_text(v, fallback="—")
    if s == "—":
        return s
    try:
        x = float(str(s).replace(" ", "").replace(",", "."))
        return f"{x:,.2f}".replace(",", " ").replace(".00", "") + " ₽"
    except Exception:
        return s


def render_details(row: pd.Series):
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

    block(
        "🏛️ Программы",
        [
            ("ГП/СП:", safe_text(row.get("state_program", ""))),
            ("ФП:", safe_text(row.get("federal_project", ""))),
            ("РП:", safe_text(row.get("regional_program", ""))),
        ],
    )

    block(
        "📑 Соглашение",
        [
            ("№:", safe_text(row.get("agreement", ""))),
            ("Дата:", fmt_date_ru(parse_any_date(row.get("agreement_date", "")))),
            ("Сумма:", _money(row.get("agreement_amount", ""))),
        ],
    )

    block(
        "📌 Параметры",
        [
            ("Мощность:", safe_text(row.get("capacity_seats", ""))),
            ("Площадь:", safe_text(row.get("area_m2", ""))),
            ("Целевой срок:", fmt_date_ru(parse_any_date(row.get("target_deadline", "")))),
        ],
    )

    block(
        "🧾 ПСД / Экспертиза",
        [
            ("Стоимость ПСД:", _money(row.get("psd_cost", ""))),
            ("Проектировщик:", safe_text(row.get("designer", ""))),
            ("Экспертиза:", safe_text(row.get("expertise", ""))),
            ("Дата экспертизы:", fmt_date_ru(parse_any_date(row.get("expertise_date", "")))),
            ("Заключение:", safe_text(row.get("expertise_conclusion", ""))),
        ],
    )

    block(
        "🏗️ РНС",
        [
            ("№ РНС:", safe_text(row.get("rns", ""))),
            ("Дата:", fmt_date_ru(parse_any_date(row.get("rns_date", "")))),
            ("Срок действия:", fmt_date_ru(parse_any_date(row.get("rns_expiry", "")))),
        ],
    )

    block(
        "📦 Контракт",
        [
            ("№:", safe_text(row.get("contract", ""))),
            ("Дата:", fmt_date_ru(parse_any_date(row.get("contract_date", "")))),
            ("Подрядчик:", safe_text(row.get("contractor", ""))),
            ("Цена:", _money(row.get("contract_price", ""))),
        ],
    )

    block(
        "⏱️ Сроки / Финансы",
        [
            ("Окончание (план):", fmt_date_ru(parse_any_date(row.get("end_date_plan", "")))),
            ("Окончание (факт):", fmt_date_ru(parse_any_date(row.get("end_date_fact", "")))),
            ("Готовность:", safe_text(row.get("readiness", ""))),
            ("Оплачено:", _money(row.get("paid", ""))),
        ],
    )


# =============================
# CARD RENDER (КЛЮЧЕВОЕ: unsafe_allow_html=True)
# =============================
def render_card(row: pd.Series):
    title = safe_text(row.get("name", ""), fallback="Объект")
    obj_id = safe_text(row.get("id", ""), fallback="—")
    obj_type = safe_text(row.get("object_type", ""), fallback="—")
    sector = safe_text(row.get("sector", ""), fallback="—")
    district = safe_text(row.get("district", ""), fallback="—")
    address = safe_text(row.get("address", ""), fallback="—")
    responsible = safe_text(row.get("responsible", ""), fallback="—")
    status = safe_text(row.get("status", ""), fallback="—")

    works = safe_text(row.get("works_in_progress", ""), fallback="—")
    issues = safe_text(row.get("issues", ""), fallback="—")

    card_url = safe_text(row.get("card_url", ""), fallback="")
    folder_url = safe_text(row.get("folder_url", ""), fallback="")

    upd_cls, upd_label = update_traffic_class(row.get("last_update", ""))
    works_cls, works_label = works_traffic_class(works)
    status_cls = status_class(status)

    tone = status_tone(status)
    accent = {
        "green": "rgba(34,197,94,.55)",
        "yellow": "rgba(245,158,11,.55)",
        "red": "rgba(239,68,68,.55)",
        "gray": "rgba(15,23,42,.18)",
    }.get(tone, "rgba(15,23,42,.18)")

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

    # ВОТ ЗДЕСЬ И БЫЛА ПРИЧИНА: обязательно unsafe_allow_html=True
    st.markdown(
        f"""
<div class="card">
  <div class="card-inner">
    <div class="card-accent" style="background:{accent};"></div>

    <h3 class="card-title">{title}</h3>

    <div class="card-subchips">
      <span class="chip">🆔 {obj_id}</span>
      <span class="chip chip-muted">🏷️ {sector}</span>
      <span class="chip chip-muted">📍 {district}</span>
      <span class="chip chip-muted">🏛️ {obj_type}</span>
    </div>

    <div class="card-grid">
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
</div>
""",
        unsafe_allow_html=True,
    )

    # Раскрытие данных — чтобы лента не была “простынёй”
    exp_title = "📋 Паспорт объекта и контрольные показатели — нажмите, чтобы раскрыть"
    with st.expander(exp_title, expanded=False):
        if issues and issues != "—" and issues.strip():
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
