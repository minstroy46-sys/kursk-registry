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
    if s in ("—", "", "нет", "не ведутся"):
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

    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v

    s = str(v).strip()
    if not s or s.lower() in ("nan", "none", "null", "—"):
        return None

    # Excel serial date (например 45234)
    if re.fullmatch(r"\d+(\.\d+)?", s):
        try:
            num = float(s)
            dt = pd.to_datetime(num, unit="D", origin="1899-12-30", errors="coerce")
            if pd.isna(dt):
                return None
            return dt.date()
        except Exception:
            return None

    # популярные форматы
    for fmt in ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass

    # общий парсер
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


def percent_fmt(v) -> str:
    """
    Готовность:
    - 0.38 -> 38%
    - 38 -> 38%
    - '38%' -> 38%
    """
    s = safe_text(v, fallback="—")
    if s == "—":
        return "—"
    s0 = str(s).strip()

    if "%" in s0:
        s1 = s0.replace("%", "").replace(",", ".").strip()
        try:
            x = float(s1)
            return f"{int(round(x))}%"
        except Exception:
            return s0

    try:
        x = float(str(s0).replace(" ", "").replace("\u00A0", "").replace(",", "."))
        if 0 <= x <= 1:
            return f"{int(round(x * 100))}%"
        if 1 < x <= 100:
            return f"{int(round(x))}%"
        return f"{x}%"
    except Exception:
        return s0


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

    # fallback local xlsx
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
    if df.empty:
        return df

    def col(*cands):
        return pick_col(df, list(cands))

    out = pd.DataFrame()

    out["sector"] = df[col("sector", "отрасль")] if col("sector", "отрасль") else ""
    out["district"] = df[col("district", "район")] if col("district", "район") else ""
    out["name"] = df[col("name", "object_name", "наименование_объекта", "наименование объекта", "объект")] if col(
        "name", "object_name", "наименование_объекта", "наименование объекта", "объект"
    ) else ""
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
    out["card_url"] = df[col("card_url", "ссылка_на_карточку_(google)", "ссылка на карточку", "ссылка_на_карточку")] if col(
        "card_url", "ссылка_на_карточку_(google)", "ссылка на карточку", "ссылка_на_карточку"
    ) else ""
    out["folder_url"] = df[col("folder_url", "ссылка_на_папку_(drive)", "ссылка на папку", "ссылка_на_папку")] if col(
        "folder_url", "ссылка_на_папку_(drive)", "ссылка на папку", "ссылка_на_папку"
    ) else ""

    # дополнительные поля (как в вашем реестре)
    fields = [
        "state_program", "federal_project", "regional_program",
        "agreement", "agreement_date", "agreement_amount",
        "capacity_seats", "area_m2", "target_deadline",
        "design", "psd_cost", "designer",
        "expertise", "expertise_conclusion", "expertise_date",
        "rns", "rns_date", "rns_expiry",
        "contract", "contract_date", "contractor", "contract_price",
        "end_date_plan", "end_date_fact", "readiness", "paid",
        "photo_url",
    ]
    for f in fields:
        c = col(f, f.replace("_", " "), f.upper())
        out[f] = df[c] if c else ""

    for c in out.columns:
        out[c] = out[c].astype(str).replace({"nan": "", "None": "", "null": ""})

    return out


# =============================
# STYLES (dark-mode aware)
# =============================
crest_b64 = read_local_crest_b64()

st.markdown(
    """
<style>
:root{
  --bg: #f7f8fb;
  --card: #ffffff;
  --card2: rgba(15,23,42,.03);
  --text: #0f172a;
  --muted: rgba(15,23,42,.72);
  --border: rgba(15,23,42,.10);
  --shadow: rgba(0,0,0,.06);
  --chip-bg: rgba(15,23,42,.05);
  --chip-bd: rgba(15,23,42,.10);
  --btn-bg: rgba(255,255,255,.95);
  --btn-bd: rgba(15,23,42,.12);
}

@media (prefers-color-scheme: dark){
  :root{
    --bg: #0b1220;
    --card: #111a2b;
    --card2: rgba(255,255,255,.05);
    --text: rgba(255,255,255,.92);
    --muted: rgba(255,255,255,.70);
    --border: rgba(255,255,255,.12);
    --shadow: rgba(0,0,0,.35);
    --chip-bg: rgba(255,255,255,.06);
    --chip-bd: rgba(255,255,255,.12);
    --btn-bg: rgba(17,26,43,.92);
    --btn-bd: rgba(255,255,255,.14);
  }
}

html, body, [data-testid="stAppViewContainer"]{
  background: var(--bg) !important;
}

.block-container { padding-top: 24px !important; max-width: 1200px; }
@media (max-width: 1200px){ .block-container { max-width: 96vw; } }
div[data-testid="stHorizontalBlock"]{ gap: 14px; }

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* HERO */
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

/* CARD */
.card{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 16px;
  box-shadow: 0 10px 22px var(--shadow);
  margin-bottom: 10px;
}
.card[data-accent="green"]{ box-shadow: 0 10px 22px var(--shadow), inset 6px 0 0 rgba(34,197,94,.55); }
.card[data-accent="yellow"]{ box-shadow: 0 10px 22px var(--shadow), inset 6px 0 0 rgba(245,158,11,.55); }
.card[data-accent="red"]{ box-shadow: 0 10px 22px var(--shadow), inset 6px 0 0 rgba(239,68,68,.55); }
.card[data-accent="blue"]{ box-shadow: 0 10px 22px var(--shadow), inset 6px 0 0 rgba(59,130,246,.45); }

.title-bar{
  display:flex;
  align-items:flex-start;
  justify-content:space-between;
  gap: 12px;
  margin-bottom: 8px;
}
.card-title{
  font-size: 20px;
  line-height: 1.15;
  font-weight: 950;
  margin: 0;
  color: var(--text);
  letter-spacing: .2px;
}
.card-title span{
  background: linear-gradient(90deg, rgba(59,130,246,.22), rgba(34,197,94,.16), rgba(245,158,11,.12));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
@media (prefers-color-scheme: dark){
  .card-title span{
    background: linear-gradient(90deg, rgba(147,197,253,.45), rgba(134,239,172,.28), rgba(253,230,138,.25));
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
  }
}

.photo{
  width: 132px;
  height: 82px;
  border-radius: 12px;
  border: 1px solid var(--border);
  overflow:hidden;
  background: var(--card2);
  flex: 0 0 auto;
}
.photo img{ width:100%; height:100%; object-fit: cover; display:block; }

.card-subchips{
  display:flex; gap: 8px; flex-wrap: wrap;
  margin-bottom: 10px;
}
.chip{
  display:inline-flex; align-items:center; gap: 8px;
  padding: 6px 10px; border-radius: 999px;
  border: 1px solid var(--chip-bd);
  background: var(--chip-bg);
  font-size: 13px; color: var(--text);
}

.card-grid{
  display:grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 18px;
  margin-top: 6px;
}
.card-item{ font-size: 14px; color: var(--text); }
.card-item b{ color: var(--text); }

.card-tags{
  display:flex; gap: 10px; flex-wrap: wrap;
  margin-top: 10px;
}
.tag{
  display:inline-flex; align-items:center; gap: 8px;
  padding: 6px 10px; border-radius: 999px;
  border: 1px solid var(--chip-bd);
  background: var(--chip-bg);
  font-size: 13px; color: var(--text);
  font-weight: 900;
}
.tag-green{ background: rgba(34,197,94,.12); border-color: rgba(34,197,94,.22); }
.tag-yellow{ background: rgba(245,158,11,.14); border-color: rgba(245,158,11,.25); }
.tag-red{ background: rgba(239,68,68,.12); border-color: rgba(239,68,68,.22); }
.tag-gray{ opacity: .92; }

.card-actions{
  display:flex; gap: 12px; margin-top: 12px;
}
.a-btn{
  flex: 1 1 0;
  display:flex; justify-content:center; align-items:center; gap: 8px;
  padding: 10px 12px; border-radius: 12px;
  border: 1px solid var(--btn-bd);
  background: var(--btn-bg);
  text-decoration:none !important;
  color: var(--text) !important;
  font-weight: 900; font-size: 14px;
  transition: .12s ease-in-out;
}
.a-btn:hover{ transform: translateY(-1px); box-shadow: 0 10px 18px rgba(0,0,0,.10); }
.a-btn.disabled{ opacity: .45; pointer-events:none; }

.section{
  margin-top: 12px;
  padding: 12px;
  border-radius: 14px;
  border: 1px solid var(--border);
  background: var(--card2);
}
.section-title{ font-weight: 950; color: var(--text); margin-bottom: 8px; font-size: 14px; }
.row{ color: var(--text); font-size: 13.5px; margin-bottom: 4px; }
.row b{ color: var(--text); }

.issue-box{
  border: 1px solid rgba(239,68,68,.25);
  background: rgba(239,68,68,.08);
  color: var(--text);
  padding: 10px 12px;
  border-radius: 12px;
  font-size: 13.5px;
}

@media (max-width: 900px){
  .card-grid{ grid-template-columns: 1fr; }
  .card-actions{ flex-direction: column; }
  .photo{ width: 100%; height: 140px; }
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

q = st.text_input("🔎 Поиск (наименование / адрес / ответственный)", value="", key="f_search").strip().lower()

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
            ]
        ).lower()
        return q in s

    filtered = filtered[filtered.apply(row_match, axis=1)]

st.caption(f"Показано объектов: {len(filtered)} из {len(df)}")
st.divider()


# =============================
# RENDER
# =============================
def render_kv(label: str, value: str):
    st.markdown(f'<div class="row"><b>{label}:</b> {value}</div>', unsafe_allow_html=True)


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
    photo_url = safe_text(row.get("photo_url", ""), fallback="")

    accent = status_accent(status)
    w_col = works_color(work_flag)
    u_col, u_txt = update_color(row.get("updated_at", ""))

    s_tag = {"green": "tag-green", "yellow": "tag-yellow", "red": "tag-red"}.get(accent, "tag-gray")
    w_tag = {"green": "tag-green", "red": "tag-red"}.get(w_col, "tag-gray")
    u_tag = {"green": "tag-green", "yellow": "tag-yellow", "red": "tag-red"}.get(u_col, "tag-gray")

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

    photo_html = f'<div class="photo"><img src="{photo_url}" alt="Фото объекта"/></div>' if photo_url and photo_url != "—" else ""

    # ШАПКА карточки
    st.markdown(
        f"""
<div class="card" data-accent="{accent}">
  <div class="title-bar">
    <h3 class="card-title"><span>{title}</span></h3>
    {photo_html}
  </div>

  <div class="card-subchips">
    <span class="chip">🏷️ {sector}</span>
    <span class="chip">📍 {district}</span>
  </div>

  <div class="card-grid">
    <div class="card-item">🗺️ <b>Адрес:</b> {address}</div>
    <div class="card-item">👤 <b>Ответственный:</b> {responsible}</div>
  </div>

  <div class="card-tags">
    <span class="tag {s_tag}">📌 Статус: {status}</span>
    <span class="tag {w_tag}">🛠️ Работы: {work_flag}</span>
    <span class="tag {u_tag}">⏱️ Обновлено: {u_txt}</span>
  </div>

  <div class="card-actions">
    {btn_card}
    {btn_folder}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    # СВОРАЧИВАЕМЫЙ “ПАСПОРТ”
    with st.expander("📋 Паспорт объекта и контрольные показатели — нажмите, чтобы раскрыть", expanded=False):
        st.markdown('<div class="section"><div class="section-title">⚠️ Проблемные вопросы</div>', unsafe_allow_html=True)
        if issues != "—":
            st.markdown(f'<div class="issue-box">{issues}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="row">—</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="section"><div class="section-title">🏛️ Программы</div>', unsafe_allow_html=True)
        render_kv("ГП/СП", safe_text(row.get("state_program", ""), "—"))
        render_kv("ФП", safe_text(row.get("federal_project", ""), "—"))
        render_kv("РП", safe_text(row.get("regional_program", ""), "—"))
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="section"><div class="section-title">🧾 Соглашение</div>', unsafe_allow_html=True)
        render_kv("№", safe_text(row.get("agreement", ""), "—"))
        render_kv("Дата", date_fmt(row.get("agreement_date", "")))
        render_kv("Сумма", money_fmt(row.get("agreement_amount", "")))
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="section"><div class="section-title">📦 Параметры</div>', unsafe_allow_html=True)
        render_kv("Мощность", safe_text(row.get("capacity_seats", ""), "—"))
        render_kv("Площадь", safe_text(row.get("area_m2", ""), "—"))
        render_kv("Целевой срок", date_fmt(row.get("target_deadline", "")))
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="section"><div class="section-title">🗂️ ПСД / Экспертиза</div>', unsafe_allow_html=True)
        render_kv("Стоимость ПСД", money_fmt(row.get("psd_cost", "")))
        render_kv("Проектировщик", safe_text(row.get("designer", ""), "—"))
        render_kv("Экспертиза", safe_text(row.get("expertise", ""), "—"))
        render_kv("Дата экспертизы", date_fmt(row.get("expertise_date", "")))
        render_kv("Заключение", safe_text(row.get("expertise_conclusion", ""), "—"))
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="section"><div class="section-title">🏗️ РНС</div>', unsafe_allow_html=True)
        render_kv("№ РНС", safe_text(row.get("rns", ""), "—"))
        render_kv("Дата", date_fmt(row.get("rns_date", "")))
        render_kv("Срок действия", date_fmt(row.get("rns_expiry", "")))
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="section"><div class="section-title">🧩 Контракт</div>', unsafe_allow_html=True)
        render_kv("№", safe_text(row.get("contract", ""), "—"))
        render_kv("Дата", date_fmt(row.get("contract_date", "")))
        render_kv("Подрядчик", safe_text(row.get("contractor", ""), "—"))
        render_kv("Цена", money_fmt(row.get("contract_price", "")))
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="section"><div class="section-title">⏳ Сроки / финансы</div>', unsafe_allow_html=True)
        render_kv("Окончание (план)", date_fmt(row.get("end_date_plan", "")))
        render_kv("Окончание (факт)", date_fmt(row.get("end_date_fact", "")))
        render_kv("Готовность", percent_fmt(row.get("readiness", "")))
        render_kv("Оплачено", money_fmt(row.get("paid", "")))
        st.markdown("</div>", unsafe_allow_html=True)


for _, r in filtered.iterrows():
    render_card(r)
