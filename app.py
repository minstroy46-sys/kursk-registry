import os
import re
import pandas as pd
import streamlit as st


# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(
    page_title="Реестр объектов — Курская область",
    layout="wide",
    initial_sidebar_state="collapsed",
)

APP_TITLE = "Министерство восстановления, развития приграничья и строительства Курской области"
APP_SUBTITLE = "Реестр объектов"
APP_DESC = "Единый список объектов 2025–2028 с быстрыми фильтрами и переходом в карточку/папку."

ASSET_GERB = os.path.join("assets", "gerb.png")

# Ваш файл-резерв (если CSV_URL не задан / недоступен)
LOCAL_XLSX_CANDIDATES = [
    "РЕЕСТР_объектов_Курская_область_2025-2028.xlsx",
    "РЕЕСТР_объектов_Курская_область_2025-2028 (7).xlsx",
]


# -----------------------------
# CSS (шапка + мобильная адаптация + скрыть watermark)
# -----------------------------
st.markdown(
    """
<style>
/* чуть приятнее базовый фон */
.stApp { background: #f6f8fb; }

/* скрыть стандартные элементы streamlit */
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;} /* "водяной знак" снизу часто прячется так */

/* HERO */
.hero-wrap{
  max-width: 1120px;
  margin: 22px auto 14px auto;
  border-radius: 18px;
  padding: 22px 26px;
  position: relative;
  overflow: hidden;
  box-shadow: 0 14px 30px rgba(16, 24, 40, .18);
  background: linear-gradient(135deg, #1b3a6f 0%, #244b86 55%, #1a3768 100%);
}
.hero-wrap:before{
  content:"";
  position:absolute;
  inset:-40px -120px auto auto;
  width: 520px; height: 520px;
  transform: rotate(12deg);
  background: radial-gradient(circle at 30% 30%, rgba(255,255,255,.14), rgba(255,255,255,0) 60%);
}
.hero-row{
  display:flex; gap:18px; align-items:flex-start;
  position:relative; z-index:2;
}
.hero-logo{
  width: 76px; height: 76px;
  border-radius: 14px;
  background: rgba(255,255,255,.08);
  border: 1px solid rgba(255,255,255,.16);
  display:flex; align-items:center; justify-content:center;
  flex: 0 0 auto;
}
.hero-logo img{ width: 58px; height: 58px; object-fit: contain; }
.hero-titles{ flex:1 1 auto; min-width: 0; }
.hero-ministry{
  color: rgba(255,255,255,.95);
  font-weight: 800;
  font-size: 22px;
  line-height: 1.2;
  letter-spacing: .2px;
  margin: 0 0 6px 0;
  white-space: normal;
}
.hero-app{
  color: rgba(255,255,255,.95);
  font-weight: 700;
  font-size: 18px;
  margin: 0 0 8px 0;
}
.hero-desc{
  color: rgba(255,255,255,.85);
  font-size: 13px;
  margin: 0 0 12px 0;
}
.hero-pill{
  display:inline-flex; align-items:center; gap:8px;
  padding: 7px 12px;
  border-radius: 999px;
  background: rgba(255,255,255,.10);
  border: 1px solid rgba(255,255,255,.16);
  color: rgba(255,255,255,.90);
  font-size: 12px;
}

/* фильтры — чуть компактнее */
.filter-block{
  max-width:1120px;
  margin: 0 auto 8px auto;
}

/* карточки */
.card{
  border: 1px solid rgba(16,24,40,.08);
  border-radius: 16px;
  padding: 14px 14px 12px 14px;
  background: #ffffff;
  box-shadow: 0 8px 18px rgba(16,24,40,.06);
}
.card-title{
  font-size: 15px;
  font-weight: 800;
  margin: 0 0 10px 0;
  color: #0f172a;
}
.meta{
  border-radius: 12px;
  background: #f4f6f9;
  border: 1px solid rgba(16,24,40,.06);
  padding: 10px 10px;
}
.meta-row{
  display:flex; gap:10px;
  font-size: 12.5px;
  margin: 4px 0;
  color: #0f172a;
  align-items:flex-start;
}
.meta-ico{ width:18px; text-align:center; flex:0 0 18px; }
.meta b{ color:#0f172a; }

.badges{
  display:flex; gap:8px; flex-wrap:wrap; margin-top:10px;
}
.badge{
  display:inline-flex; align-items:center; gap:7px;
  padding: 6px 10px;
  border-radius: 999px;
  background: #f4f6ff;
  border: 1px solid rgba(59,130,246,.22);
  font-size: 12px;
  color:#0f172a;
}

/* мобильная адаптация */
@media (max-width: 680px){
  .hero-wrap{ padding: 16px 16px; margin-top: 10px; }
  .hero-row{ gap:12px; }
  .hero-logo{ width:64px; height:64px; }
  .hero-logo img{ width:48px; height:48px; }
  .hero-ministry{ font-size: 18px; }
  .hero-app{ font-size: 16px; }
}
</style>
""",
    unsafe_allow_html=True,
)


# -----------------------------
# DATA LOADING
# -----------------------------
def _normalize_colname(s: str) -> str:
    s = str(s).strip()
    s = s.replace("\n", " ")
    s = re.sub(r"\s+", " ", s)
    return s


def _pick_col(df: pd.DataFrame, preferred: list[str]) -> str | None:
    """Вернуть существующую колонку из списка preferred (точное совпадение по нормализованному имени)."""
    norm_map = {_normalize_colname(c): c for c in df.columns}
    for p in preferred:
        p_norm = _normalize_colname(p)
        if p_norm in norm_map:
            return norm_map[p_norm]
    return None


@st.cache_data(show_spinner=False)
def load_registry() -> pd.DataFrame:
    # 1) пробуем CSV_URL из secrets
    csv_url = st.secrets.get("CSV_URL", "").strip() if hasattr(st, "secrets") else ""
    if csv_url:
        try:
            df = pd.read_csv(csv_url)
            return df
        except Exception:
            pass

    # 2) пробуем локальный XLSX в репозитории
    for f in LOCAL_XLSX_CANDIDATES:
        if os.path.exists(f):
            try:
                df = pd.read_excel(f, sheet_name=0)
                return df
            except Exception:
                continue

    # 3) пусто
    return pd.DataFrame()


def safe_str(x) -> str:
    if x is None:
        return "—"
    try:
        if pd.isna(x):
            return "—"
    except Exception:
        pass
    s = str(x).strip()
    return s if s else "—"


def build_field_map(df: pd.DataFrame) -> dict:
    """
    Привязка к ВАШЕМУ реестру.
    Реальные колонки из вашего файла:
    ID, Отрасль, Район, Наименование_объекта, Ответственный, Статус, Работы_ведутся,
    Ссылка_на_карточку_(Google), Ссылка_на_папку_(Drive), Адрес и др.
    """
    return {
        "id": _pick_col(df, ["ID", "Id", "id"]),
        "sector": _pick_col(df, ["Отрасль", "sector"]),
        "district": _pick_col(df, ["Район", "district"]),
        "name": _pick_col(df, ["Наименование_объекта", "Наименование объекта", "объект", "name"]),
        "address": _pick_col(df, ["Адрес", "address"]),
        "responsible": _pick_col(df, ["Ответственный", "responsible"]),
        "status": _pick_col(df, ["Статус", "status"]),
        "works": _pick_col(df, ["Работы_ведутся", "Работы ведутся", "works"]),
        "card_url": _pick_col(df, ["Ссылка_на_карточку_(Google)", "card_url_text", "card_url"]),
        "folder_url": _pick_col(df, ["Ссылка_на_папку_(Drive)", "folder_url_text", "folder_url"]),
    }


def district_sort_key(d: str) -> tuple:
    """
    Курск первым, Курский район вторым, остальное по алфавиту.
    """
    d0 = (d or "").strip().lower()
    if d0 == "курск":
        return (0, d0)
    if d0 in ["курский", "курский район", "курский р-н"]:
        return (1, d0)
    return (2, d0)


# -----------------------------
# UI: HERO (ВАЖНО: без st.code / без вывода html как текст)
# -----------------------------
def render_hero():
    gerb_html = ""
    if os.path.exists(ASSET_GERB):
        # Streamlit корректно раздает относительные пути в HTML внутри markdown
        gerb_html = f'<img src="{ASSET_GERB}" alt="Герб"/>'
    else:
        gerb_html = "🏛️"

    st.markdown(
        f"""
<div class="hero-wrap">
  <div class="hero-row">
    <div class="hero-logo">{gerb_html}</div>
    <div class="hero-titles">
      <div class="hero-ministry">{APP_TITLE}</div>
      <div class="hero-app">{APP_SUBTITLE}</div>
      <div class="hero-desc">{APP_DESC}</div>
      <div class="hero-pill">📄 Источник данных: Google Sheets (CSV)</div>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


# -----------------------------
# UI: CARD
# -----------------------------
def render_card(row: pd.Series, fm: dict):
    rid = safe_str(row.get(fm["id"])) if fm["id"] else "—"
    name = safe_str(row.get(fm["name"])) if fm["name"] else "—"

    sector = safe_str(row.get(fm["sector"])) if fm["sector"] else "—"
    district = safe_str(row.get(fm["district"])) if fm["district"] else "—"
    address = safe_str(row.get(fm["address"])) if fm["address"] else "—"
    responsible = safe_str(row.get(fm["responsible"])) if fm["responsible"] else "—"
    status = safe_str(row.get(fm["status"])) if fm["status"] else "—"
    works = safe_str(row.get(fm["works"])) if fm["works"] else "—"

    card_url = safe_str(row.get(fm["card_url"])) if fm["card_url"] else "—"
    folder_url = safe_str(row.get(fm["folder_url"])) if fm["folder_url"] else "—"

    # Заголовок: ТОЛЬКО название (без ID) — как вы просили
    st.markdown(f'<div class="card"><div class="card-title">{name}</div>', unsafe_allow_html=True)

    st.markdown(
        f"""
<div class="meta">
  <div class="meta-row"><span class="meta-ico">🏷️</span><span><b>Отрасль:</b> {sector}</span></div>
  <div class="meta-row"><span class="meta-ico">📍</span><span><b>Район:</b> {district}</span></div>
  <div class="meta-row"><span class="meta-ico">🗺️</span><span><b>Адрес:</b> {address}</span></div>
  <div class="meta-row"><span class="meta-ico">👤</span><span><b>Ответственный:</b> {responsible}</span></div>
</div>

<div class="badges">
  <span class="badge">📌 <b>Статус:</b> {status}</span>
  <span class="badge">🛠️ <b>Работы:</b> {works}</span>
</div>
""",
        unsafe_allow_html=True,
    )

    # Кнопки
    c1, c2 = st.columns(2)
    with c1:
        if card_url != "—" and card_url.lower().startswith("http"):
            st.link_button("📄 Открыть карточку", card_url, use_container_width=True)
        else:
            st.button("📄 Открыть карточку", disabled=True, use_container_width=True, key=f"card_disabled_{rid}_{name}")

    with c2:
        if folder_url != "—" and folder_url.lower().startswith("http"):
            st.link_button("📁 Открыть папку", folder_url, use_container_width=True)
        else:
            st.button("📁 Открыть папку", disabled=True, use_container_width=True, key=f"folder_disabled_{rid}_{name}")

    st.markdown("</div>", unsafe_allow_html=True)  # закрыть .card


# -----------------------------
# MAIN
# -----------------------------
render_hero()

df = load_registry()

# если пусто — понятная ошибка + что сделать
if df.empty:
    st.error("Данные не загрузились (реестр пустой). Проверьте CSV_URL в Secrets или наличие .xlsx в репозитории.")
    st.info(
        "1) Streamlit Cloud → Settings → Secrets → добавьте CSV_URL\n"
        "2) Либо положите XLSX в корень репозитория (как резервный источник)\n"
        "3) Убедитесь, что Google Sheet опубликован/доступен по ссылке."
    )
    st.stop()

# нормализуем имена колонок
df.columns = [_normalize_colname(c) for c in df.columns]

fm = build_field_map(df)

# Диагностика (по умолчанию выключена)
with st.sidebar:
    st.markdown("### Диагностика")
    diag = st.toggle("Показать диагностику", value=False, key="diag_toggle")
    if diag:
        st.write("Найденные столбцы:")
        for k, v in fm.items():
            st.write(f"{k}: {v}")

# Подготовка списков фильтров
sector_col = fm["sector"]
district_col = fm["district"]
status_col = fm["status"]

sectors = ["Все"]
districts = ["Все"]
statuses = ["Все"]

if sector_col:
    sectors += sorted([x for x in df[sector_col].dropna().astype(str).unique().tolist() if str(x).strip()])

if district_col:
    dlist = [x for x in df[district_col].dropna().astype(str).unique().tolist() if str(x).strip()]
    dlist = sorted(dlist, key=district_sort_key)
    districts += dlist

if status_col:
    statuses += sorted([x for x in df[status_col].dropna().astype(str).unique().tolist() if str(x).strip()])

# ФИЛЬТРЫ
st.markdown('<div class="filter-block">', unsafe_allow_html=True)
fc1, fc2, fc3 = st.columns(3)

with fc1:
    sector_sel = st.selectbox("🏷️ Отрасль", sectors, index=0, key="sector_sel")
with fc2:
    district_sel = st.selectbox("📍 Район", districts, index=0, key="district_sel")
with fc3:
    status_sel = st.selectbox("📌 Статус", statuses, index=0, key="status_sel")

q = st.text_input("🔎 Поиск (наименование / адрес / ответственный / id)", value="", key="search_q")
st.markdown("</div>", unsafe_allow_html=True)

# Применяем фильтры
fdf = df.copy()

if sector_col and sector_sel != "Все":
    fdf = fdf[fdf[sector_col].astype(str) == str(sector_sel)]

if district_col and district_sel != "Все":
    fdf = fdf[fdf[district_col].astype(str) == str(district_sel)]

if status_col and status_sel != "Все":
    fdf = fdf[fdf[status_col].astype(str) == str(status_sel)]

# Поиск
q0 = q.strip().lower()
if q0:
    search_cols = []
    for key in ["id", "name", "address", "responsible"]:
        if fm.get(key):
            search_cols.append(fm[key])

    def row_match(r):
        for c in search_cols:
            v = safe_str(r.get(c)).lower()
            if q0 in v:
                return True
        return False

    fdf = fdf[fdf.apply(row_match, axis=1)]

st.caption(f"Показано объектов: {len(fdf)} из {len(df)}")

# РЕНДЕР КАРТОЧЕК (2 колонки на десктопе, 1 на мобиле Streamlit сам перестроит)
colA, colB = st.columns(2)
for i, (_, row) in enumerate(fdf.iterrows()):
    target = colA if i % 2 == 0 else colB
    with target:
        render_card(row, fm)
