import base64
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


def date_fmt(v) -> str:
    d = try_parse_date(v)
    return d.strftime("%d.%m.%Y") if d else "—"


def readiness_fmt(v) -> str:
    s = safe_text(v, fallback="—")
    if s == "—":
        return s
    try:
        x = str(s).replace(" ", "").replace("\u00A0", "").replace(",", ".")
        f = float(x)
        # если 0..1 — считаем долей
        if 0 <= f <= 1:
            return f"{int(round(f * 100))}%"
        # если 1..100 — уже проценты
        if 1 < f <= 100:
            return f"{int(round(f))}%"
        return s
    except Exception:
        # если уже содержит %
        return s


def norm_text_for_search(s: str) -> str:
    s = (s or "").lower().replace("ё", "е")
    s = re.sub(r"[^\w\s]", " ", s)  # убрать пунктуацию
    s = re.sub(r"\s+", " ", s).strip()
    return s


def make_acronym(text: str) -> str:
    """
    Авто-аббревиатура по первым буквам слов (МОДКБ, ФАП и т.п.)
    """
    t = norm_text_for_search(text)
    if not t:
        return ""
    words = [w for w in t.split() if len(w) >= 2]
    ac = "".join([w[0] for w in words]).upper()
    return ac


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

    # ВАЖНО: берём ссылку из card_url_text (как вы просили), иначе fallback
    out["card_url"] = df[col(
        "card_url_text",
        "card_url",
        "ссылка_на_карточку_(google)",
        "ссылка на карточку",
        "ссылка_на_карточку"
    )] if col(
        "card_url_text",
        "card_url",
        "ссылка_на_карточку_(google)",
        "ссылка на карточку",
        "ссылка_на_карточку"
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
    out["agreement_date"] = df[col("agreement_date", "дата соглашения")] if col(
        "agreement_date", "дата соглашения"
    ) else ""
    out["agreement_amount"] = df[col("agreement_amount", "сумма соглашения")] if col(
        "agreement_amount", "сумма соглашения"
    ) else ""

    out["capacity_seats"] = df[col("capacity_seats", "мощность", "мест", "посещений")] if col(
        "capacity_seats", "мощность", "мест", "посещений"
    ) else ""
    out["area_m2"] = df[col("area_m2", "площадь", "м2", "кв.м")] if col(
        "area_m2", "площадь", "м2", "кв.м"
    ) else ""
    out["target_deadline"] = df[col("target_deadline", "целевой срок")] if col(
        "target_deadline", "целевой срок"
    ) else ""

    out["design"] = df[col("design", "проектирование", "псд")] if col("design", "проектирование", "псд") else ""
    out["psd_cost"] = df[col("psd_cost", "стоимость псд")] if col("psd_cost", "стоимость псд") else ""
    out["designer"] = df[col("designer", "проектировщик")] if col("designer", "проектировщик") else ""

    out["expertise"] = df[col("expertise", "экспертиза")] if col("expertise", "экспертиза") else ""
    out["expertise_conclusion"] = df[col("expertise_conclusion", "заключение экспертизы")] if col(
        "expertise_conclusion", "заключение экспертизы"
    ) else ""
    out["expertise_date"] = df[col("expertise_date", "дата экспертизы")] if col(
        "expertise_date", "дата экспертизы"
    ) else ""

    out["rns"] = df[col("rns", "рнс")] if col("rns", "рнс") else ""
    out["rns_date"] = df[col("rns_date", "дата рнс")] if col("rns_date", "дата рнс") else ""
    out["rns_expiry"] = df[col("rns_expiry", "срок действия рнс")] if col("rns_expiry", "срок действия рнс") else ""

    out["contract"] = df[col("contract", "контракт", "номер контракта")] if col(
        "contract", "контракт", "номер контракта"
    ) else ""
    out["contract_date"] = df[col("contract_date", "дата контракта")] if col(
        "contract_date", "дата контракта"
    ) else ""
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

    # Индекс для поиска + аббревиатуры
    out["_search"] = (
        out["name"].astype(str) + " " +
        out["address"].astype(str) + " " +
        out["responsible"].astype(str) + " " +
        out["sector"].astype(str) + " " +
        out["district"].astype(str)
    ).apply(norm_text_for_search)

    out["_abbr"] = out["name"].astype(str).apply(make_acronym).str.lower()
    out["_search_full"] = (out["_search"] + " " + out["_abbr"]).str.strip()

    return out


# =============================
# STYLES (FORCE LIGHT + READABLE MOBILE)
# =============================
crest_b64 = read_local_crest_b64()

st.markdown(
    """
<style>
/* --- Force light palette (чтобы на телефоне не было белого текста на светлом фоне) --- */
:root{
  --bg: #eef2f6;
  --card: #ffffff;
  --text: #0f172a;
  --muted: rgba(15,23,42,.70);
  --border: rgba(15,23,42,.12);
  --shadow: rgba(0,0,0,.08);
  --chip-bg: rgba(15,23,42,.05);
  --chip-bd: rgba(15,23,42,.10);
  --btn-bg: rgba(255,255,255,.96);
  --btn-bd: rgba(15,23,42,.16);
  --hr: rgba(15,23,42,.12);
}

.block-container { padding-top: 22px !important; max-width: 1200px; }
@media (max-width: 1200px){ .block-container { max-width: 96vw; } }
div[data-testid="stHorizontalBlock"]{ gap: 14px; }

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

html, body, [data-testid="stAppViewContainer"]{
  background: var(--bg) !important;
}

/* ===== HERO ===== */
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

/* ===== Filters panel (чтобы фильтры не сливались) ===== */
.filters-panel{
  border: 1px solid rgba(15,23,42,.12);
  background: rgba(255,255,255,.72);
  border-radius: 16px;
  padding: 12px 12px 6px 12px;
  box-shadow: 0 10px 20px rgba(0,0,0,.05);
  margin-bottom: 12px;
}

/* Поля ввода/селекты — единый стиль */
div[data-testid="stSelectbox"] > div,
div[data-testid="stTextInput"] > div{
  border-radius: 12px !important;
}
div[data-testid="stSelectbox"] div[role="combobox"],
div[data-testid="stTextInput"] input{
  background: rgba(255,255,255,.95) !important;
  border: 1px solid rgba(15,23,42,.14) !important;
  color: var(--text) !important;
}
div[data-testid="stTextInput"] input{
  padding-top: 12px !important;
  padding-bottom: 12px !important;
}

/* ===== CARD: больше воздуха + красивый внутренний фон ===== */
.card{
  background: linear-gradient(135deg, rgba(255,255,255,.94), rgba(248,250,252,.94));
  border: 1px solid var(--border);
  border-radius: 18px;
  padding: 18px;
  box-shadow: 0 10px 22px var(--shadow);
  margin-bottom: 16px;
  position: relative;
  overflow: hidden;
}
.card[data-accent="green"]{ border-color: rgba(34,197,94,.35); box-shadow: 0 12px 26px var(--shadow), inset 10px 0 0 rgba(34,197,94,.35); }
.card[data-accent="yellow"]{ border-color: rgba(245,158,11,.35); box-shadow: 0 12px 26px var(--shadow), inset 10px 0 0 rgba(245,158,11,.35); }
.card[data-accent="red"]{ border-color: rgba(239,68,68,.35); box-shadow: 0 12px 26px var(--shadow), inset 10px 0 0 rgba(239,68,68,.35); }
.card[data-accent="blue"]{ border-color: rgba(59,130,246,.30); box-shadow: 0 12px 26px var(--shadow), inset 10px 0 0 rgba(59,130,246,.28); }

.card-inner{
  padding: 10px 12px 12px 14px; /* воздух от контура */
}

.card-title{
  font-size: 20px;
  line-height: 1.18;
  font-weight: 900;
  margin: 0 0 12px 0;
  color: var(--text);
}

.card-subchips{ display:flex; gap:8px; flex-wrap:wrap; margin: 0 0 12px 0; }
.chip{
  display:inline-flex;
  align-items:center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid var(--chip-bd);
  background: var(--chip-bg);
  font-size: 13px;
  color: var(--text);
  opacity: .95;
}

/* Сетка для иконок и текста */
.card-grid{
  display:grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px 18px;
  margin-top: 4px;
  margin-bottom: 12px;
}
.line{
  display:flex;
  align-items:flex-start;
  gap: 10px;
  padding: 9px 10px;
  border-radius: 12px;
  background: rgba(15,23,42,.03);
  border: 1px solid rgba(15,23,42,.08);
}
.ico{
  width: 22px;
  flex: 0 0 22px;
  display:flex;
  justify-content:center;
  margin-top: 1px;
}
.ltxt{ color: var(--text); font-size: 14px; }
.ltxt b{ color: var(--text); }

.card-tags{ display:flex; gap:10px; flex-wrap:wrap; margin-top: 10px; margin-bottom: 12px; }
.tag{
  display:inline-flex;
  align-items:center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid var(--chip-bd);
  background: var(--chip-bg);
  font-size: 13px;
  color: var(--text);
  font-weight: 800;
}
.tag-gray{ opacity: .92; }
.tag-green{ background: rgba(34,197,94,.12); border-color: rgba(34,197,94,.25); }
.tag-yellow{ background: rgba(245,158,11,.14); border-color: rgba(245,158,11,.25); }
.tag-red{ background: rgba(239,68,68,.12); border-color: rgba(239,68,68,.25); }

/* Кнопка карточки — отдельный контур */
.card-actions{ display:flex; gap:12px; margin-top: 10px; margin-bottom: 12px; }
.a-btn{
  flex: 1 1 0;
  display:flex;
  justify-content:center;
  align-items:center;
  gap: 8px;
  padding: 11px 12px;
  border-radius: 12px;
  border: 1px solid var(--btn-bd);
  background: var(--btn-bg);
  text-decoration:none !important;
  color: var(--text) !important;
  font-weight: 900;
  font-size: 14px;
  transition: .12s ease-in-out;
}
.a-btn:hover{ transform: translateY(-1px); box-shadow: 0 10px 18px rgba(0,0,0,.10); }
.a-btn.disabled{ opacity: .45; pointer-events:none; }

/* Паспорт: общий контейнер внутри карточки */
.passport-wrap{
  border: 1px solid rgba(15,23,42,.12);
  background: rgba(255,255,255,.78);
  border-radius: 16px;
  padding: 12px;
}

/* Секции паспорта */
.section{
  padding: 12px;
  border-radius: 14px;
  border: 1px solid rgba(15,23,42,.10);
  background: rgba(255,255,255,.92);
}
.section-title{
  font-weight: 900;
  color: var(--text);
  margin-bottom: 8px;
  font-size: 14px;
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
.row .muted{ color: var(--muted); }

/* Проблемы — красиво переносятся */
.issue-box{
  border: 1px solid rgba(239,68,68,.25);
  background: rgba(239,68,68,.06);
  color: var(--text);
  padding: 10px 12px;
  border-radius: 12px;
  font-size: 13.5px;
  line-height: 1.45;
  white-space: pre-wrap;
  word-break: break-word;
}

/* 2 колонки секций */
.passport-grid{
  display:grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
@media (max-width: 900px){
  .card-grid{ grid-template-columns: 1fr; }
  .passport-grid{ grid-template-columns: 1fr; }
  .card-title{ font-size: 18px; }
}

/* Кнопка-стрелка */
.collapse-center{
  display:flex;
  justify-content:center;
  margin-top: 12px;
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
    st.error(
        "Данные не загрузились (реестр пустой). Проверьте CSV_URL в Secrets "
        "или наличие .xlsx в репозитории."
    )
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
st.markdown('<div class="filters-panel">', unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns([1, 1, 1, 1.2])
with c1:
    sector_sel = st.selectbox("🏷️ Отрасль", sectors, index=0, key="f_sector")
with c2:
    district_sel = st.selectbox("📍 Район", districts, index=0, key="f_district")
with c3:
    status_sel = st.selectbox("📌 Статус", statuses, index=0, key="f_status")
with c4:
    # без подсказки внутри поля
    q = st.text_input("🔎 Поиск", value="", key="f_search").strip().lower()
st.markdown("</div>", unsafe_allow_html=True)

filtered = df.copy()

if sector_sel != "Все":
    filtered = filtered[filtered["sector"].astype(str) == str(sector_sel)]
if district_sel != "Все":
    filtered = filtered[filtered["district"].astype(str) == str(district_sel)]
if status_sel != "Все":
    filtered = filtered[filtered["status"].astype(str) == str(status_sel)]

if q:
    nq = norm_text_for_search(q)

    def row_match(r):
        blob = str(r.get("_search_full", ""))
        return nq in blob

    filtered = filtered[filtered.apply(row_match, axis=1)]

st.caption(f"Показано объектов: {len(filtered)} из {len(df)}")
st.divider()


# =============================
# CARD RENDER
# =============================
def render_kv(label: str, value: str):
    st.markdown(f'<div class="row"><b>{label}:</b> {value}</div>', unsafe_allow_html=True)


def render_section(title: str, inner_html: str):
    st.markdown(
        f"""
<div class="section">
  <div class="section-title">{title}</div>
  {inner_html}
</div>
""",
        unsafe_allow_html=True,
    )


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

    accent = status_accent(status)
    w_col = works_color(work_flag)
    u_col, u_txt = update_color(row.get("updated_at", ""))

    s_col = "tag-gray"
    if accent == "green":
        s_col = "tag-green"
    elif accent == "yellow":
        s_col = "tag-yellow"
    elif accent == "red":
        s_col = "tag-red"

    w_tag = "tag-gray"
    if w_col == "green":
        w_tag = "tag-green"
    elif w_col == "yellow":
        w_tag = "tag-yellow"
    elif w_col == "red":
        w_tag = "tag-red"

    u_tag = "tag-gray"
    if u_col == "green":
        u_tag = "tag-green"
    elif u_col == "yellow":
        u_tag = "tag-yellow"
    elif u_col == "red":
        u_tag = "tag-red"

    btn_card = (
        f'<a class="a-btn" href="{card_url}" target="_blank">📄 Открыть карточку</a>'
        if card_url and card_url != "—"
        else '<span class="a-btn disabled">📄 Открыть карточку</span>'
    )

    # ключ состояния паспорта (на объект)
    obj_id = safe_text(row.get("id", ""), fallback="")
    key_open = f"passport_open_{obj_id or title}"

    if key_open not in st.session_state:
        st.session_state[key_open] = False

    # Рендер карточки (паспорт внутри контура)
    st.markdown(
        f"""
<div class="card" data-accent="{accent}">
  <div class="card-inner">

    <div class="card-title">{title}</div>

    <div class="card-subchips">
      <span class="chip">🏷️ {sector}</span>
      <span class="chip">📍 {district}</span>
    </div>

    <div class="card-grid">
      <div class="line">
        <span class="ico">🗺️</span>
        <span class="ltxt"><b>Адрес:</b> {address}</span>
      </div>

      <div class="line">
        <span class="ico">👤</span>
        <span class="ltxt"><b>Ответственный:</b> {responsible}</span>
      </div>
    </div>

    <div class="card-tags">
      <span class="tag {s_col}">📌 Статус: {status}</span>
      <span class="tag {w_tag}">🛠️ Работы: {work_flag}</span>
      <span class="tag {u_tag}">⏱️ Обновлено: {u_txt}</span>
    </div>

    <div class="card-actions">
      {btn_card}
    </div>
""",
        unsafe_allow_html=True,
    )

    # Кнопка "открыть паспорт" (нормальная, внутри карточки)
    cols = st.columns([1, 3, 1])
    with cols[1]:
        if not st.session_state[key_open]:
            if st.button("📋 Паспорт объекта и контрольные показатели", key=f"open_{key_open}"):
                st.session_state[key_open] = True
                st.rerun()

    # ПАСПОРТ
    if st.session_state[key_open]:
        st.markdown('<div class="passport-wrap">', unsafe_allow_html=True)

        # Проблемные вопросы (во всю ширину)
        if issues != "—":
            st.markdown(
                f"""
<div class="section">
  <div class="section-title">⚠️ Проблемные вопросы</div>
  <div class="issue-box">{issues}</div>
</div>
""",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
<div class="section">
  <div class="section-title">⚠️ Проблемные вопросы</div>
  <div class="row"><span class="muted">—</span></div>
</div>
""",
                unsafe_allow_html=True,
            )

        # Секции в 2 колонки
        st.markdown('<div class="passport-grid">', unsafe_allow_html=True)

        # Программы
        st.markdown(
            f"""
<div class="section">
  <div class="section-title">🏛️ Программы</div>
  <div class="row"><b>ГП/СП:</b> {safe_text(row.get("state_program", ""), "—")}</div>
  <div class="row"><b>ФП:</b> {safe_text(row.get("federal_project", ""), "—")}</div>
  <div class="row"><b>РП:</b> {safe_text(row.get("regional_program", ""), "—")}</div>
</div>
""",
            unsafe_allow_html=True,
        )

        # Соглашение
        st.markdown(
            f"""
<div class="section">
  <div class="section-title">🧾 Соглашение</div>
  <div class="row"><b>№:</b> {safe_text(row.get("agreement", ""), "—")}</div>
  <div class="row"><b>Дата:</b> {date_fmt(row.get("agreement_date", ""))}</div>
  <div class="row"><b>Сумма:</b> {money_fmt(row.get("agreement_amount", ""))}</div>
</div>
""",
            unsafe_allow_html=True,
        )

        # Параметры
        st.markdown(
            f"""
<div class="section">
  <div class="section-title">📦 Параметры</div>
  <div class="row"><b>Мощность:</b> {safe_text(row.get("capacity_seats", ""), "—")}</div>
  <div class="row"><b>Площадь:</b> {safe_text(row.get("area_m2", ""), "—")}</div>
  <div class="row"><b>Целевой срок:</b> {date_fmt(row.get("target_deadline", ""))}</div>
</div>
""",
            unsafe_allow_html=True,
        )

        # ПСД / Экспертиза
        st.markdown(
            f"""
<div class="section">
  <div class="section-title">🗂️ ПСД / Экспертиза</div>
  <div class="row"><b>ПСД:</b> {safe_text(row.get("design", ""), "—")}</div>
  <div class="row"><b>Стоимость ПСД:</b> {money_fmt(row.get("psd_cost", ""))}</div>
  <div class="row"><b>Проектировщик:</b> {safe_text(row.get("designer", ""), "—")}</div>
  <div class="row"><b>Экспертиза:</b> {safe_text(row.get("expertise", ""), "—")}</div>
  <div class="row"><b>Дата экспертизы:</b> {date_fmt(row.get("expertise_date", ""))}</div>
  <div class="row"><b>Заключение:</b> {safe_text(row.get("expertise_conclusion", ""), "—")}</div>
</div>
""",
            unsafe_allow_html=True,
        )

        # РНС
        st.markdown(
            f"""
<div class="section">
  <div class="section-title">🏗️ РНС</div>
  <div class="row"><b>№ РНС:</b> {safe_text(row.get("rns", ""), "—")}</div>
  <div class="row"><b>Дата:</b> {date_fmt(row.get("rns_date", ""))}</div>
  <div class="row"><b>Срок действия:</b> {date_fmt(row.get("rns_expiry", ""))}</div>
</div>
""",
            unsafe_allow_html=True,
        )

        # Контракт
        st.markdown(
            f"""
<div class="section">
  <div class="section-title">🧩 Контракт</div>
  <div class="row"><b>№:</b> {safe_text(row.get("contract", ""), "—")}</div>
  <div class="row"><b>Дата:</b> {date_fmt(row.get("contract_date", ""))}</div>
  <div class="row"><b>Подрядчик:</b> {safe_text(row.get("contractor", ""), "—")}</div>
  <div class="row"><b>Цена:</b> {money_fmt(row.get("contract_price", ""))}</div>
</div>
""",
            unsafe_allow_html=True,
        )

        # Сроки/финансы
        st.markdown(
            f"""
<div class="section">
  <div class="section-title">⏳ Сроки / финансы</div>
  <div class="row"><b>Окончание (план):</b> {date_fmt(row.get("end_date_plan", ""))}</div>
  <div class="row"><b>Окончание (факт):</b> {date_fmt(row.get("end_date_fact", ""))}</div>
  <div class="row"><b>Готовность:</b> {readiness_fmt(row.get("readiness", ""))}</div>
  <div class="row"><b>Оплачено:</b> {money_fmt(row.get("paid", ""))}</div>
</div>
""",
            unsafe_allow_html=True,
        )

        st.markdown("</div>", unsafe_allow_html=True)  # passport-grid

        # Кнопка-стрелка (свернуть)
        st.markdown('<div class="collapse-center">', unsafe_allow_html=True)
        if st.button("▲", key=f"collapse_{key_open}"):
            st.session_state[key_open] = False
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)  # passport-wrap

    # закрываем card-inner / card
    st.markdown("</div></div>", unsafe_allow_html=True)


# =============================
# OUTPUT
# =============================
for _, r in filtered.iterrows():
    render_card(r)
