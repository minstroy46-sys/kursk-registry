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
    """CSS-класс для подсветки статуса."""
    s = norm_col(status_text)

    if "останов" in s or "приостанов" in s:
        return "status status-red"
    if "проектир" in s:
        return "status status-yellow"
    if "строитель" in s:
        return "status status-green"
    return "status"


# ---------- DATE FIX (Google Sheets serial -> dd.mm.yyyy) ----------
GS_EPOCH = date(1899, 12, 30)  # Google Sheets / Excel serial base

def to_date_str(v) -> str:
    """
    Приводим дату к строке ДД.ММ.ГГГГ.
    Поддерживает:
    - datetime/date
    - строки (пытаемся распарсить)
    - числа (serial Google Sheets: 45652)
    """
    if v is None:
        return "—"
    try:
        if pd.isna(v):
            return "—"
    except Exception:
        pass

    # datetime/date
    if isinstance(v, (datetime, date)):
        try:
            return pd.to_datetime(v).strftime("%d.%m.%Y")
        except Exception:
            return str(v)

    # numeric serial
    if isinstance(v, (int, float)):
        # отсекаем совсем “мелкие/мусорные” числа
        if 20000 <= float(v) <= 90000:
            d = GS_EPOCH + timedelta(days=int(float(v)))
            return d.strftime("%d.%m.%Y")
        # иначе показываем как есть
        return str(v)

    s = str(v).strip()
    if not s:
        return "—"

    # string -> datetime
    try:
        dt = pd.to_datetime(s, dayfirst=True, errors="coerce")
        if pd.notna(dt):
            return dt.strftime("%d.%m.%Y")
    except Exception:
        pass

    return s


def normalize_dates_in_df(df: pd.DataFrame) -> pd.DataFrame:
    """Автоприведение всех *_date / *date* колонок к нормальному виду (строкой)."""
    if df.empty:
        return df
    for c in df.columns:
        nc = norm_col(c)
        if nc.endswith("_date") or nc == "date" or "date" in nc:
            df[c] = df[c].apply(to_date_str)
    return df


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
            "РЕЕСТР_объектов_Курская_область_2025-2028 (7).xlsx",
            "registry.xlsx",
            "data.xlsx",
        ]
        for name in candidates:
            p = Path(__file__).parent / name
            if p.exists():
                try:
                    # ВАЖНО: если есть лист "РЕЕСТР" — берём его
                    xls = pd.ExcelFile(p)
                    sheet = "РЕЕСТР" if "РЕЕСТР" in xls.sheet_names else 0
                    df = pd.read_excel(p, sheet_name=sheet)
                    break
                except Exception:
                    pass

    if df is None or df.empty:
        return pd.DataFrame()

    df.columns = [str(c).strip() for c in df.columns]
    df = normalize_dates_in_df(df)
    return df


def normalize_schema(df: pd.DataFrame) -> pd.DataFrame:
    """
    Приводим к вашей фиксированной схеме (англ. колонки).
    Если каких-то колонок нет — создаём пустые.
    """
    if df.empty:
        return df.copy()

    # Базовые (A-O и дальше по вашей схеме)
    mapping = {
        "id": ["id", "ID"],
        "sector": ["sector", "Отрасль"],
        "district": ["district", "Район"],
        "object_name": ["object_name", "name", "Наименование_объекта", "Наименование объекта"],
        "object_type": ["object_type", "объект", "Объект", "Тип", "type"],
        "responsible": ["responsible", "Ответственный"],
        "status": ["status", "Статус"],
        "works_in_progress": ["works_in_progress", "Работы_ведутся", "Работы ведутся", "work_flag", "works"],
        "issues": ["issues", "Проблемные_вопросы", "Проблемные вопросы"],
        "last_update": ["last_update", "Дата_последнего_обновления", "Дата последнего обновления"],
        "card_url": ["card_url", "Ссылка_на_карточку_(Google)", "Ссылка на карточку", "Ссылка_на_карточку"],
        "folder_url": ["folder_url", "Ссылка_на_папку_(Drive)", "Ссылка на папку", "Ссылка_на_папку"],
        "card_url_text": ["card_url_text"],
        "folder_url_text": ["folder_url_text"],
        "address": ["address", "Адрес"],

        # Расширение после address (ваша финальная структура)
        "state_program": ["state_program", "Госпрограмма"],
        "federal_project": ["federal_project", "Федеральный_проект", "Федеральный проект"],
        "regional_program": ["regional_program", "Региональная_программа", "Региональная программа"],
        "agreement": ["agreement", "Соглашение"],
        "agreement_date": ["agreement_date", "Дата_соглашения", "Дата соглашения"],
        "agreement_amount": ["agreement_amount", "Сумма_соглашения", "Сумма соглашения"],
        "capacity_seats": ["capacity_seats", "Мощность (мест)", "Мощность_мест", "capacity"],
        "area_m2": ["area_m2", "Площадь", "Площадь_м2", "area"],
        "target_deadline": ["target_deadline", "Срок_достижения результата"],
        "design": ["design", "Проектирование"],
        "psd_cost": ["psd_cost", "Стоимость_ПСД", "Стоимость ПСД"],
        "designer": ["designer", "Проектировщик"],
        "expertise": ["expertise", "Экспертиза"],
        "expertise_conclusion": ["expertise_conclusion", "Заключение экспертизы"],
        "expertise_date": ["expertise_date", "Дата экспертизы"],
        "rns": ["rns", "РНС"],
        "rns_date": ["rns_date", "Дата РНС", "rns date", "Дата"],
        "rns_expiry": ["rns_expiry", "Срок РНС", "rns_expiry"],
        "contract": ["contract", "Контракт"],
        "contract_date": ["contract_date", "Дата контракта"],
        "contractor": ["contractor", "Подрядчик"],
        "contract_price": ["contract_price", "Цена контракта"],
        "end_date_plan": ["end_date_plan", "Срок окончания_план"],
        "end_date_fact": ["end_date_fact", "Срок окончания_факт"],
        "readiness": ["readiness", "Готовность"],
        "paid": ["paid", "Оплачено"],
        "updated_at": ["updated_at", "updated_at", "Обновлено", "updated"],
    }

    out = pd.DataFrame()

    # соберём колонки
    for target, candidates in mapping.items():
        col = pick_col(df, candidates)
        if col:
            out[target] = df[col]
        else:
            out[target] = ""

    # чистим nan/None
    for c in out.columns:
        out[c] = out[c].astype(str).replace({"nan": "", "None": ""})

    # ещё раз приводим все date-поля (после cast to str тоже бывает)
    for c in out.columns:
        nc = norm_col(c)
        if nc.endswith("_date") or "date" in nc:
            out[c] = out[c].apply(to_date_str)

    return out


# =============================
# STYLES (ШАПКУ НЕ ТРОГАЕМ — оставляем как есть)
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
   CARDS (ONLY DESIGN CHANGE)
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
  color: rgba(15, 23, 42, .92);
}

.tag.status-yellow{
  background: rgba(245, 158, 11, .12);
  border-color: rgba(245, 158, 11, .25);
  color: rgba(15, 23, 42, .92);
}

.tag.status-red{
  background: rgba(239, 68, 68, .09);
  border-color: rgba(239, 68, 68, .20);
  color: rgba(15, 23, 42, .92);
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
  color: rgba(15, 23, 42, .70);
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

# фильтры по вашим полям
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
                str(r.get("object_name", "")),
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
# CARD RENDER (ваш стиль + аккуратно добавили доп.поля)
# =============================
def render_card(row: pd.Series):
    title = safe_text(row.get("object_name", ""), fallback="Объект")
    sector = safe_text(row.get("sector", ""), fallback="—")
    district = safe_text(row.get("district", ""), fallback="—")
    address = safe_text(row.get("address", ""), fallback="—")
    responsible = safe_text(row.get("responsible", ""), fallback="—")

    status = safe_text(row.get("status", ""), fallback="—")
    work_flag = safe_text(row.get("works_in_progress", ""), fallback="—")
    last_update = safe_text(row.get("last_update", ""), fallback="—")
    issues = safe_text(row.get("issues", ""), fallback="—")

    card_url = safe_text(row.get("card_url", ""), fallback="")
    folder_url = safe_text(row.get("folder_url", ""), fallback="")

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

    # доп поля (покажем только если есть значения)
    extra_pairs = [
        ("Госпрограмма", row.get("state_program", "")),
        ("Фед. проект", row.get("federal_project", "")),
        ("Рег. программа", row.get("regional_program", "")),
        ("Соглашение", row.get("agreement", "")),
        ("Дата соглаш.", row.get("agreement_date", "")),
        ("Сумма соглаш.", row.get("agreement_amount", "")),
        ("Мощность (мест)", row.get("capacity_seats", "")),
        ("Площадь (м²)", row.get("area_m2", "")),
        ("Срок достижения", row.get("target_deadline", "")),
        ("Проектирование", row.get("design", "")),
        ("Стоимость ПСД", row.get("psd_cost", "")),
        ("Проектировщик", row.get("designer", "")),
        ("Экспертиза", row.get("expertise", "")),
        ("Заключение экспертизы", row.get("expertise_conclusion", "")),
        ("Дата экспертизы", row.get("expertise_date", "")),
        ("РНС", row.get("rns", "")),
        ("Дата РНС", row.get("rns_date", "")),
        ("РНС (срок/оконч.)", row.get("rns_expiry", "")),
        ("Контракт", row.get("contract", "")),
        ("Дата контракта", row.get("contract_date", "")),
        ("Подрядчик", row.get("contractor", "")),
        ("Цена контракта", row.get("contract_price", "")),
        ("Окончание (план)", row.get("end_date_plan", "")),
        ("Окончание (факт)", row.get("end_date_fact", "")),
        ("Готовность", row.get("readiness", "")),
        ("Оплачено", row.get("paid", "")),
        ("updated_at", row.get("updated_at", "")),
    ]
    extra_lines = []
    for k, v in extra_pairs:
        vv = safe_text(v, fallback="")
        if vv and vv != "—":
            extra_lines.append(f"• <b>{k}:</b> {vv}")

    extra_html = ""
    if extra_lines:
        extra_html = "<br/>".join(extra_lines)
    else:
        extra_html = "—"

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
    <span class="tag">🗓️ <b>Обновлено:</b> {last_update}</span>
  </div>

  <div class="card-actions">
    {btn_card}
    {btn_folder}
  </div>

  <div class="card-extra">
    <b>Проблемные вопросы:</b> {issues}<br/><br/>
    <b>Паспорт/финансы/сроки (из реестра):</b><br/>
    {extra_html}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


for _, r in filtered.iterrows():
    render_card(r)
