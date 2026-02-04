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
    if s.lower() in ("nan", "none", "null", ""):
        return fallback
    return s


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


def parse_date_any(v) -> date | None:
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
    if not s or s.lower() in ("—", "nan", "none", "null"):
        return None

    m = re.match(r"^(\d{2})\.(\d{2})\.(\d{4})$", s)
    if m:
        dd, mm, yy = map(int, m.groups())
        try:
            return date(yy, mm, dd)
        except Exception:
            return None

    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", s)
    if m:
        yy, mm, dd = map(int, m.groups())
        try:
            return date(yy, mm, dd)
        except Exception:
            return None

    # excel serial
    if re.fullmatch(r"\d+(\.\d+)?", s):
        try:
            num = float(s.replace(",", "."))
            dt = pd.to_datetime(num, unit="D", origin="1899-12-30", errors="coerce")
            if pd.isna(dt):
                return None
            return dt.date()
        except Exception:
            return None

    try:
        dt = pd.to_datetime(s, errors="coerce", dayfirst=True)
        if pd.isna(dt):
            return None
        return dt.date()
    except Exception:
        return None


def fmt_date(v) -> str:
    d = parse_date_any(v)
    return d.strftime("%d.%m.%Y") if d else "—"


def fmt_money(v) -> str:
    s = safe_text(v, fallback="—")
    if s == "—":
        return s
    try:
        x = str(s).replace(" ", "").replace("\u00a0", "").replace(",", ".")
        x = float(x)
        return f"{x:,.2f}".replace(",", " ").replace(".00", "") + " ₽"
    except Exception:
        return s if ("₽" in s or "руб" in s.lower()) else f"{s} ₽"


def fmt_area(v) -> str:
    s = safe_text(v, fallback="—")
    if s == "—":
        return s
    try:
        x = float(str(s).replace(" ", "").replace("\u00a0", "").replace(",", "."))
        if abs(x - round(x)) < 1e-9:
            return f"{int(round(x)):,} м²".replace(",", " ")
        return f"{x:,.2f} м²".replace(",", " ").replace(".00", "")
    except Exception:
        return s


def fmt_int(v) -> str:
    s = safe_text(v, fallback="—")
    if s == "—":
        return s
    try:
        x = float(str(s).replace(" ", "").replace("\u00a0", "").replace(",", "."))
        return str(int(round(x)))
    except Exception:
        return s


def fmt_percent(v) -> str:
    s = safe_text(v, fallback="—")
    if s == "—":
        return s
    if "%" in s:
        s2 = s.replace("%", "").strip().replace(",", ".")
        try:
            x = float(s2)
            return f"{int(round(x))}%"
        except Exception:
            return s
    try:
        x = float(s.replace(" ", "").replace("\u00a0", "").replace(",", "."))
        if 0 <= x <= 1:
            x *= 100
        x = max(0, min(100, x))
        return f"{int(round(x))}%"
    except Exception:
        return s


def status_accent(status_text: str) -> str:
    s = norm_col(status_text)
    if "останов" in s or "приостанов" in s:
        return "red"
    if "проектир" in s:
        return "yellow"
    if "строитель" in s:
        return "green"
    return "gray"


def works_accent(works_text: str) -> str:
    s = norm_col(works_text)
    if any(x in s for x in ["нет", "не вед", "не выполня", "останов", "приостанов"]):
        return "red"
    if any(x in s for x in ["да", "ведут", "выполн", "идут", "осущест"]):
        return "green"
    return "gray"


def updated_accent(updated_at_value) -> tuple[str, str]:
    d = parse_date_any(updated_at_value)
    if not d:
        return "gray", "—"
    days = (date.today() - d).days
    txt = d.strftime("%d.%m.%Y")
    if days <= 7:
        return "green", txt
    if days <= 14:
        return "yellow", txt
    return "red", txt


def normalize_search_text(s: str) -> str:
    s = norm_col(s)
    s = re.sub(r"[^0-9a-zа-я]+", "", s, flags=re.IGNORECASE)
    return s


def make_acronym_ru(text: str) -> str:
    if not text:
        return ""
    words = re.findall(r"[А-Яа-яA-Za-z]+", str(text))
    letters = []
    for w in words:
        w = w.strip()
        if len(w) <= 2:
            continue
        letters.append(w[0])
    return "".join(letters).upper()


ABBR_MAP = {
    "фап": ["фельдшерскоакушерскийпункт", "фельдшерскоакушерский", "акушерскийпункт"],
    "одкб": ["областнаядетскаяклиническаябольница", "детскаяклиническаябольница", "клиническаябольница"],
    "црб": ["центральнаярайоннаябольница", "районнаябольница"],
    "фок": ["физкультурнооздоровительныйкомплекс", "физкультурныйкомплекс", "оздоровительныйкомплекс"],
}


def expand_query_tokens(q_raw: str) -> list[str]:
    q = norm_col(q_raw)
    qn = normalize_search_text(q)
    tokens = [qn] if qn else []

    if q in ABBR_MAP:
        tokens.extend(ABBR_MAP[q])

    for k, variants in ABBR_MAP.items():
        if k in q:
            tokens.extend(variants)

    out = []
    for t in tokens:
        if t and t not in out:
            out.append(t)
    return out


def normalize_url(url: str) -> str:
    """
    Исправляет частую проблему:
    если в таблице лежит "docs.google.com/...." без https://,
    Streamlit воспринимает как относительный путь и уводит обратно в приложение.
    """
    u = safe_text(url, fallback="")
    if not u or u == "—":
        return ""
    u = u.strip()
    if u.startswith("//"):
        u = "https:" + u
    if not (u.startswith("http://") or u.startswith("https://")):
        u = "https://" + u
    return u


# =============================
# DATA LOADING
# =============================
@st.cache_data(show_spinner=False, ttl=60)
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
    if df.empty:
        return df

    col_sector = pick_col(df, ["отрасль", "sector"])
    col_district = pick_col(df, ["район", "district"])
    col_name = pick_col(df, ["object_name", "наименование_объекта", "наименование объекта", "объект", "name"])
    col_address = pick_col(df, ["адрес", "address"])
    col_resp = pick_col(df, ["ответственный", "responsible"])
    col_status = pick_col(df, ["статус", "status"])
    col_works = pick_col(df, ["works_in_progress", "работы", "works", "work_flag", "вид работ"])
    col_card = pick_col(df, ["card_url", "ссылка_на_карточку", "ссылка на карточку"])
    col_updated = pick_col(df, ["updated_at", "last_update", "обновлено", "дата обновления"])

    passport_map = {
        "state_program": ["state_program", "госпрограмма", "гп", "государственная программа"],
        "federal_project": ["federal_project", "федеральный проект", "фп"],
        "regional_program": ["regional_program", "региональная программа", "рп"],
        "agreement": ["agreement", "соглашение"],
        "agreement_date": ["agreement_date", "дата соглашения"],
        "agreement_amount": ["agreement_amount", "сумма соглашения"],
        "capacity_seats": ["capacity_seats", "мощность", "мест"],
        "area_m2": ["area_m2", "площадь"],
        "target_deadline": ["target_deadline", "срок_достижения", "срок достижения результата", "целевой срок"],
        "psd_cost": ["psd_cost", "стоимость_псд", "стоимость псд"],
        "designer": ["designer", "проектировщик"],
        "expertise": ["expertise", "экспертиза"],
        "expertise_conclusion": ["expertise_conclusion", "заключение экспертизы", "заключение"],
        "expertise_date": ["expertise_date", "дата экспертизы"],
        "rns": ["rns", "рнс"],
        "rns_date": ["rns_date", "дата рнс"],
        "rns_expiry": ["rns_expiry", "рнс до", "срок действия рнс"],
        "contract": ["contract", "контракт"],
        "contract_date": ["contract_date", "дата контракта"],
        "contractor": ["contractor", "подрядчик"],
        "contract_price": ["contract_price", "цена контракта"],
        "end_date_plan": ["end_date_plan", "срок окончания план"],
        "end_date_fact": ["end_date_fact", "срок окончания факт"],
        "readiness": ["readiness", "готовность"],
        "paid": ["paid", "оплачено"],
        "issues": ["issues", "проблемные вопросы", "проблемы"],
    }

    out = pd.DataFrame()
    out["sector"] = df[col_sector] if col_sector else ""
    out["district"] = df[col_district] if col_district else ""
    out["name"] = df[col_name] if col_name else ""
    out["address"] = df[col_address] if col_address else ""
    out["responsible"] = df[col_resp] if col_resp else ""
    out["status"] = df[col_status] if col_status else ""
    out["work_flag"] = df[col_works] if col_works else ""
    out["card_url"] = df[col_card] if col_card else ""
    out["updated_at"] = df[col_updated] if col_updated else ""

    for k, candidates in passport_map.items():
        c = pick_col(df, candidates)
        out[k] = df[c] if c else ""

    for c in out.columns:
        out[c] = out[c].astype(str).replace({"nan": "", "None": "", "null": ""})

    return out


# =============================
# STYLES
# =============================
crest_b64 = read_local_crest_b64()

st.markdown(
    """
<style>
.block-container { padding-top: 22px !important; max-width: 1200px; }
@media (max-width: 1200px){ .block-container { max-width: 96vw; } }
div[data-testid="stHorizontalBlock"]{ gap: 14px; }
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

:root{
  --bg: #f7f8fb;
  --card: #ffffff;
  --text: rgba(15,23,42,.96);
  --muted: rgba(15,23,42,.70);
  --border: rgba(15,23,42,.10);
  --shadow: 0 12px 26px rgba(0,0,0,.06);
  --panel: rgba(15,23,42,.04);
  --chip: rgba(15,23,42,.05);
  --btn: rgba(255,255,255,.90);

  --green: rgba(34,197,94,.55);
  --yellow: rgba(245,158,11,.55);
  --red: rgba(239,68,68,.55);
  --gray: rgba(148,163,184,.55);

  --soft-red-bg: rgba(239,68,68,.08);
  --soft-red-bd: rgba(239,68,68,.18);
}

@media (prefers-color-scheme: dark){
  :root{
    --bg: #0b1220;
    --card: rgba(255,255,255,.06);
    --text: rgba(255,255,255,.92);
    --muted: rgba(255,255,255,.68);
    --border: rgba(255,255,255,.12);
    --shadow: 0 18px 34px rgba(0,0,0,.40);
    --panel: rgba(255,255,255,.06);
    --chip: rgba(255,255,255,.08);
    --btn: rgba(255,255,255,.08);

    --soft-red-bg: rgba(239,68,68,.10);
    --soft-red-bd: rgba(239,68,68,.20);
  }
}

body{ background: var(--bg) !important; }

/* HERO (без лишних разделителей, минимальный отступ вниз) */
.hero-wrap{ width:100%; display:flex; justify-content:center; margin-bottom: 6px; }
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
  width: 74px; height: 74px;
  border-radius: 14px;
  background: rgba(255,255,255,.10);
  display:flex; align-items:center; justify-content:center;
  border: 1px solid rgba(255,255,255,.16);
  flex: 0 0 auto;
}
.hero-crest img{ width: 56px; height: 56px; object-fit: contain; filter: drop-shadow(0 6px 10px rgba(0,0,0,.35)); }
.hero-titles{ flex: 1 1 auto; min-width: 0; }
.hero-ministry{ color: rgba(255,255,255,.95); font-weight: 900; font-size: 20px; line-height: 1.15; }
.hero-app{ margin-top: 6px; color: rgba(255,255,255,.92); font-weight: 800; font-size: 16px; }
.hero-sub{ margin-top: 6px; color: rgba(255,255,255,.78); font-size: 13px; }
@media (max-width: 900px){
  .hero-ministry{ font-size: 16px; }
  .hero-row{ align-items:center; }
}

/* Controls (прямо под шапкой, без лишних полос/разделений) */
.controls{
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 12px 12px 10px 12px;
  box-shadow: var(--shadow);
  margin: 0 0 12px 0;
}
.controls-top{
  display:flex; align-items:center; justify-content:space-between;
  gap: 12px; margin-bottom: 10px;
}
.controls-title{ font-weight: 950; font-size: 14px; color: var(--text); }
.controls-hint{ font-size: 12px; color: var(--muted); }

/* Widgets */
div[data-baseweb="select"] > div{
  border-radius: 12px !important;
  border: 1px solid var(--border) !important;
  background: rgba(255,255,255,.06) !important;
}
div[data-baseweb="input"] input{
  border-radius: 12px !important;
  border: 1px solid var(--border) !important;
  background: rgba(255,255,255,.06) !important;
  color: var(--text) !important;
}
label{ color: var(--muted) !important; font-weight: 900 !important; }

/* CARD with FULL border by status */
.card{
  background: var(--card);
  border-radius: 18px;
  padding: 16px 16px 14px 16px;
  box-shadow: var(--shadow);
  margin-bottom: 14px;
  border: 2px solid var(--border);
  position: relative;
  overflow: hidden;
}
.card.border-green{ border-color: var(--green); }
.card.border-yellow{ border-color: var(--yellow); }
.card.border-red{ border-color: var(--red); }
.card.border-gray{ border-color: var(--gray); }

/* subtle inner glow */
.card:after{
  content:"";
  position:absolute;
  inset:-120px -80px auto auto;
  width: 420px; height: 220px;
  background: radial-gradient(circle at 30% 30%, rgba(59,130,246,.14), rgba(0,0,0,0) 70%);
  transform: rotate(12deg);
  pointer-events:none;
}

.card-title{
  display:block;
  font-size: 18px;
  line-height: 1.25;
  font-weight: 950;
  margin: 0 0 10px 0;
  color: var(--text);
  padding: 10px 12px;
  border-radius: 14px;
  border: 1px solid var(--border);
  background: linear-gradient(180deg, rgba(255,255,255,.06), rgba(0,0,0,0));
}

.chips{ display:flex; gap:8px; flex-wrap:wrap; margin-bottom: 10px; }
.chip{
  display:inline-flex; align-items:center; gap:8px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: var(--chip);
  font-size: 12px;
  color: var(--text);
  font-weight: 900;
}

.card-grid{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 18px;
  margin-top: 6px;
}
.card-item{ font-size: 14px; color: var(--text); }
.card-item b{ color: var(--text); }

.card-tags{ display:flex; gap: 10px; flex-wrap: wrap; margin-top: 12px; }
.tag{
  display:inline-flex; align-items:center; gap: 8px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: var(--chip);
  font-size: 13px;
  color: var(--text);
  font-weight: 900;
}
.tag-green{ background: rgba(34,197,94,.10); border-color: rgba(34,197,94,.18); }
.tag-yellow{ background: rgba(245,158,11,.12); border-color: rgba(245,158,11,.20); }
.tag-red{ background: rgba(239,68,68,.10); border-color: rgba(239,68,68,.18); }
.tag-gray{ background: var(--chip); }

.card-actions{ display:flex; gap: 12px; margin-top: 12px; }
.a-btn{
  flex: 1 1 0;
  display:flex; justify-content:center; align-items:center; gap: 8px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid var(--border);
  background: var(--btn);
  text-decoration:none !important;
  color: var(--text) !important;
  font-weight: 950;
  font-size: 14px;
  transition: .12s ease-in-out;
}
.a-btn:hover{ transform: translateY(-1px); box-shadow: 0 10px 18px rgba(0,0,0,.10); }
.a-btn.disabled{ opacity: .45; pointer-events: none; }

/* Passport details */
details{
  margin-top: 12px;
  background: rgba(255,255,255,.04);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 10px 12px;
}
summary{
  cursor:pointer;
  font-weight: 950;
  color: var(--text);
  list-style: none;
}
summary::-webkit-details-marker{ display:none; }

.section{
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed var(--border);
}
.section-title{
  font-weight: 950;
  color: var(--text);
  margin-bottom: 6px;
}
.row{
  color: var(--text);
  font-size: 13px;
  margin: 4px 0;
}
.row b{ color: var(--text); }

.issue-box{
  border: 1px solid var(--soft-red-bd);
  background: var(--soft-red-bg);
  border-radius: 12px;
  padding: 10px 12px;
  color: var(--text);
  font-size: 13px;
  line-height: 1.35;
}

/* real collapse button */
.collapse-btn{
  display:inline-block;
  margin-top: 10px;
  font-weight: 900;
  font-size: 13px;
  color: var(--muted) !important;
  text-decoration:none !important;
  border: 1px solid var(--border);
  background: rgba(255,255,255,.05);
  padding: 8px 10px;
  border-radius: 12px;
}
.collapse-btn:hover{ color: var(--text) !important; }

@media (max-width: 900px){
  .card-grid{ grid-template-columns: 1fr; }
  .card-title{ font-size: 16px; }
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
    st.error("Данные не загрузились (реестр пустой). Проверьте CSV_URL в Secrets.")
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
# CONTROLS (без разделителей под шапкой)
# =============================
st.markdown(
    """
<div class="controls">
  <div class="controls-top">
    <div class="controls-title">Фильтры и поиск</div>
    <div class="controls-hint">Сокращения: ФАП, ОДКБ, ЦРБ, ФОК…</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

c1, c2, c3, c4 = st.columns([1, 1, 1, 1.4])
with c1:
    sector_sel = st.selectbox("🏷️ Отрасль", sectors, index=0, key="f_sector")
with c2:
    district_sel = st.selectbox("📍 Район", districts, index=0, key="f_district")
with c3:
    status_sel = st.selectbox("📌 Статус", statuses, index=0, key="f_status")
with c4:
    # ВАЖНО: НЕ в form -> поиск применяется без “кнопки”
    q_raw = st.text_input("🔎 Поиск", value="", key="f_search", placeholder="Напр.: ФАП, ОДКБ, школа 500, Тускарная...")


# =============================
# APPLY FILTERS + SEARCH
# =============================
filtered = df.copy()

if sector_sel != "Все":
    filtered = filtered[filtered["sector"].astype(str) == str(sector_sel)]
if district_sel != "Все":
    filtered = filtered[filtered["district"].astype(str) == str(district_sel)]
if status_sel != "Все":
    filtered = filtered[filtered["status"].astype(str) == str(status_sel)]

tokens = expand_query_tokens(q_raw)

if tokens:

    def row_match(r: pd.Series) -> bool:
        name = str(r.get("name", "") or "")
        address = str(r.get("address", "") or "")
        resp = str(r.get("responsible", "") or "")
        sector = str(r.get("sector", "") or "")
        district = str(r.get("district", "") or "")

        hay = " ".join([name, address, resp, sector, district])
        hay_norm = normalize_search_text(hay)

        acr = make_acronym_ru(name)
        acr_norm = normalize_search_text(acr)

        name_norm = normalize_search_text(name)
        addr_norm = normalize_search_text(address)

        for t in tokens:
            if not t:
                continue
            if t in hay_norm or t in name_norm or t in addr_norm:
                return True
            if acr_norm and t == acr_norm:
                return True
        return False

    filtered = filtered[filtered.apply(row_match, axis=1)]

st.caption(f"Показано объектов: {len(filtered)} из {len(df)}")


# =============================
# PASSPORT HTML
# =============================
def passport_html(row: pd.Series, uid: str) -> str:
    issues = safe_text(row.get("issues", ""))

    blocks = []

    if issues not in ("—", ""):
        blocks.append(
            f"""
<div class="section">
  <div class="section-title">⚠️ Проблемные вопросы</div>
  <div class="issue-box">{issues}</div>
</div>
"""
        )

    def add_kv_section(title: str, items: list[tuple[str, str]]):
        show = any(v not in ("—", "") for _, v in items)
        if not show:
            return
        rows = "\n".join([f'<div class="row"><b>{k}:</b> {v}</div>' for k, v in items])
        blocks.append(
            f"""
<div class="section">
  <div class="section-title">{title}</div>
  {rows}
</div>
"""
        )

    add_kv_section(
        "🏛️ Программы",
        [
            ("ГП/СП", safe_text(row.get("state_program", ""))),
            ("ФП", safe_text(row.get("federal_project", ""))),
            ("РП", safe_text(row.get("regional_program", ""))),
        ],
    )

    add_kv_section(
        "🧾 Соглашение",
        [
            ("№", safe_text(row.get("agreement", ""))),
            ("Дата", fmt_date(row.get("agreement_date", ""))),
            ("Сумма", fmt_money(row.get("agreement_amount", ""))),
        ],
    )

    add_kv_section(
        "📦 Параметры",
        [
            ("Мощность", fmt_int(row.get("capacity_seats", ""))),
            ("Площадь", fmt_area(row.get("area_m2", ""))),
            ("Целевой срок", fmt_date(row.get("target_deadline", ""))),
        ],
    )

    add_kv_section(
        "📑 ПСД / Экспертиза",
        [
            ("Стоимость ПСД", fmt_money(row.get("psd_cost", ""))),
            ("Проектировщик", safe_text(row.get("designer", ""))),
            ("Экспертиза", safe_text(row.get("expertise", ""))),
            ("Дата экспертизы", fmt_date(row.get("expertise_date", ""))),
            ("Заключение", safe_text(row.get("expertise_conclusion", ""))),
        ],
    )

    add_kv_section(
        "🏗️ РНС",
        [
            ("№ РНС", safe_text(row.get("rns", ""))),
            ("Дата", fmt_date(row.get("rns_date", ""))),
            ("Срок действия", fmt_date(row.get("rns_expiry", ""))),
        ],
    )

    add_kv_section(
        "🧱 Контракт",
        [
            ("№", safe_text(row.get("contract", ""))),
            ("Дата", fmt_date(row.get("contract_date", ""))),
            ("Подрядчик", safe_text(row.get("contractor", ""))),
            ("Цена", fmt_money(row.get("contract_price", ""))),
        ],
    )

    add_kv_section(
        "⏱️ Сроки / Финансы",
        [
            ("Окончание (план)", fmt_date(row.get("end_date_plan", ""))),
            ("Окончание (факт)", fmt_date(row.get("end_date_fact", ""))),
            ("Готовность", fmt_percent(row.get("readiness", ""))),
            ("Оплачено", fmt_money(row.get("paid", ""))),
        ],
    )

    if not blocks:
        blocks.append('<div class="row" style="color:var(--muted)">Нет паспортных данных для отображения.</div>')

    # ✅ РЕАЛЬНО закрывает details: снимает атрибут open
    blocks.append(
        f"""
<a class="collapse-btn" href="#{uid}" onclick="this.closest('details').removeAttribute('open'); return false;">
  ⬆️ Свернуть паспорт
</a>
"""
    )

    return "\n".join(blocks)


# =============================
# CARD RENDER
# =============================
def render_card(row: pd.Series, idx: int):
    uid = f"card_{idx}"

    title = safe_text(row.get("name", ""), fallback="Объект")
    sector = safe_text(row.get("sector", ""), fallback="—")
    district = safe_text(row.get("district", ""), fallback="—")
    address = safe_text(row.get("address", ""), fallback="—")
    responsible = safe_text(row.get("responsible", ""), fallback="—")

    status = safe_text(row.get("status", ""), fallback="—")
    work_flag = safe_text(row.get("work_flag", ""), fallback="—")

    card_url = normalize_url(row.get("card_url", ""))

    # border by status
    s_acc = status_accent(status)
    border_cls = f"border-{s_acc}"

    # works traffic light (soft)
    w_acc = works_accent(work_flag)
    work_tag_cls = "tag tag-gray"
    if w_acc == "green":
        work_tag_cls = "tag tag-green"
    elif w_acc == "red":
        work_tag_cls = "tag tag-red"

    # updated traffic light
    u_acc, u_txt = updated_accent(row.get("updated_at", ""))
    upd_tag_cls = "tag tag-gray"
    if u_acc == "green":
        upd_tag_cls = "tag tag-green"
    elif u_acc == "yellow":
        upd_tag_cls = "tag tag-yellow"
    elif u_acc == "red":
        upd_tag_cls = "tag tag-red"

    # status tag
    st_tag_cls = "tag tag-gray"
    if s_acc == "green":
        st_tag_cls = "tag tag-green"
    elif s_acc == "yellow":
        st_tag_cls = "tag tag-yellow"
    elif s_acc == "red":
        st_tag_cls = "tag tag-red"

    btn_card = (
        f'<a class="a-btn" href="{card_url}" target="_blank" rel="noopener noreferrer">📄 Открыть карточку</a>'
        if card_url
        else '<span class="a-btn disabled">📄 Открыть карточку</span>'
    )

    passport = passport_html(row, uid)

    st.markdown(
        f"""
<div class="card {border_cls}" id="{uid}">
  <div class="card-title">{title}</div>

  <div class="chips">
    <span class="chip">🏷️ {sector}</span>
    <span class="chip">📍 {district}</span>
  </div>

  <div class="card-grid">
    <div class="card-item">🗺️ <b>Адрес:</b> {address}</div>
    <div class="card-item">👤 <b>Ответственный:</b> {responsible}</div>
  </div>

  <div class="card-tags">
    <span class="{st_tag_cls}">📌 Статус: {status}</span>
    <span class="{work_tag_cls}">🛠️ Работы: {work_flag}</span>
    <span class="{upd_tag_cls}">🕒 Обновлено: {u_txt}</span>
  </div>

  <div class="card-actions">
    {btn_card}
  </div>

  <details>
    <summary>🧾 Паспорт объекта и контрольные показатели</summary>
    {passport}
  </details>
</div>
""",
        unsafe_allow_html=True,
    )


# =============================
# OUTPUT
# =============================
for i, r in enumerate(filtered.to_dict(orient="records"), start=0):
    render_card(pd.Series(r), i)
