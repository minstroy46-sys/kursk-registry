import base64
import html
import re
from datetime import datetime, date
from pathlib import Path

import pandas as pd
import streamlit as st


# =============================
# CONFIG
# =============================
st.set_page_config(page_title="Реестр объектов", layout="wide")


# =============================
# HELPERS (safe / normalize)
# =============================
def safe_text(v, fallback="—") -> str:
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


def html_escape(v) -> str:
    return html.escape(safe_text(v, fallback="—"))


def norm_col(s: str) -> str:
    if s is None:
        return ""
    s = str(s).strip().lower().replace("ё", "е")
    s = re.sub(r"\s+", " ", s)
    return s


def norm_search(s: str) -> str:
    """Нормализация текста для поиска (рус/лат/цифры), без мусора."""
    s = safe_text(s, fallback="")
    s = s.lower().replace("ё", "е")
    s = re.sub(r"[^\w\s\-\/\.]", " ", s, flags=re.UNICODE)  # убираем лишнюю пунктуацию
    s = re.sub(r"\s+", " ", s).strip()
    return s


def pick_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    cols = {norm_col(c): c for c in df.columns}
    for cand in candidates:
        nc = norm_col(cand)
        if nc in cols:
            return cols[nc]
    for cand in candidates:
        nc = norm_col(cand)
        if not nc:
            continue
        for c in df.columns:
            if nc in norm_col(c):
                return c
    return None


def ensure_url(v) -> str:
    x = safe_text(v, fallback="").strip()
    if not x or x == "—":
        return ""
    if re.match(r"^https?://", x, flags=re.I):
        return x
    return ""


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


def status_accent(status_text: str) -> str:
    s = norm_col(status_text)
    if "останов" in s or "приостанов" in s:
        return "red"
    if "проектир" in s:
        return "yellow"
    if "строитель" in s:
        return "green"
    return "blue"


def works_color(work_flag: str) -> str:
    s = norm_col(work_flag)
    if s in ("—", "", "нет", "не ведутся", "не ведутся.", "не ведутся.."):
        return "red"
    if "не вед" in s or "не выполня" in s or "отсутств" in s:
        return "red"
    if s == "да" or "ведут" in s or "выполня" in s or "идут" in s:
        return "green"
    return "gray"


def try_parse_date(v) -> date | None:
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
    if not s or s.lower() in ("nan", "none", "null", "—"):
        return None

    # serial date (Google/Excel)
    if re.fullmatch(r"\d+(\.\d+)?", s):
        try:
            num = float(s)
            dt = pd.to_datetime(num, unit="D", origin="1899-12-30", errors="coerce")
            if pd.isna(dt):
                return None
            return dt.date()
        except Exception:
            return None

    for fmt in ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass

    try:
        dt = pd.to_datetime(s, errors="coerce", dayfirst=True)
        if pd.isna(dt):
            return None
        return dt.date()
    except Exception:
        return None


def update_color(updated_at_value) -> tuple[str, str]:
    d = try_parse_date(updated_at_value)
    if not d:
        return "gray", "—"
    days = (date.today() - d).days
    if days <= 7:
        return "green", d.strftime("%d.%m.%Y")
    if days <= 14:
        return "yellow", d.strftime("%d.%m.%Y")
    return "red", d.strftime("%d.%m.%Y")


def money_fmt(v) -> str:
    s = safe_text(v, fallback="—")
    if s == "—":
        return s
    try:
        x = str(s).replace(" ", "").replace("\u00A0", "").replace(",", ".")
        x = float(x)
        return f"{x:,.2f}".replace(",", " ").replace(".00", "") + " ₽"
    except Exception:
        return s if ("₽" in s or "руб" in s.lower()) else f"{s} ₽"


def date_fmt(v) -> str:
    d = try_parse_date(v)
    return d.strftime("%d.%m.%Y") if d else "—"


# =============================
# SEARCH: abbreviations + smart matching
# =============================
ABBR = {
    # добавляйте по мере необходимости (ключи — как люди ищут)
    "фап": ["фельдшерско-акушерский пункт", "фельдшерско акушерский пункт"],
    "одкб": ["областная детская клиническая больница", "детская областная клиническая больница"],
    "црб": ["центральная районная больница"],
    "фок": ["физкультурно-оздоровительный комплекс", "физкультурно оздоровительный комплекс"],
    "дк": ["дом культуры", "дворец культуры"],
    "сош": ["средняя общеобразовательная школа", "школа"],
    "оош": ["основная общеобразовательная школа"],
    "доу": ["дошкольное образовательное учреждение", "детский сад"],
    "мкоу": ["муниципальное казенное общеобразовательное учреждение"],
    "мбоу": ["муниципальное бюджетное общеобразовательное учреждение"],
}


def expand_query_tokens(q: str) -> list[str]:
    qn = norm_search(q)
    if not qn:
        return []
    parts = qn.split()
    out = set(parts)

    # если запрос содержит сокращение — добавляем расшифровки
    for p in parts:
        if p in ABBR:
            for full in ABBR[p]:
                out.add(norm_search(full))

    # если запрос написан слитно (например "фап курск") уже распадётся,
    # но на всякий случай добавим исходный qn
    out.add(qn)
    return [x for x in out if x]


def build_row_search_blob(row: pd.Series) -> str:
    base = " ".join(
        [
            safe_text(row.get("name", ""), ""),
            safe_text(row.get("object_type", ""), ""),
            safe_text(row.get("address", ""), ""),
            safe_text(row.get("responsible", ""), ""),
            safe_text(row.get("sector", ""), ""),
            safe_text(row.get("district", ""), ""),
            safe_text(row.get("status", ""), ""),
            safe_text(row.get("issues", ""), ""),
        ]
    )
    blob = norm_search(base)

    # если в названии встречаются сокращения — добавим их расшифровки в blob,
    # чтобы поиск по "ФАП" находил объект, даже если в названии написано полностью (и наоборот)
    words = set(blob.split())
    for abbr, expansions in ABBR.items():
        if abbr in words or re.search(rf"\b{re.escape(abbr)}\b", blob):
            for full in expansions:
                blob += " " + norm_search(full)
        # также если в тексте есть расшифровка — добавим сокращение
        for full in expansions:
            if norm_search(full) in blob:
                blob += " " + abbr

    return blob


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

    if df.empty:
        candidates = [
            "РЕЕСТР_объектов_Курская_область_2025-2028.xlsx",
            "РЕЕСТР_объектов_Курская_область_2025-2028 (18).xlsx",
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
    if df.empty:
        return df

    def col(*cands):
        return pick_col(df, list(cands))

    out = pd.DataFrame()

    out["id"] = df[col("id", "ID")] if col("id", "ID") else ""
    out["sector"] = df[col("sector", "отрасль")] if col("sector", "отрасль") else ""
    out["district"] = df[col("district", "район")] if col("district", "район") else ""
    out["name"] = df[col("name", "object_name", "наименование_объекта", "наименование объекта", "объект")] if col(
        "name", "object_name", "наименование_объекта", "наименование объекта", "объект"
    ) else ""
    out["object_type"] = df[col("object_type", "тип", "вид объекта")] if col("object_type", "тип", "вид объекта") else ""
    out["address"] = df[col("address", "адрес")] if col("address", "адрес") else ""
    out["responsible"] = df[col("responsible", "ответственный")] if col("responsible", "ответственный") else ""
    out["status"] = df[col("status", "статус")] if col("status", "статус") else ""
    out["work_flag"] = df[col("work_flag", "работы", "works_in_progress", "works")] if col(
        "work_flag", "работы", "works_in_progress", "works"
    ) else ""
    out["issues"] = df[col("issues", "проблемы", "проблемные вопросы")] if col(
        "issues", "проблемы", "проблемные вопросы"
    ) else ""
    out["updated_at"] = df[col("updated_at", "last_update", "обновлено", "updated")] if col(
        "updated_at", "last_update", "обновлено", "updated"
    ) else ""

    # URL КАРТОЧКИ — из card_url_text
    out["card_url_text"] = df[col("card_url_text", "card_url", "ссылка_на_карточку_(google)", "ссылка на карточку", "ссылка_на_карточку")] if col(
        "card_url_text", "card_url", "ссылка_на_карточку_(google)", "ссылка на карточку", "ссылка_на_карточку"
    ) else ""

    # Паспортные поля
    out["state_program"] = df[col("state_program", "гп", "государственная программа")] if col(
        "state_program", "гп", "государственная программа"
    ) else ""
    out["federal_project"] = df[col("federal_project", "фп", "федеральный проект")] if col(
        "federal_project", "фп", "федеральный проект"
    ) else ""
    out["regional_program"] = df[col("regional_program", "рп", "региональная программа")] if col(
        "regional_program", "рп", "региональная программа"
    ) else ""

    out["agreement"] = df[col("agreement", "соглашение", "номер соглашения")] if col(
        "agreement", "соглашение", "номер соглашения"
    ) else ""
    out["agreement_date"] = df[col("agreement_date", "дата соглашения")] if col("agreement_date", "дата соглашения") else ""
    out["agreement_amount"] = df[col("agreement_amount", "сумма соглашения")] if col("agreement_amount", "сумма соглашения") else ""

    out["capacity_seats"] = df[col("capacity_seats", "мощность", "мест", "посещений")] if col(
        "capacity_seats", "мощность", "мест", "посещений"
    ) else ""
    out["area_m2"] = df[col("area_m2", "площадь", "м2", "кв.м")] if col("area_m2", "площадь", "м2", "кв.м") else ""
    out["target_deadline"] = df[col("target_deadline", "целевой срок")] if col("target_deadline", "целевой срок") else ""

    out["design"] = df[col("design", "проектирование", "псд")] if col("design", "проектирование", "псд") else ""
    out["psd_cost"] = df[col("psd_cost", "стоимость псд")] if col("psd_cost", "стоимость псд") else ""
    out["designer"] = df[col("designer", "проектировщик")] if col("designer", "проектировщик") else ""

    out["expertise"] = df[col("expertise", "экспертиза")] if col("expertise", "экспертиза") else ""
    out["expertise_conclusion"] = df[col("expertise_conclusion", "заключение экспертизы")] if col(
        "expertise_conclusion", "заключение экспертизы"
    ) else ""
    out["expertise_date"] = df[col("expertise_date", "дата экспертизы")] if col("expertise_date", "дата экспертизы") else ""

    out["rns"] = df[col("rns", "рнс")] if col("rns", "рнс") else ""
    out["rns_date"] = df[col("rns_date", "дата рнс")] if col("rns_date", "дата рнс") else ""
    out["rns_expiry"] = df[col("rns_expiry", "срок действия рнс")] if col("rns_expiry", "срок действия рнс") else ""

    out["contract"] = df[col("contract", "контракт", "номер контракта")] if col("contract", "контракт", "номер контракта") else ""
    out["contract_date"] = df[col("contract_date", "дата контракта")] if col("contract_date", "дата контракта") else ""
    out["contractor"] = df[col("contractor", "подрядчик")] if col("contractor", "подрядчик") else ""
    out["contract_price"] = df[col("contract_price", "цена контракта", "стоимость контракта")] if col(
        "contract_price", "цена контракта", "стоимость контракта"
    ) else ""

    out["end_date_plan"] = df[col("end_date_plan", "окончание план")] if col("end_date_plan", "окончание план") else ""
    out["end_date_fact"] = df[col("end_date_fact", "окончание факт")] if col("end_date_fact", "окончание факт") else ""
    out["readiness"] = df[col("readiness", "готовность")] if col("readiness", "готовность") else ""
    out["paid"] = df[col("paid", "оплачено")] if col("paid", "оплачено") else ""

    for c in out.columns:
        out[c] = out[c].astype(str).replace({"nan": "", "None": "", "null": ""})

    return out


# =============================
# STYLES (modern + compact filters + nicer cards)
# =============================
crest_b64 = read_local_crest_b64()

st.markdown(
    """
<style>
:root{
  --bg: #0b1220;
  --panel: rgba(255,255,255,.06);
  --panel2: rgba(255,255,255,.08);
  --text: rgba(255,255,255,.92);
  --muted: rgba(255,255,255,.72);
  --border: rgba(255,255,255,.12);
  --shadow: rgba(0,0,0,.35);
  --chip: rgba(255,255,255,.07);
  --chipbd: rgba(255,255,255,.12);
  --btnbg: rgba(17,26,43,.85);
  --btnbd: rgba(255,255,255,.16);
}

.block-container { padding-top: 20px !important; max-width: 1200px; }
@media (max-width: 1200px){ .block-container { max-width: 96vw; } }
div[data-testid="stHorizontalBlock"]{ gap: 12px; }

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

html, body, [data-testid="stAppViewContainer"]{
  background: radial-gradient(1200px 600px at 18% 10%, rgba(60,130,255,.12), rgba(0,0,0,0) 60%),
              radial-gradient(900px 540px at 85% 30%, rgba(245,158,11,.10), rgba(0,0,0,0) 55%),
              var(--bg) !important;
}

/* HERO */
.hero-wrap{ width:100%; display:flex; justify-content:center; margin-bottom: 10px; }
.hero{
  width: 100%;
  border-radius: 18px;
  padding: 16px 16px;
  background: radial-gradient(1200px 380px at 22% 30%, rgba(60,130,255,.22), rgba(0,0,0,0) 55%),
              linear-gradient(135deg, #0b2a57, #1b4c8f);
  box-shadow: 0 18px 34px rgba(0,0,0,.22);
  position: relative;
  overflow: hidden;
}
.hero:after{
  content:"";
  position:absolute;
  inset:-44px -140px auto auto;
  width: 540px; height: 340px;
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
  width: 72px; height: 72px;
  border-radius: 14px;
  background: rgba(255,255,255,.10);
  display:flex;
  align-items:center;
  justify-content:center;
  border: 1px solid rgba(255,255,255,.16);
  flex: 0 0 auto;
}
.hero-crest img{
  width: 54px; height: 54px; object-fit: contain;
  filter: drop-shadow(0 6px 10px rgba(0,0,0,.35));
}
.hero-titles{ flex: 1 1 auto; min-width: 0; }
.hero-ministry{
  color: rgba(255,255,255,.95);
  font-weight: 900;
  font-size: 18px;
  line-height: 1.15;
}
.hero-app{
  margin-top: 6px;
  color: rgba(255,255,255,.92);
  font-weight: 800;
  font-size: 15px;
}
.hero-sub{
  margin-top: 6px;
  color: rgba(255,255,255,.78);
  font-size: 13px;
}
@media (max-width: 900px){
  .hero-ministry{ font-size: 15px; }
  .hero-row{ align-items:center; }
}

/* FILTER BAR */
.filter-wrap{
  margin-top: 0px;
  margin-bottom: 14px;
  padding: 12px 12px;
  border-radius: 16px;
  border: 1px solid var(--border);
  background: linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.04));
  box-shadow: 0 10px 20px rgba(0,0,0,.20);
}
.filter-title{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap: 10px;
  margin-bottom: 8px;
  color: var(--text);
}
.filter-title .left{
  font-weight: 900;
  letter-spacing: .2px;
}
.filter-title .right{
  color: var(--muted);
  font-size: 12.5px;
  font-weight: 700;
}

/* Streamlit inputs styling (select/text) */
div[data-testid="stSelectbox"] > div{
  border-radius: 14px !important;
}
div[data-testid="stTextInput"] > div{
  border-radius: 14px !important;
}
div[data-baseweb="select"] > div{
  background: rgba(255,255,255,.06) !important;
  border: 1px solid rgba(255,255,255,.12) !important;
}
div[data-baseweb="input"]{
  background: rgba(255,255,255,.06) !important;
  border: 1px solid rgba(255,255,255,.12) !important;
}
div[data-baseweb="input"] input{
  color: var(--text) !important;
}
div[data-baseweb="select"] span{
  color: var(--text) !important;
}
label{
  color: rgba(255,255,255,.78) !important;
  font-weight: 800 !important;
}

/* CARD */
.card{
  border-radius: 18px;
  padding: 16px;
  margin-bottom: 14px;
  border: 1px solid var(--border);
  background:
    radial-gradient(900px 320px at 20% 10%, rgba(60,130,255,.10), rgba(0,0,0,0) 55%),
    radial-gradient(700px 280px at 90% 20%, rgba(245,158,11,.07), rgba(0,0,0,0) 55%),
    linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.04));
  box-shadow: 0 14px 26px rgba(0,0,0,.28);
  position: relative;
  overflow: hidden;
}

.card[data-accent="green"]{
  border-color: rgba(34,197,94,.36);
  box-shadow:
    0 14px 26px rgba(0,0,0,.28),
    -12px 0 28px rgba(34,197,94,.14),
    inset 8px 0 0 rgba(34,197,94,.55);
}
.card[data-accent="yellow"]{
  border-color: rgba(245,158,11,.38);
  box-shadow:
    0 14px 26px rgba(0,0,0,.28),
    -12px 0 28px rgba(245,158,11,.14),
    inset 8px 0 0 rgba(245,158,11,.55);
}
.card[data-accent="red"]{
  border-color: rgba(239,68,68,.38);
  box-shadow:
    0 14px 26px rgba(0,0,0,.28),
    -12px 0 28px rgba(239,68,68,.14),
    inset 8px 0 0 rgba(239,68,68,.55);
}
.card[data-accent="blue"]{
  border-color: rgba(59,130,246,.32);
  box-shadow:
    0 14px 26px rgba(0,0,0,.28),
    -12px 0 28px rgba(59,130,246,.12),
    inset 8px 0 0 rgba(59,130,246,.48);
}

.card-title{
  font-size: 19px;
  line-height: 1.15;
  font-weight: 900;
  margin: 0 0 10px 0;
  color: var(--text);
}
.card-subchips{
  display:flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: -2px;
  margin-bottom: 10px;
}
.chip{
  display:inline-flex;
  align-items:center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid var(--chipbd);
  background: var(--chip);
  font-size: 13px;
  color: var(--text);
  opacity: .95;
}

.card-grid{
  display:grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 18px;
  margin-top: 6px;
}
.card-item{
  font-size: 14px;
  color: var(--text);
}
.card-item b{ color: var(--text); }

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
  border: 1px solid var(--chipbd);
  background: var(--chip);
  font-size: 13px;
  color: var(--text);
  font-weight: 800;
}
.tag-gray{ opacity: .92; }
.tag-green{ background: rgba(34,197,94,.10); border-color: rgba(34,197,94,.20); }
.tag-yellow{ background: rgba(245,158,11,.12); border-color: rgba(245,158,11,.22); }
.tag-red{ background: rgba(239,68,68,.10); border-color: rgba(239,68,68,.20); }

.card-actions{ margin-top: 12px; }
.a-btn{
  width: 100%;
  display:flex;
  justify-content:center;
  align-items:center;
  gap: 8px;
  padding: 11px 12px;
  border-radius: 14px;
  border: 1px solid var(--btnbd);
  background: linear-gradient(180deg, rgba(255,255,255,.08), rgba(255,255,255,.04));
  text-decoration:none !important;
  color: var(--text) !important;
  font-weight: 900;
  font-size: 14px;
  transition: .12s ease-in-out;
}
.a-btn:hover{
  transform: translateY(-1px);
  box-shadow: 0 12px 20px rgba(0,0,0,.25);
}
.a-btn.disabled{
  opacity: .45;
  pointer-events:none;
}

/* Passport collapsible INSIDE card */
.details{
  margin-top: 12px;
  border-radius: 14px;
  border: 1px solid rgba(255,255,255,.12);
  background: rgba(255,255,255,.04);
  overflow: hidden;
}
.details summary{
  cursor: pointer;
  padding: 12px 12px;
  font-weight: 900;
  color: var(--text);
  list-style: none;
}
.details summary::-webkit-details-marker{ display:none; }
.details .content{
  padding: 12px 12px 14px 12px;
  border-top: 1px dashed rgba(255,255,255,.14);
}

.section{
  margin-top: 10px;
  padding: 10px 10px;
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,.12);
  background: rgba(255,255,255,.03);
}
.section-title{
  font-weight: 900;
  color: var(--text);
  margin-bottom: 8px;
  font-size: 13.5px;
}
.row{
  display:flex;
  gap: 10px;
  flex-wrap: wrap;
  color: var(--text);
  font-size: 13.5px;
  line-height: 1.35;
}
.row b{ color: var(--text); }
.muted{ color: var(--muted); }

.issue-box{
  border: 1px solid rgba(239,68,68,.22);
  background: rgba(239,68,68,.08);
  color: var(--text);
  padding: 10px 12px;
  border-radius: 12px;
  font-size: 13.5px;
}

@media (max-width: 900px){
  .card-grid{ grid-template-columns: 1fr; }
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
    else '<span style="color:rgba(255,255,255,.8);font-weight:900;font-size:12px;">герб</span>'
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
    st.error("Данные не загрузились. Проверьте CSV_URL в Secrets или наличие .xlsx в репозитории.")
    st.stop()

df = normalize_schema(raw)

# подготовим поле для быстрого поиска (кешируем вычисление в памяти)
if "search_blob" not in df.columns:
    df["search_blob"] = df.apply(build_row_search_blob, axis=1)

# списки фильтров
sectors = sorted([x for x in df["sector"].unique().tolist() if str(x).strip()])
districts = sorted([x for x in df["district"].unique().tolist() if str(x).strip()])
statuses = sorted([x for x in df["status"].unique().tolist() if str(x).strip()])

sectors = move_prochie_to_bottom(sectors)

sectors = ["Все"] + sectors
districts = ["Все"] + districts
statuses = ["Все"] + statuses


# =============================
# FILTER BAR (ничего между шапкой и фильтрами)
# =============================
st.markdown(
    """
<div class="filter-wrap">
  <div class="filter-title">
    <div class="left">🔎 Поиск и фильтры</div>
    <div class="right">Советы: ищите по названию, адресу, ответственному или сокращениям (ФАП, ОДКБ и др.)</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# сами виджеты ниже (они должны визуально "лежать" в этом блоке)
# чтобы они выглядели частью блока — просто размещаем сразу после
c1, c2, c3, c4 = st.columns([1.0, 1.0, 1.0, 1.35])
with c1:
    sector_sel = st.selectbox("Отрасль", sectors, index=0, key="f_sector")
with c2:
    district_sel = st.selectbox("Район", districts, index=0, key="f_district")
with c3:
    status_sel = st.selectbox("Статус", statuses, index=0, key="f_status")
with c4:
    q = st.text_input("Поиск", value="", key="f_search", placeholder="Например: ФАП, ОДКБ, школа, Курский район, Иванов…").strip()

# (убираем любые разделители/подписи между шапкой и фильтрами — как вы просили)


# =============================
# FILTERING + SMART SEARCH
# =============================
filtered = df.copy()

if sector_sel != "Все":
    filtered = filtered[filtered["sector"].astype(str) == str(sector_sel)]
if district_sel != "Все":
    filtered = filtered[filtered["district"].astype(str) == str(district_sel)]
if status_sel != "Все":
    filtered = filtered[filtered["status"].astype(str) == str(status_sel)]

qn = norm_search(q)
if qn:
    tokens = expand_query_tokens(qn)

    def match_blob(blob: str) -> bool:
        # логика: все токены должны встретиться (AND), но токен может быть фразой
        # это повышает точность и при этом хорошо работает для сокращений
        for t in tokens:
            if t and t not in blob:
                return False
        return True

    filtered = filtered[filtered["search_blob"].apply(match_blob)]

# компактный счетчик (не вставляем "divider" — но показываем аккуратно)
st.markdown(
    f'<div style="margin:-6px 0 10px 2px; color:rgba(255,255,255,.70); font-weight:800; font-size:13px;">'
    f'Показано: {len(filtered)} из {len(df)}'
    f"</div>",
    unsafe_allow_html=True,
)


# =============================
# CARD RENDER (passport inside same contour)
# =============================
def tag_class_from_color(c: str) -> str:
    if c == "green":
        return "tag-green"
    if c == "yellow":
        return "tag-yellow"
    if c == "red":
        return "tag-red"
    return "tag-gray"


def render_row_kv(label: str, value: str) -> str:
    return f'<div class="row"><b>{html.escape(label)}:</b> {html_escape(value)}</div>'


def render_card(row: pd.Series):
    title = html_escape(row.get("name", "Объект"))
    sector = html_escape(row.get("sector", "—"))
    district = html_escape(row.get("district", "—"))
    address = html_escape(row.get("address", "—"))
    responsible = html_escape(row.get("responsible", "—"))

    status = safe_text(row.get("status", ""), "—")
    work_flag = safe_text(row.get("work_flag", ""), "—")
    issues = safe_text(row.get("issues", ""), "—")

    status_h = html.escape(status)
    work_h = html.escape(work_flag)

    card_url = ensure_url(row.get("card_url_text", ""))

    accent = status_accent(status)
    w_col = works_color(work_flag)
    u_col, u_txt = update_color(row.get("updated_at", ""))

    s_tag = tag_class_from_color(accent)
    w_tag = tag_class_from_color(w_col)
    u_tag = tag_class_from_color(u_col)

    btn_card = (
        f'<a class="a-btn" href="{html.escape(card_url)}" target="_blank" rel="noopener noreferrer">📄 Открыть карточку</a>'
        if card_url
        else '<span class="a-btn disabled">📄 Открыть карточку</span>'
    )

    # Паспорт внутри карточки (один контур)
    issues_html = (
        f'<div class="issue-box">{html_escape(issues)}</div>' if issues != "—" else '<div class="row"><span class="muted">—</span></div>'
    )

    passport_html = f"""
<details class="details">
  <summary>📋 Паспорт объекта и контрольные показатели</summary>
  <div class="content">

    <div class="section">
      <div class="section-title">⚠️ Проблемные вопросы</div>
      {issues_html}
    </div>

    <div class="section">
      <div class="section-title">🏛️ Программы</div>
      {render_row_kv("ГП/СП", row.get("state_program", ""))}
      {render_row_kv("ФП", row.get("federal_project", ""))}
      {render_row_kv("РП", row.get("regional_program", ""))}
    </div>

    <div class="section">
      <div class="section-title">🧾 Соглашение</div>
      {render_row_kv("№", row.get("agreement", ""))}
      {render_row_kv("Дата", date_fmt(row.get("agreement_date", "")))}
      {render_row_kv("Сумма", money_fmt(row.get("agreement_amount", "")))}
    </div>

    <div class="section">
      <div class="section-title">📦 Параметры</div>
      {render_row_kv("Мощность", row.get("capacity_seats", ""))}
      {render_row_kv("Площадь", row.get("area_m2", ""))}
      {render_row_kv("Целевой срок", date_fmt(row.get("target_deadline", "")))}
    </div>

    <div class="section">
      <div class="section-title">🗂️ ПСД / Экспертиза</div>
      {render_row_kv("ПСД", row.get("design", ""))}
      {render_row_kv("Стоимость ПСД", money_fmt(row.get("psd_cost", "")))}
      {render_row_kv("Проектировщик", row.get("designer", ""))}
      {render_row_kv("Экспертиза", row.get("expertise", ""))}
      {render_row_kv("Дата экспертизы", date_fmt(row.get("expertise_date", "")))}
      {render_row_kv("Заключение", row.get("expertise_conclusion", ""))}
    </div>

    <div class="section">
      <div class="section-title">🏗️ РНС</div>
      {render_row_kv("№ РНС", row.get("rns", ""))}
      {render_row_kv("Дата", date_fmt(row.get("rns_date", "")))}
      {render_row_kv("Срок действия", date_fmt(row.get("rns_expiry", "")))}
    </div>

    <div class="section">
      <div class="section-title">🧩 Контракт</div>
      {render_row_kv("№", row.get("contract", ""))}
      {render_row_kv("Дата", date_fmt(row.get("contract_date", "")))}
      {render_row_kv("Подрядчик", row.get("contractor", ""))}
      {render_row_kv("Цена", money_fmt(row.get("contract_price", "")))}
    </div>

    <div class="section">
      <div class="section-title">⏳ Сроки / финансы</div>
      {render_row_kv("Окончание (план)", date_fmt(row.get("end_date_plan", "")))}
      {render_row_kv("Окончание (факт)", date_fmt(row.get("end_date_fact", "")))}
      {render_row_kv("Готовность", row.get("readiness", ""))}
      {render_row_kv("Оплачено", money_fmt(row.get("paid", "")))}
    </div>

  </div>
</details>
"""

    st.markdown(
        f"""
<div class="card" data-accent="{html.escape(accent)}">
  <div class="card-title">{title}</div>

  <div class="card-subchips">
    <span class="chip">🏷️ {sector}</span>
    <span class="chip">📍 {district}</span>
  </div>

  <div class="card-grid">
    <div class="card-item">🗺️ <b>Адрес:</b> {address}</div>
    <div class="card-item">👤 <b>Ответственный:</b> {responsible}</div>
  </div>

  <div class="card-tags">
    <span class="tag {s_tag}">📌 Статус: {status_h}</span>
    <span class="tag {w_tag}">🛠️ Работы: {work_h}</span>
    <span class="tag {u_tag}">⏱️ Обновлено: {html.escape(u_txt)}</span>
  </div>

  <div class="card-actions">
    {btn_card}
  </div>

  {passport_html}
</div>
""",
        unsafe_allow_html=True,
    )


# =============================
# OUTPUT
# =============================
for _, r in filtered.iterrows():
    render_card(r)
