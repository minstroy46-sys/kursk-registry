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


def parse_date_any(v) -> date | None:
    """
    Понимает:
    - '04.02.2026', '2026-02-04'
    - excel-серийные числа (если вдруг придут)
    - пусто -> None
    """
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except Exception:
        pass

    s = str(v).strip()
    if not s or s.lower() in ("—", "nan", "none"):
        return None

    # dd.mm.yyyy
    m = re.match(r"^(\d{2})\.(\d{2})\.(\d{4})$", s)
    if m:
        dd, mm, yy = map(int, m.groups())
        try:
            return date(yy, mm, dd)
        except Exception:
            return None

    # yyyy-mm-dd
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", s)
    if m:
        yy, mm, dd = map(int, m.groups())
        try:
            return date(yy, mm, dd)
        except Exception:
            return None

    # excel serial
    try:
        num = float(s.replace(",", "."))
        # Excel origin 1899-12-30 for pandas
        dt = pd.to_datetime(num, unit="D", origin="1899-12-30", errors="coerce")
        if pd.isna(dt):
            return None
        return dt.date()
    except Exception:
        return None


def fmt_date(d: date | None) -> str:
    return d.strftime("%d.%m.%Y") if isinstance(d, date) else "—"


def fmt_money(v) -> str:
    try:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return "—"
        s = str(v).strip()
        if not s or s.lower() in ("—", "nan", "none"):
            return "—"
        x = float(s.replace(" ", "").replace("\u00a0", "").replace(",", "."))
        return f"{x:,.2f} ₽".replace(",", " ").replace(".00", "")
    except Exception:
        return safe_text(v, "—")


def fmt_area(v) -> str:
    try:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return "—"
        s = str(v).strip()
        if not s or s.lower() in ("—", "nan", "none"):
            return "—"
        x = float(s.replace(" ", "").replace("\u00a0", "").replace(",", "."))
        # без лишних .00
        if abs(x - round(x)) < 1e-9:
            return f"{int(round(x)):,} м²".replace(",", " ")
        return f"{x:,.2f} м²".replace(",", " ").replace(".00", "")
    except Exception:
        return safe_text(v, "—")


def fmt_int(v) -> str:
    try:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return "—"
        s = str(v).strip()
        if not s or s.lower() in ("—", "nan", "none"):
            return "—"
        x = float(s.replace(" ", "").replace("\u00a0", "").replace(",", "."))
        return f"{int(round(x))}"
    except Exception:
        return safe_text(v, "—")


def fmt_percent(v) -> str:
    """
    Если приходит 0.38 -> 38%
    Если приходит 38 -> 38%
    """
    try:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return "—"
        s = str(v).strip()
        if not s or s.lower() in ("—", "nan", "none"):
            return "—"
        x = float(s.replace(" ", "").replace("\u00a0", "").replace(",", "."))
        if 0 <= x <= 1:
            x = x * 100
        x = max(0, min(100, x))
        return f"{int(round(x))}%"
    except Exception:
        return safe_text(v, "—")


def status_class(status_text: str) -> str:
    s = norm_col(status_text)
    if "останов" in s or "приостанов" in s:
        return "tag tag-status tag-red"
    if "проектир" in s:
        return "tag tag-status tag-yellow"
    if "строитель" in s:
        return "tag tag-status tag-green"
    return "tag tag-status tag-gray"


def works_class(works_text: str) -> str:
    s = norm_col(works_text)
    # трактуем "нет", "не ведутся", "не ведется" как красный
    if any(x in s for x in ["нет", "не вед", "не выполня", "не осуществ", "останов", "приостанов"]):
        return "tag tag-gray tag-red"
    # трактуем "да", "ведутся", "выполняются" как зеленый
    if any(x in s for x in ["да", "ведут", "выполн", "осущест", "идут"]):
        return "tag tag-gray tag-green"
    return "tag tag-gray"


def updated_class(updated_at_value) -> tuple[str, str]:
    """
    Светофор по дате обновления:
    1-7 дней зелёный, 7-14 жёлтый, >14 красный.
    Возвращает (css_class, text)
    """
    d = parse_date_any(updated_at_value)
    if not d:
        return ("tag tag-gray tag-red", "—")

    days = (date.today() - d).days
    text = fmt_date(d)

    if days <= 7:
        return ("tag tag-gray tag-green", text)
    if days <= 14:
        return ("tag tag-gray tag-yellow", text)
    return ("tag tag-gray tag-red", text)


def normalize_search_text(s: str) -> str:
    """
    Нормализация для гибкого поиска:
    - lower
    - ё->е
    - убираем все кроме букв/цифр
    """
    s = norm_col(s)
    s = re.sub(r"[^0-9a-zа-я]+", "", s, flags=re.IGNORECASE)
    return s


def make_acronym_ru(text: str) -> str:
    """
    Строим аббревиатуру по словам: "Областная детская клиническая больница" -> "ОДКБ"
    """
    if not text:
        return ""
    words = re.findall(r"[А-Яа-яA-Za-z]+", str(text))
    letters = []
    for w in words:
        w = w.strip()
        if len(w) <= 2:
            continue
        letters.append(w[0])
    acr = "".join(letters).upper()
    return acr


# Карта популярных сокращений -> "полные" подсказки (для расширения запроса)
ABBR_MAP = {
    "фап": ["фельдшерскоакушерскийпункт", "фельдшерскоакушерский", "фельдшерско", "акушерскийпункт"],
    "одкб": ["областнаядетскаяклиническаябольница", "детскаяклиническаябольница", "клиническаябольница"],
    "црб": ["центральнаярайоннаябольница", "районнаябольница"],
    "фок": ["физкультурнооздоровительныйкомплекс", "физкультурныйкомплекс", "оздоровительныйкомплекс"],
    "дк": ["домкультуры", "культурнодосуговыйцентр", "центркультуры"],
    "школа": ["школа", "сош", "мкоу", "оу"],
    "дс": ["детскийсад", "доу", "мбдоу"],
}


def expand_query_tokens(q_raw: str) -> list[str]:
    """
    Возвращает список нормализованных "токенов" поиска:
    - сам запрос
    - если это известное сокращение — добавляем варианты расшифровки
    """
    q = norm_col(q_raw)
    qn = normalize_search_text(q)
    tokens = [qn] if qn else []
    if q in ABBR_MAP:
        tokens.extend(ABBR_MAP[q])
    # если пользователь ввёл "фап" внутри строки (например "фап олховатка")
    for k, variants in ABBR_MAP.items():
        if k in q:
            tokens.extend(variants)
    # убираем дубли
    out = []
    for t in tokens:
        if t and t not in out:
            out.append(t)
    return out


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
    Unified columns (для карточек):
    id, sector, district, name, address, responsible, status, work_flag, card_url, folder_url, updated_at
    + дополнительные поля (паспорт)
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
    col_works = pick_col(df, ["работы", "works", "вид работ", "work_flag", "works_in_progress"])
    col_card = pick_col(df, ["card_url", "ссылка на карточку", "ссылка_на_карточку"])
    col_folder = pick_col(df, ["folder_url", "ссылка на папку", "ссылка_на_папку"])
    col_updated = pick_col(df, ["updated_at", "last_update", "обновлено", "дата обновления"])

    # паспортные поля (если есть в реестре)
    passport_map = {
        "state_program": ["state_program", "гп", "государственная программа"],
        "federal_project": ["federal_project", "фп", "федеральный проект"],
        "regional_program": ["regional_program", "рп", "региональная программа"],
        "agreement": ["agreement", "соглашение", "№ соглашения"],
        "agreement_date": ["agreement_date", "дата соглашения"],
        "agreement_amount": ["agreement_amount", "сумма соглашения"],
        "capacity_seats": ["capacity_seats", "мощность", "мест", "посещений"],
        "area_m2": ["area_m2", "площадь"],
        "target_deadline": ["target_deadline", "целевой срок"],
        "psd_cost": ["psd_cost", "стоимость пcд", "стоимость псд"],
        "designer": ["designer", "проектировщик"],
        "expertise": ["expertise", "экспертиза"],
        "expertise_conclusion": ["expertise_conclusion", "заключение экспертизы", "заключение"],
        "expertise_date": ["expertise_date", "дата экспертизы"],
        "rns": ["rns", "рнс", "разрешение на строительство", "№ рнс"],
        "rns_date": ["rns_date", "дата рнс"],
        "rns_expiry": ["rns_expiry", "срок действия рнс", "окончание рнс"],
        "contract": ["contract", "контракт", "№ контракта"],
        "contract_date": ["contract_date", "дата контракта"],
        "contractor": ["contractor", "подрядчик"],
        "contract_price": ["contract_price", "цена контракта", "стоимость контракта"],
        "end_date_plan": ["end_date_plan", "окончание (план)", "срок план"],
        "end_date_fact": ["end_date_fact", "окончание (факт)", "срок факт"],
        "readiness": ["readiness", "готовность", "процент готовности"],
        "paid": ["paid", "оплачено"],
        "issues": ["issues", "проблемные вопросы", "проблемы"],
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
    out["updated_at"] = df[col_updated] if col_updated else ""

    # добавим паспортные, если найдутся
    for k, candidates in passport_map.items():
        c = pick_col(df, candidates)
        out[k] = df[c] if c else ""

    for c in out.columns:
        out[c] = out[c].astype(str).replace({"nan": "", "None": ""})

    return out


# =============================
# STYLES (ТЁМНАЯ/СВЕТЛАЯ ТЕМА)
# =============================
crest_b64 = read_local_crest_b64()

st.markdown(
    """
<style>
/* ===== Base layout ===== */
.block-container { padding-top: 22px !important; max-width: 1200px; }
@media (max-width: 1200px){ .block-container { max-width: 96vw; } }
div[data-testid="stHorizontalBlock"]{ gap: 14px; }
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* ===== Theme variables ===== */
:root{
  --bg: #f7f8fb;
  --card: #ffffff;
  --text: rgba(15,23,42,.96);
  --muted: rgba(15,23,42,.70);
  --border: rgba(15,23,42,.10);
  --shadow: 0 12px 26px rgba(0,0,0,.06);
  --chip: rgba(15,23,42,.05);
  --chip2: rgba(15,23,42,.08);
  --panel: rgba(15,23,42,.04);
  --link: rgba(15,23,42,.92);
}

/* Dark mode (если браузер/OS dark) */
@media (prefers-color-scheme: dark){
  :root{
    --bg: #0b1220;
    --card: rgba(255,255,255,.06);
    --text: rgba(255,255,255,.92);
    --muted: rgba(255,255,255,.68);
    --border: rgba(255,255,255,.12);
    --shadow: 0 18px 34px rgba(0,0,0,.40);
    --chip: rgba(255,255,255,.08);
    --chip2: rgba(255,255,255,.12);
    --panel: rgba(255,255,255,.06);
    --link: rgba(255,255,255,.92);
  }
}

/* Background */
body{ background: var(--bg) !important; }

/* ===== Hero (ваш стиль) ===== */
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
.hero-ministry{ color: rgba(255,255,255,.95); font-weight: 900; font-size: 20px; line-height: 1.15; }
.hero-app{ margin-top: 6px; color: rgba(255,255,255,.92); font-weight: 800; font-size: 16px; }
.hero-sub{ margin-top: 6px; color: rgba(255,255,255,.78); font-size: 13px; }
@media (max-width: 900px){
  .hero-ministry{ font-size: 16px; }
  .hero-row{ align-items:center; }
}

/* ===== Filter panel ===== */
.filter-panel{
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 14px 14px 10px 14px;
  box-shadow: var(--shadow);
  margin-bottom: 8px;
}
.filter-title{
  font-weight: 900;
  font-size: 14px;
  color: var(--text);
  margin-bottom: 10px;
  opacity: .92;
}
.small-caption{ color: var(--muted); font-size: 12px; margin-top: 6px; }

/* Streamlit widgets polish */
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
label, .stTextInput label, .stSelectbox label{
  color: var(--muted) !important;
  font-weight: 800 !important;
}

/* ===== Cards ===== */
.card{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 18px;
  padding: 16px 16px 14px 16px;
  box-shadow: var(--shadow);
  margin-bottom: 14px;
  position: relative;
  overflow: hidden;
}
/* интересная рамка: тонкая градиентная линия слева + мягкая подсветка */
.card:before{
  content:"";
  position:absolute;
  left:0; top:0; bottom:0;
  width: 4px;
  background: linear-gradient(180deg, rgba(34,197,94,.85), rgba(59,130,246,.55), rgba(245,158,11,.55));
  opacity: .85;
}
.card:after{
  content:"";
  position:absolute;
  inset:-120px -80px auto auto;
  width: 420px; height: 220px;
  background: radial-gradient(circle at 30% 30%, rgba(59,130,246,.18), rgba(0,0,0,0) 70%);
  transform: rotate(12deg);
  pointer-events:none;
}

/* Заголовок объекта — аккуратная “плашка” */
.card-title{
  display:inline-block;
  font-size: 18px;
  line-height: 1.2;
  font-weight: 950;
  margin: 0 0 10px 0;
  color: var(--text);
  padding: 10px 12px;
  border-radius: 14px;
  border: 1px solid var(--border);
  background: linear-gradient(180deg, rgba(255,255,255,.06), rgba(0,0,0,0));
}
@media (prefers-color-scheme: light){
  .card-title{ background: linear-gradient(180deg, rgba(15,23,42,.03), rgba(255,255,255,0)); }
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
  font-weight: 800;
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
  font-weight: 800;
}

.tag-green{ background: rgba(34,197,94,.12); border-color: rgba(34,197,94,.22); }
.tag-yellow{ background: rgba(245,158,11,.14); border-color: rgba(245,158,11,.26); }
.tag-red{ background: rgba(239,68,68,.12); border-color: rgba(239,68,68,.24); }
.tag-gray{ background: var(--chip); }

.card-actions{ display:flex; gap: 12px; margin-top: 12px; }
.a-btn{
  flex: 1 1 0;
  display:flex; justify-content:center; align-items:center; gap: 8px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid var(--border);
  background: rgba(255,255,255,.06);
  text-decoration:none !important;
  color: var(--link) !important;
  font-weight: 900;
  font-size: 14px;
  transition: .12s ease-in-out;
}
.a-btn:hover{ transform: translateY(-1px); box-shadow: 0 10px 18px rgba(0,0,0,.10); }
.a-btn.disabled{ opacity: .45; pointer-events: none; }

.hr-soft{
  height: 1px;
  background: linear-gradient(90deg, rgba(0,0,0,0), var(--border), rgba(0,0,0,0));
  margin: 14px 0 10px 0;
}

/* details/expander styling */
details{
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
# FILTERS (красиво панелью)
# =============================
st.markdown('<div class="filter-panel">', unsafe_allow_html=True)
st.markdown('<div class="filter-title">Фильтры и поиск</div>', unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
with c1:
    sector_sel = st.selectbox("🏷️ Отрасль", sectors, index=0, key="f_sector")
with c2:
    district_sel = st.selectbox("📍 Район", districts, index=0, key="f_district")
with c3:
    status_sel = st.selectbox("📌 Статус", statuses, index=0, key="f_status")

q_raw = st.text_input("🔎 Поиск (в т.ч. по сокращениям: ФАП, ОДКБ, ЦРБ…)", value="", key="f_search").strip()
st.markdown('</div>', unsafe_allow_html=True)

if st.button("🔄 Обновить данные"):
    st.cache_data.clear()
    st.rerun()


# =============================
# APPLY FILTERS + FLEX SEARCH
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

        # базовая “склейка”
        hay = " ".join([name, address, resp, sector, district])
        hay_norm = normalize_search_text(hay)

        # автосгенерированная аббревиатура по названию
        acr = make_acronym_ru(name)
        acr_norm = normalize_search_text(acr)

        # также добавим “склейку” самого названия отдельно (часто помогает)
        name_norm = normalize_search_text(name)
        addr_norm = normalize_search_text(address)

        for t in tokens:
            if not t:
                continue
            # 1) обычное contains в нормализованной строке
            if t in hay_norm:
                return True
            # 2) поиск по аббревиатуре
            if acr_norm and t == acr_norm:
                return True
            # 3) если пользователь ввёл кусок “склеенного” слова — тоже ловим
            if t in name_norm or t in addr_norm:
                return True
        return False

    filtered = filtered[filtered.apply(row_match, axis=1)]

st.caption(f"Показано объектов: {len(filtered)} из {len(df)}")
st.divider()


# =============================
# CARD RENDER
# =============================
def render_passport(row: pd.Series):
    # вытягиваем значения
    state_program = safe_text(row.get("state_program", ""))
    federal_project = safe_text(row.get("federal_project", ""))
    regional_program = safe_text(row.get("regional_program", ""))

    agreement = safe_text(row.get("agreement", ""))
    agreement_date = fmt_date(parse_date_any(row.get("agreement_date", "")))
    agreement_amount = fmt_money(row.get("agreement_amount", ""))

    capacity_seats = fmt_int(row.get("capacity_seats", ""))
    area_m2 = fmt_area(row.get("area_m2", ""))
    target_deadline = fmt_date(parse_date_any(row.get("target_deadline", "")))

    psd_cost = fmt_money(row.get("psd_cost", ""))
    designer = safe_text(row.get("designer", ""))
    expertise = safe_text(row.get("expertise", ""))
    expertise_conclusion = safe_text(row.get("expertise_conclusion", ""))
    expertise_date = fmt_date(parse_date_any(row.get("expertise_date", "")))

    rns = safe_text(row.get("rns", ""))
    rns_date = fmt_date(parse_date_any(row.get("rns_date", "")))
    rns_expiry = fmt_date(parse_date_any(row.get("rns_expiry", "")))

    contract = safe_text(row.get("contract", ""))
    contract_date = fmt_date(parse_date_any(row.get("contract_date", "")))
    contractor = safe_text(row.get("contractor", ""))
    contract_price = fmt_money(row.get("contract_price", ""))

    end_plan = fmt_date(parse_date_any(row.get("end_date_plan", "")))
    end_fact = fmt_date(parse_date_any(row.get("end_date_fact", "")))
    readiness = fmt_percent(row.get("readiness", ""))
    paid = fmt_money(row.get("paid", ""))

    issues = safe_text(row.get("issues", ""))

    # рисуем секции (только если есть что показать — чтобы не было пустоты)
    blocks = []

    if any(x not in ("—", "") for x in [issues]):
        blocks.append(
            f"""
<div class="section">
  <div class="section-title">⚠️ Проблемные вопросы</div>
  <div class="row">{issues}</div>
</div>
"""
        )

    if any(x not in ("—", "") for x in [state_program, federal_project, regional_program]):
        blocks.append(
            f"""
<div class="section">
  <div class="section-title">🏛️ Программы</div>
  <div class="row"><b>ГП/СП:</b> {state_program}</div>
  <div class="row"><b>ФП:</b> {federal_project}</div>
  <div class="row"><b>РП:</b> {regional_program}</div>
</div>
"""
        )

    if any(x not in ("—", "") for x in [agreement, agreement_date, agreement_amount]):
        blocks.append(
            f"""
<div class="section">
  <div class="section-title">🧾 Соглашение</div>
  <div class="row"><b>№:</b> {agreement}</div>
  <div class="row"><b>Дата:</b> {agreement_date}</div>
  <div class="row"><b>Сумма:</b> {agreement_amount}</div>
</div>
"""
        )

    if any(x not in ("—", "") for x in [capacity_seats, area_m2, target_deadline]):
        blocks.append(
            f"""
<div class="section">
  <div class="section-title">📦 Параметры</div>
  <div class="row"><b>Мощность:</b> {capacity_seats}</div>
  <div class="row"><b>Площадь:</b> {area_m2}</div>
  <div class="row"><b>Целевой срок:</b> {target_deadline}</div>
</div>
"""
        )

    if any(x not in ("—", "") for x in [psd_cost, designer, expertise, expertise_date, expertise_conclusion]):
        blocks.append(
            f"""
<div class="section">
  <div class="section-title">📑 ПСД / Экспертиза</div>
  <div class="row"><b>Стоимость ПСД:</b> {psd_cost}</div>
  <div class="row"><b>Проектировщик:</b> {designer}</div>
  <div class="row"><b>Экспертиза:</b> {expertise}</div>
  <div class="row"><b>Дата экспертизы:</b> {expertise_date}</div>
  <div class="row"><b>Заключение:</b> {expertise_conclusion}</div>
</div>
"""
        )

    if any(x not in ("—", "") for x in [rns, rns_date, rns_expiry]):
        blocks.append(
            f"""
<div class="section">
  <div class="section-title">🏗️ РНС</div>
  <div class="row"><b>№ РНС:</b> {rns}</div>
  <div class="row"><b>Дата:</b> {rns_date}</div>
  <div class="row"><b>Срок действия:</b> {rns_expiry}</div>
</div>
"""
        )

    if any(x not in ("—", "") for x in [contract, contract_date, contractor, contract_price]):
        blocks.append(
            f"""
<div class="section">
  <div class="section-title">🧱 Контракт</div>
  <div class="row"><b>№:</b> {contract}</div>
  <div class="row"><b>Дата:</b> {contract_date}</div>
  <div class="row"><b>Подрядчик:</b> {contractor}</div>
  <div class="row"><b>Цена:</b> {contract_price}</div>
</div>
"""
        )

    if any(x not in ("—", "") for x in [end_plan, end_fact, readiness, paid]):
        blocks.append(
            f"""
<div class="section">
  <div class="section-title">⏱️ Сроки / Финансы</div>
  <div class="row"><b>Окончание (план):</b> {end_plan}</div>
  <div class="row"><b>Окончание (факт):</b> {end_fact}</div>
  <div class="row"><b>Готовность:</b> {readiness}</div>
  <div class="row"><b>Оплачено:</b> {paid}</div>
</div>
"""
        )

    if not blocks:
        return '<div class="row" style="color:var(--muted)">Нет паспортных данных для отображения.</div>'

    return "\n".join(blocks)


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

    updated_cls, updated_txt = updated_class(row.get("updated_at", ""))

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

    passport_html = render_passport(row)

    st.markdown(
        f"""
<div class="card">
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
    <span class="{status_class(status)}">📌 Статус: {status}</span>
    <span class="{works_class(work_flag)}">🛠️ Работы: {safe_text(work_flag)}</span>
    <span class="{updated_cls}">🕒 Обновлено: {updated_txt}</span>
  </div>

  <div class="card-actions">
    {btn_card}
    {btn_folder}
  </div>

  <div class="hr-soft"></div>

  <details>
    <summary>🧾 Паспорт объекта и контрольные показатели — нажмите, чтобы раскрыть</summary>
    {passport_html}
  </details>
</div>
""",
        unsafe_allow_html=True,
    )


# =============================
# OUTPUT
# =============================
for _, r in filtered.iterrows():
    render_card(r)
