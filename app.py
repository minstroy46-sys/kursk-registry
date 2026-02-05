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
# HELPERS
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


def esc(v) -> str:
    return html.escape(safe_text(v, fallback="—"))


def norm_col(s: str) -> str:
    if s is None:
        return ""
    s = str(s).strip().lower().replace("ё", "е")
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


def num_fmt(v) -> str:
    s = safe_text(v, fallback="—")
    if s == "—":
        return s
    try:
        x = str(s).replace(" ", "").replace("\u00A0", "").replace(",", ".")
        x = float(x)
        if x.is_integer():
            return f"{int(x):,}".replace(",", " ")
        return f"{x:,.2f}".replace(",", " ")
    except Exception:
        return s


def readiness_fmt(v) -> str:
    """
    Нормализует готовность:
    - 0.38 / 0,38 -> 38%
    - 38 -> 38%
    - 38% -> 38%
    - пусто -> —
    """
    s = safe_text(v, fallback="—")
    if s == "—":
        return "—"
    s0 = str(s).strip()
    if not s0:
        return "—"
    if "%" in s0:
        return s0.replace(" ", "")

    # пробуем число
    try:
        x = str(s0).replace(" ", "").replace("\u00A0", "").replace(",", ".")
        x = float(x)
        if 0 <= x <= 1:
            p = x * 100
        else:
            p = x

        # красивое форматирование
        if abs(p - round(p)) < 1e-9:
            return f"{int(round(p))}%"
        # одна цифра после запятой
        return f"{p:.1f}".replace(".", ",") + "%"
    except Exception:
        return s0


def norm_search(s: str) -> str:
    s = safe_text(s, fallback="")
    s = s.lower().replace("ё", "е")
    s = re.sub(r"[^\w\s\-\/\.]", " ", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# =============================
# SEARCH: abbreviations
# =============================
ABBR = {
    "фап": ["фельдшерско-акушерский пункт", "фельдшерско акушерский пункт"],
    "одкб": ["областная детская клиническая больница", "детская областная клиническая больница"],
    "црб": ["центральная районная больница"],
    "фок": ["физкультурно-оздоровительный комплекс", "физкультурно оздоровительный комплекс"],
    "дк": ["дом культуры", "дворец культуры"],
    "сош": ["средняя общеобразовательная школа", "школа"],
    "оош": ["основная общеобразовательная школа"],
    "доу": ["дошкольное образовательное учреждение", "детский сад"],
}


def expand_query_tokens(q: str) -> list[str]:
    qn = norm_search(q)
    if not qn:
        return []
    parts = qn.split()
    out = set(parts)
    out.add(qn)
    for p in parts:
        if p in ABBR:
            for full in ABBR[p]:
                out.add(norm_search(full))
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

    for abbr, expansions in ABBR.items():
        for full in expansions:
            full_n = norm_search(full)
            if full_n and full_n in blob:
                blob += " " + abbr
        if re.search(rf"\b{re.escape(abbr)}\b", blob):
            for full in expansions:
                blob += " " + norm_search(full)

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

    out["card_url_text"] = df[
        col("card_url_text", "card_url", "ссылка_на_карточку_(google)", "ссылка на карточку", "ссылка_на_карточку")
    ] if col("card_url_text", "card_url", "ссылка_на_карточку_(google)", "ссылка на карточку", "ссылка_на_карточку") else ""

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

    out["contract"] = df[col("contract", "контракт", "номер контракта")] if col(
        "contract", "контракт", "номер контракта"
    ) else ""
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
# STYLES
# =============================
crest_b64 = read_local_crest_b64()

st.markdown(
    """
<style>
:root{
  --bg: #f7f8fb;
  --text: #0f172a;
  --muted: rgba(15,23,42,.72);
  --border: rgba(15,23,42,.10);
  --shadow: rgba(0,0,0,.06);
  --chip-bg: rgba(15,23,42,.05);
  --chip-bd: rgba(15,23,42,.10);
  --btn-bg: rgba(255,255,255,.95);
  --btn-bd: rgba(15,23,42,.12);
  --hr: rgba(15,23,42,.12);

  /* Новый мягкий фон секций (не белый) */
  --soft: linear-gradient(180deg, rgba(250,252,255,.96), rgba(244,247,255,.96));
  --soft2: linear-gradient(180deg, rgba(255,255,255,.90), rgba(246,248,255,.92));
}

.block-container { padding-top: 24px !important; max-width: 1200px; }
@media (max-width: 1200px){ .block-container { max-width: 96vw; } }
div[data-testid="stHorizontalBlock"]{ gap: 14px; }

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

html, body, [data-testid="stAppViewContainer"]{
  background: var(--bg) !important;
}

/* HERO */
.hero-wrap{ width:100%; display:flex; justify-content:center; margin-bottom: 10px; }
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

/* CARD */
.card{
  background:
    radial-gradient(900px 320px at 14% 12%, rgba(59,130,246,.10), rgba(0,0,0,0) 55%),
    radial-gradient(700px 260px at 92% 18%, rgba(16,185,129,.08), rgba(0,0,0,0) 55%),
    linear-gradient(180deg, #ffffff, #f4f8ff);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 16px;
  box-shadow: 0 10px 22px var(--shadow);
  margin-bottom: 14px;
  position: relative;
}

.card[data-accent="green"]{
  border-color: rgba(34,197,94,.35);
  box-shadow: 0 10px 22px var(--shadow),
              inset 12px 0 0 rgba(34,197,94,.55),
              0 0 18px rgba(34,197,94,.14);
}
.card[data-accent="yellow"]{
  border-color: rgba(245,158,11,.38);
  box-shadow: 0 10px 22px var(--shadow),
              inset 12px 0 0 rgba(245,158,11,.58),
              0 0 18px rgba(245,158,11,.14);
}
.card[data-accent="red"]{
  border-color: rgba(239,68,68,.38);
  box-shadow: 0 10px 22px var(--shadow),
              inset 12px 0 0 rgba(239,68,68,.58),
              0 0 18px rgba(239,68,68,.14);
}
.card[data-accent="blue"]{
  border-color: rgba(59,130,246,.32);
  box-shadow: 0 10px 22px var(--shadow),
              inset 12px 0 0 rgba(59,130,246,.52),
              0 0 18px rgba(59,130,246,.12);
}

.card-title{ font-size: 20px; line-height: 1.15; font-weight: 900; margin: 0 0 10px 0; color: var(--text); }
.card-subchips{ display:flex; gap: 8px; flex-wrap: wrap; margin-top: -2px; margin-bottom: 10px; }
.chip{
  display:inline-flex; align-items:center; gap: 8px;
  padding: 6px 10px; border-radius: 999px;
  border: 1px solid var(--chip-bd);
  background: var(--chip-bg);
  font-size: 13px; color: var(--text);
}

.card-grid{ display:grid; grid-template-columns: 1fr 1fr; gap: 8px 18px; margin-top: 6px; }
.card-item{ font-size: 14px; color: var(--text); }
.card-item b{ color: var(--text); }

.card-tags{ display:flex; gap: 10px; flex-wrap: wrap; margin-top: 10px; }
.tag{
  display:inline-flex; align-items:center; gap: 8px;
  padding: 6px 10px; border-radius: 999px;
  border: 1px solid var(--chip-bd);
  background: var(--chip-bg);
  font-size: 13px; color: var(--text); font-weight: 800;
}
.tag-gray{ opacity: .92; }
.tag-gre
