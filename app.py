import base64
import html
import re
from datetime import datetime, date
from pathlib import Path
from textwrap import dedent

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


def readiness_fmt(v) -> str:
    s = safe_text(v, fallback="—")
    if s == "—":
        return "—"
    s0 = str(s).strip()
    if not s0:
        return "—"
    if "%" in s0:
        return s0.replace(" ", "")

    try:
        x = str(s0).replace(" ", "").replace("\u00A0", "").replace(",", ".")
        x = float(x)
        p = x * 100 if 0 <= x <= 1 else x
        if abs(p - round(p)) < 1e-9:
            return f"{int(round(p))}%"
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
@st.cache_data(show_spinner=False, ttl=120)
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
    dedent(
        """
        <style>
        :root{
          --text: #0f172a;
          --muted: rgba(15,23,42,.70);
          --page: radial-gradient(1100px 520px at 24% 18%, rgba(59,130,246,.08), rgba(0,0,0,0) 56%),
                  radial-gradient(900px 480px at 78% 22%, rgba(16,185,129,.07), rgba(0,0,0,0) 56%),
                  linear-gradient(180deg, #f6f8fc, #eef2f7);
          --border: rgba(15,23,42,.14);
          --border-strong: rgba(15,23,42,.20);
          --shadow: rgba(0,0,0,.07);

          --chip-bg: rgba(15,23,42,.05);
          --chip-bd: rgba(15,23,42,.10);

          --soft: linear-gradient(180deg, rgba(255,255,255,.98), rgba(245,248,255,.98));
          --soft2: linear-gradient(180deg, rgba(255,255,255,.96), rgba(246,248,255,.98));

          --btn-bg: rgba(255,255,255,.96);
          --btn-bd: rgba(15,23,42,.18);
          --btn-shadow: rgba(0,0,0,.08);

          --pad: 20px;
        }

        .block-container { padding-top: 24px !important; max-width: 1200px; }
        @media (max-width: 1200px){ .block-container { max-width: 96vw; } }
        div[data-testid="stHorizontalBlock"]{ gap: 14px; }

        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}

        html, body, [data-testid="stAppViewContainer"]{
          background: var(--page) !important;
        }

        html, body, [data-testid="stAppViewContainer"], [data-testid="stAppViewContainer"] *{ color: var(--text); }
        p, span, li, div, small { color: var(--text); }
        .stCaption, [data-testid="stCaptionContainer"] * { color: var(--muted) !important; }
        label, [data-testid="stWidgetLabel"] *{ color: var(--text) !important; opacity: 1 !important; }
        h1,h2,h3,h4,h5,h6{ color: var(--text) !important; }

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
        .hero-ministry{ color: rgba(255,255,255,.95) !important; font-weight: 900; font-size: 20px; line-height: 1.15; }
        .hero-app{ margin-top: 6px; color: rgba(255,255,255,.92) !important; font-weight: 800; font-size: 16px; }
        .hero-sub{ margin-top: 6px; color: rgba(255,255,255,.78) !important; font-size: 13px; }
        @media (max-width: 900px){
          .hero-ministry{ font-size: 16px; }
          .hero-row{ align-items:center; }
        }

        /* Панели фильтров */
        div[data-testid="stSelectbox"], div[data-testid="stTextInput"]{
          background: linear-gradient(180deg, rgba(255,255,255,.86), rgba(245,248,255,.94));
          border: 1px solid rgba(15,23,42,.16);
          border-radius: 16px;
          padding: 10px 10px 6px 10px;
          box-shadow: 0 14px 26px rgba(0,0,0,.08);
        }
        div[data-testid="stTextInput"] input,
        div[data-testid="stSelectbox"] div[role="combobox"]{
          border: 1px solid var(--border-strong) !important;
          box-shadow: 0 10px 18px rgba(0,0,0,.06) !important;
          background: rgba(255,255,255,.96) !important;
          border-radius: 12px !important;
        }

        /* Карточка */
        .card{
          background:
            radial-gradient(900px 320px at 14% 12%, rgba(59,130,246,.08), rgba(0,0,0,0) 55%),
            radial-gradient(700px 260px at 92% 18%, rgba(16,185,129,.06), rgba(0,0,0,0) 55%),
            linear-gradient(180deg, #ffffff, #f4f8ff);
          border: 1px solid var(--border);
          border-radius: 18px;
          padding: var(--pad);
          box-shadow: 0 12px 26px var(--shadow);
          margin-bottom: 16px;
          position: relative;
          overflow: hidden;
        }
        .card[data-accent="green"]{
          border-color: rgba(34,197,94,.32);
          box-shadow: 0 12px 26px var(--shadow), inset 12px 0 0 rgba(34,197,94,.52);
        }
        .card[data-accent="yellow"]{
          border-color: rgba(245,158,11,.34);
          box-shadow: 0 12px 26px var(--shadow), inset 12px 0 0 rgba(245,158,11,.56);
        }
        .card[data-accent="red"]{
          border-color: rgba(239,68,68,.34);
          box-shadow: 0 12px 26px var(--shadow), inset 12px 0 0 rgba(239,68,68,.56);
        }
        .card[data-accent="blue"]{
          border-color: rgba(59,130,246,.30);
          box-shadow: 0 12px 26px var(--shadow), inset 12px 0 0 rgba(59,130,246,.50);
        }

        .card-head{ display:flex; flex-direction:column; gap: 10px; }
        .card-title{ font-size: 20px; line-height: 1.18; font-weight: 950; margin: 0; color: var(--text) !important; }
        .card-subchips{ display:flex; gap: 8px; flex-wrap: wrap; margin-top: -4px; }
        .chip{
          display:inline-flex; align-items:center; gap: 8px;
          padding: 6px 10px;
          border-radius: 999px;
          border: 1px solid var(--chip-bd);
          background: var(--chip-bg);
          font-size: 13px;
          color: var(--text) !important;
          font-weight: 800;
        }

        /* Ровные строки адрес/ответственный */
        .info-grid{
          margin-top: 2px;
          display:grid;
          grid-template-columns: 1fr 1fr;
          gap: 10px 14px;
        }
        .info-item{
          display:flex;
          gap: 10px;
          align-items:flex-start;
          padding: 10px 12px;
          border-radius: 14px;
          border: 1px solid rgba(15,23,42,.12);
          background: linear-gradient(180deg, rgba(255,255,255,.92), rgba(245,248,255,.92));
        }
        .ico{
          width: 30px; height: 30px;
          border-radius: 10px;
          display:flex;
          align-items:center;
          justify-content:center;
          border: 1px solid rgba(15,23,42,.10);
          background: rgba(15,23,42,.05);
          font-size: 16px;
          flex: 0 0 auto;
        }
        .itxt{ min-width: 0; }
        .ilbl{ font-size: 12px; font-weight: 900; color: var(--muted) !important; letter-spacing: .2px; }
        .ival{
          margin-top: 2px;
          font-size: 14px;
          font-weight: 800;
          line-height: 1.25;
          word-break: break-word;
          overflow-wrap: anywhere;
        }

        /* Тэги */
        .card-tags{ display:flex; gap: 10px; flex-wrap: wrap; margin-top: 12px; }
        .tag{
          display:inline-flex; align-items:center; gap: 8px;
          padding: 7px 11px;
          border-radius: 999px;
          border: 1px solid var(--chip-bd);
          background: var(--chip-bg);
          font-size: 13px;
          color: var(--text) !important;
          font-weight: 900;
        }
        .tag-gray{ opacity: .92; }
        .tag-green{ background: rgba(34,197,94,.12); border-color: rgba(34,197,94,.22); }
        .tag-yellow{ background: rgba(245,158,11,.14); border-color: rgba(245,158,11,.25); }
        .tag-red{ background: rgba(239,68,68,.12); border-color: rgba(239,68,68,.22); }

        /* Кнопка */
        .a-btn{
          width: 100%;
          display:flex; justify-content:center; align-items:center; gap: 8px;
          padding: 11px 12px;
          border-radius: 14px;
          border: 1px solid var(--btn-bd);
          background: var(--btn-bg);
          text-decoration:none !important;
          color: var(--text) !important;
          font-weight: 950;
          font-size: 14px;
          transition: .12s ease-in-out;
          margin-top: 14px;
          box-shadow: 0 10px 18px var(--btn-shadow);
        }
        .a-btn:hover{ transform: translateY(-1px); box-shadow: 0 14px 22px rgba(0,0,0,.10); }
        .a-btn.disabled{ opacity: .45; pointer-events:none; }

        /* Паспорт внутри общего контура */
        .passport{ margin-top: 14px; border-top: 1px solid rgba(15,23,42,.12); padding-top: 10px; }
        .passport-toggle{ position:absolute; opacity:0; pointer-events:none; }
        .passport-summary{
          cursor: pointer;
          padding: 10px 12px;
          border-radius: 14px;
          border: 1px solid rgba(15,23,42,.12);
          background: linear-gradient(180deg, rgba(255,255,255,.88), rgba(245,248,255,.92));
          font-weight: 950;
          display:flex; align-items:center; gap: 10px;
          user-select: none;
        }
        .passport-summary:before{ content:"▸"; font-weight: 950; opacity:.75; }
        .passport-toggle:checked + .passport-summary:before{ content:"▾"; }
        .passport-body{
          display:none;
          margin-top: 10px;
          padding: 12px;
          border-radius: 14px;
          border: 1px solid rgba(15,23,42,.12);
          background: var(--soft2);
        }
        .passport-toggle:checked ~ .passport-body{ display:block; }

        .passport-grid{ display:grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        .section-wide{ grid-column: 1 / -1; }
        .section{
          padding: 12px;
          border-radius: 14px;
          border: 1px solid rgba(15,23,42,.12);
          background: var(--soft);
        }
        .section-title{ font-weight: 950; margin-bottom: 8px; font-size: 14px; }
        .row{
          display:flex; gap: 10px; flex-wrap: wrap;
          font-size: 13.5px; line-height: 1.35;
          word-break: break-word; overflow-wrap: anywhere;
        }
        .row .muted{ color: var(--muted) !important; }
        .issue-box{
          border: 1px solid rgba(239,68,68,.22);
          background: rgba(239,68,68,.07);
          padding: 10px 12px;
          border-radius: 12px;
          font-size: 13.5px;
          line-height: 1.35;
          word-break: break-word;
          overflow-wrap: anywhere;
        }

        .passport-close{ display:none; justify-content:center; margin-top: 10px; }
        .passport-toggle:checked ~ .passport-close{ display:flex; }
        .passport-close-btn{
          width: 34px; height: 34px;
          border-radius: 999px;
          border: 1px solid rgba(15,23,42,.18);
          background: rgba(255,255,255,.92);
          font-weight: 950;
          display:flex; align-items:center; justify-content:center;
          box-shadow: 0 10px 18px rgba(0,0,0,.08);
          cursor: pointer;
          user-select: none;
        }
        .passport-close-btn:hover{
          transform: translateY(-1px);
          box-shadow: 0 14px 22px rgba(0,0,0,.10);
        }

        @media (max-width: 900px){
          .card-title{ font-size: 18px; }
          .info-grid{ grid-template-columns: 1fr; }
          .passport-grid{ grid-template-columns: 1fr; }
        }
        </style>
        """
    ),
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
    dedent(
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
        """
    ),
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
            pwd = st.text_input("Пароль", type="password", placeholder="")
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
    st.error(
        "Данные не загрузились (реестр пустой). Проверьте CSV_URL в Secrets "
        "или наличие .xlsx в репозитории."
    )
    st.stop()

df = normalize_schema(raw)
df["search_blob"] = df.apply(build_row_search_blob, axis=1)

sectors = sorted([x for x in df["sector"].unique().tolist() if str(x).strip()])
districts = sorted([x for x in df["district"].unique().tolist() if str(x).strip()])
statuses = sorted([x for x in df["status"].unique().tolist() if str(x).strip()])

sectors = move_prochie_to_bottom(sectors)

sectors = ["Все"] + sectors
districts = ["Все"] + districts
statuses = ["Все"] + statuses


# =============================
# FILTERS + SEARCH
# =============================
c1, c2, c3, c4 = st.columns([1.0, 1.0, 1.0, 1.35])
with c1:
    sector_sel = st.selectbox("🏷️ Отрасль", sectors, index=0, key="f_sector")
with c2:
    district_sel = st.selectbox("📍 Район", districts, index=0, key="f_district")
with c3:
    status_sel = st.selectbox("📌 Статус", statuses, index=0, key="f_status")
with c4:
    q = st.text_input("🔎 Поиск", value="", key="f_search", placeholder="").strip()


# =============================
# FILTER APPLY
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
        for t in tokens:
            if t and t not in blob:
                return False
        return True

    filtered = filtered[filtered["search_blob"].apply(match_blob)]

st.caption(f"Показано объектов: {len(filtered)} из {len(df)}")
st.divider()


# =============================
# CARD RENDER (HTML)
# =============================
def tag_class(color: str) -> str:
    if color == "green":
        return "tag-green"
    if color == "yellow":
        return "tag-yellow"
    if color == "red":
        return "tag-red"
    return "tag-gray"


def kv_html(label: str, value) -> str:
    return f'<div class="row"><b>{esc(label)}:</b> {esc(value)}</div>'


def section_html(title: str, inner_html: str, wide: bool = False) -> str:
    cls = "section section-wide" if wide else "section"
    return f'<div class="{cls}"><div class="section-title">{esc(title)}</div>{inner_html}</div>'


def render_card(row: pd.Series):
    title_txt = safe_text(row.get("name", "Объект"))
    title = esc(title_txt)
    sector = esc(row.get("sector", "—"))
    district = esc(row.get("district", "—"))
    address = esc(row.get("address", "—"))
    responsible = esc(row.get("responsible", "—"))

    status = safe_text(row.get("status", ""), "—")
    work_flag = safe_text(row.get("work_flag", ""), "—")
    issues = safe_text(row.get("issues", ""), "—")

    accent = status_accent(status)
    w_col = works_color(work_flag)
    u_col, u_txt = update_color(row.get("updated_at", ""))

    s_cls = tag_class(accent)
    w_cls = tag_class(w_col)
    u_cls = tag_class(u_col)

    card_url = ensure_url(row.get("card_url_text", ""))

    btn_html = (
        f'<a class="a-btn" href="{esc(card_url)}" target="_blank" rel="noopener noreferrer">📄 Открыть карточку</a>'
        if card_url
        else '<span class="a-btn disabled">📄 Открыть карточку</span>'
    )

    issues_html = (
        f'<div class="issue-box">{esc(issues)}</div>'
        if issues != "—"
        else '<div class="row"><span class="muted">—</span></div>'
    )

    passport_blocks = []
    passport_blocks.append(section_html("⚠️ Проблемные вопросы", issues_html, wide=True))

    prog = (
        kv_html("ГП/СП", row.get("state_program", "—"))
        + kv_html("ФП", row.get("federal_project", "—"))
        + kv_html("РП", row.get("regional_program", "—"))
    )
    passport_blocks.append(section_html("🏛️ Программы", prog))

    agr = (
        kv_html("№", row.get("agreement", "—"))
        + kv_html("Дата", date_fmt(row.get("agreement_date", "")))
        + kv_html("Сумма", money_fmt(row.get("agreement_amount", "")))
    )
    passport_blocks.append(section_html("🧾 Соглашение", agr))

    params = (
        kv_html("Мощность", row.get("capacity_seats", "—"))
        + kv_html("Площадь", row.get("area_m2", "—"))
        + kv_html("Целевой срок", date_fmt(row.get("target_deadline", "")))
    )
    passport_blocks.append(section_html("📦 Параметры", params))

    psd = (
        kv_html("ПСД", row.get("design", "—"))
        + kv_html("Стоимость ПСД", money_fmt(row.get("psd_cost", "")))
        + kv_html("Проектировщик", row.get("designer", "—"))
        + kv_html("Экспертиза", row.get("expertise", "—"))
        + kv_html("Дата экспертизы", date_fmt(row.get("expertise_date", "")))
        + kv_html("Заключение", row.get("expertise_conclusion", "—"))
    )
    passport_blocks.append(section_html("🗂️ ПСД / Экспертиза", psd))

    rns_block = (
        kv_html("№ РНС", row.get("rns", "—"))
        + kv_html("Дата", date_fmt(row.get("rns_date", "")))
        + kv_html("Срок действия", date_fmt(row.get("rns_expiry", "")))
    )
    passport_blocks.append(section_html("🏗️ РНС", rns_block))

    contr = (
        kv_html("№", row.get("contract", "—"))
        + kv_html("Дата", date_fmt(row.get("contract_date", "")))
        + kv_html("Подрядчик", row.get("contractor", "—"))
        + kv_html("Цена", money_fmt(row.get("contract_price", "")))
    )
    passport_blocks.append(section_html("🧩 Контракт", contr))

    terms = (
        kv_html("Окончание (план)", date_fmt(row.get("end_date_plan", "")))
        + kv_html("Окончание (факт)", date_fmt(row.get("end_date_fact", "")))
        + kv_html("Готовность", readiness_fmt(row.get("readiness", "")))
        + kv_html("Оплачено", money_fmt(row.get("paid", "")))
    )
    passport_blocks.append(section_html("⏳ Сроки / финансы", terms))

    rid = safe_text(row.get("id", ""), fallback="").strip()
    if not rid:
        rid = f"row_{abs(hash(title_txt))}"
    rid = re.sub(r"[^a-zA-Z0-9_]+", "_", rid)
    toggle_id = f"passport_{rid}"

    passport_html = dedent(
        f"""
        <div class="passport">
          <input class="passport-toggle" type="checkbox" id="{toggle_id}">
          <label class="passport-summary" for="{toggle_id}">📋 Паспорт объекта и контрольные показатели</label>

          <div class="passport-body">
            <div class="passport-grid">
              {''.join(passport_blocks)}
            </div>
            <div class="passport-close">
              <label class="passport-close-btn" for="{toggle_id}" title="Свернуть">▴</label>
            </div>
          </div>
        </div>
        """
    )

    info_html = dedent(
        f"""
        <div class="info-grid">
          <div class="info-item">
            <div class="ico">🗺️</div>
            <div class="itxt">
              <div class="ilbl">Адрес</div>
              <div class="ival">{address}</div>
            </div>
          </div>
          <div class="info-item">
            <div class="ico">👤</div>
            <div class="itxt">
              <div class="ilbl">Ответственный</div>
              <div class="ival">{responsible}</div>
            </div>
          </div>
        </div>
        """
    )

    card_html = dedent(
        f"""
        <div class="card" data-accent="{esc(accent)}">
          <div class="card-head">
            <div class="card-title">{title}</div>

            <div class="card-subchips">
              <span class="chip">🏷️ {sector}</span>
              <span class="chip">📍 {district}</span>
            </div>

            {info_html}

            <div class="card-tags">
              <span class="tag {s_cls}">📌 Статус: {esc(status)}</span>
              <span class="tag {w_cls}">🛠️ Работы: {esc(work_flag)}</span>
              <span class="tag {u_cls}">⏱️ Обновлено: {esc(u_txt)}</span>
            </div>

            {btn_html}

            {passport_html}
          </div>
        </div>
        """
    )

    st.markdown(card_html, unsafe_allow_html=True)


# =============================
# OUTPUT
# =============================
for _, r in filtered.iterrows():
    render_card(r)
