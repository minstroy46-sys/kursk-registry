import os
import re
import glob
import html
import pandas as pd
import streamlit as st


# ----------------------------
# CONFIG
# ----------------------------
st.set_page_config(
    page_title="Реестр объектов — Курская область",
    page_icon="📋",
    layout="wide",
)

DEBUG = False  # поставьте True временно, если надо отладить колонки


# ----------------------------
# HELPERS
# ----------------------------
def _clean_str(x) -> str:
    if x is None:
        return ""
    if isinstance(x, float) and pd.isna(x):
        return ""
    s = str(x).strip()
    if s.lower() in ("nan", "none"):
        return ""
    return s


def _as_display(x, dash="—") -> str:
    s = _clean_str(x)
    return s if s else dash


def _looks_like_url(s: str) -> bool:
    s = _clean_str(s)
    return bool(re.match(r"^https?://", s))


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Приводим названия столбцов к нижнему регистру и '_' вместо пробелов/скобок.
    Потом маппим к стандартным: id, name, sector, district, address, responsible,
    status, works, card_url, folder_url.
    """
    cols = {}
    for c in df.columns:
        cc = str(c).strip().lower()
        cc = re.sub(r"[()\[\]]", "", cc)
        cc = re.sub(r"\s+", "_", cc)
        cc = cc.replace("__", "_")
        cols[c] = cc
    df = df.rename(columns=cols)

    # Синонимы (под разные выгрузки/версии)
    synonyms = {
        "id": [
            "id", "код", "код_объекта", "шифр", "номер", "object_id", "object_number"
        ],
        "name": [
            "наименование_объекта", "наименование", "название", "name", "object_name"
        ],
        "short": [
            "объект", "short", "short_name"
        ],
        "sector": [
            "отрасль", "сфера", "sector"
        ],
        "district": [
            "район", "муниципалитет", "district"
        ],
        "address": [
            "адрес", "местонахождение", "address"
        ],
        "responsible": [
            "ответственный", "куратор", "responsible"
        ],
        "status": [
            "статус", "состояние", "status"
        ],
        "works": [
            "работы_ведутся", "работы", "works"
        ],
        "card_url": [
            "card_url", "card_url_text", "ссылка_на_карточку", "ссылка_на_карточку_google"
        ],
        "folder_url": [
            "folder_url", "folder_url_text", "ссылка_на_папку"
        ],
    }

    def rename_first_match(std_name: str, candidates: list[str]):
        for cand in candidates:
            if cand in df.columns:
                return cand
        return None

    found = {}
    for std, cands in synonyms.items():
        col = rename_first_match(std, cands)
        if col:
            found[std] = col

    # Переименовываем найденные к стандарту
    rename_map = {v: k for k, v in found.items()}
    df = df.rename(columns=rename_map)

    # Создаём отсутствующие стандартные колонки
    for need in ["id", "name", "short", "sector", "district", "address",
                 "responsible", "status", "works", "card_url", "folder_url"]:
        if need not in df.columns:
            df[need] = ""

    # ВАЖНО: если card_url/folder_url не URL-ы, но есть *_text — подставим
    # (на случай, если где-то поменялись колонки)
    # Здесь делаем это мягко: если текущая колонка пустая, ищем альтернативу.
    if "card_url_text" in df.columns:
        mask = df["card_url"].astype(str).str.strip().eq("") | ~df["card_url"].astype(str).str.match(r"^https?://", na=False)
        df.loc[mask, "card_url"] = df.loc[mask, "card_url_text"]

    if "folder_url_text" in df.columns:
        mask = df["folder_url"].astype(str).str.strip().eq("") | ~df["folder_url"].astype(str).str.match(r"^https?://", na=False)
        df.loc[mask, "folder_url"] = df.loc[mask, "folder_url_text"]

    # Подчистим NaN
    df = df.fillna("")

    return df


def _pick_local_xlsx() -> str | None:
    # Берём первый “похожий” xlsx из репозитория (корень)
    # Можно хранить в репо резервную копию реестра.
    candidates = []
    candidates += glob.glob("*.xlsx")
    candidates += glob.glob("data/*.xlsx")
    # приоритет: если есть “реестр” в имени
    candidates_sorted = sorted(
        candidates,
        key=lambda p: (0 if "реестр" in p.lower() else 1, os.path.getmtime(p) if os.path.exists(p) else 0),
    )
    return candidates_sorted[0] if candidates_sorted else None


@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    # 1) Пробуем CSV_URL из Secrets / env
    csv_url = ""
    try:
        csv_url = st.secrets.get("CSV_URL", "")
    except Exception:
        csv_url = ""
    csv_url = csv_url or os.environ.get("CSV_URL", "")

    if _looks_like_url(csv_url):
        df = pd.read_csv(csv_url)
        df = _normalize_columns(df)
        return df

    # 2) Фолбэк: локальный xlsx
    xlsx_path = _pick_local_xlsx()
    if xlsx_path and os.path.exists(xlsx_path):
        df = pd.read_excel(xlsx_path)
        df = _normalize_columns(df)
        return df

    # 3) Совсем нечего читать
    return pd.DataFrame(columns=["id", "name", "sector", "district", "address",
                                 "responsible", "status", "works", "card_url", "folder_url", "short"])


def district_sort_key(val: str):
    s = _clean_str(val).lower()
    # хотим: Курск первым, Курский район вторым, остальное по алфавиту
    if s in ("курск", "г. курск", "город курск"):
        return (0, "курск")
    if s in ("курский район",):
        return (1, "курский район")
    return (2, s)


def inject_css():
    st.markdown(
        """
<style>
/* убрать меню/футер Streamlit (частично) */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

.block-container {padding-top: 18px; padding-bottom: 40px; max-width: 1180px;}
@media (max-width: 900px){
  .block-container {padding-left: 14px; padding-right: 14px;}
}

/* HERO */
.hero-wrap{
  width: 100%;
  margin: 4px 0 16px 0;
}
.hero{
  position: relative;
  border-radius: 18px;
  padding: 18px 20px;
  color: #fff;
  background:
    radial-gradient(1200px 420px at 18% 0%, rgba(255,255,255,0.12), rgba(255,255,255,0) 62%),
    linear-gradient(135deg, #0f2f5f 0%, #163a72 40%, #0c254b 100%);
  box-shadow: 0 10px 28px rgba(0,0,0,.18);
  overflow: hidden;
}
.hero:after{
  content:"";
  position:absolute;
  inset:-60px -120px -80px -120px;
  background: linear-gradient(120deg, rgba(255,255,255,.08) 0%, rgba(255,255,255,0) 35%, rgba(0,0,0,.14) 100%);
  transform: rotate(-6deg);
  pointer-events:none;
}

.hero-inner{
  position: relative;
  z-index: 2;
  display:flex;
  gap: 16px;
  align-items:flex-start;
}

.hero-crest{
  flex: 0 0 auto;
  width: 76px;
  height: 76px;
  border-radius: 14px;
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.14);
  display:flex;
  align-items:center;
  justify-content:center;
}
.hero-crest img{
  width: 60px;
  height: 60px;
  object-fit: contain;
  filter: drop-shadow(0 6px 10px rgba(0,0,0,.25));
}

.hero-titles{
  flex: 1 1 auto;
  min-width: 0;
}

.hero-ministry{
  font-weight: 800;
  letter-spacing: .2px;
  line-height: 1.18;
  font-size: clamp(16px, 2.2vw, 26px);
  margin: 0 0 6px 0;
  /* ВАЖНО: разрешаем переносы, чтобы на телефоне не “резалось” */
  white-space: normal;
  word-break: break-word;
}

.hero-app{
  font-weight: 800;
  font-size: clamp(18px, 2.0vw, 22px);
  opacity: .95;
  margin: 0 0 10px 0;
}

.hero-sub{
  opacity: .92;
  font-size: 13px;
  margin: 0 0 10px 0;
}

.hero-pill{
  display:inline-flex;
  align-items:center;
  gap:8px;
  border-radius: 999px;
  padding: 7px 10px;
  font-size: 12px;
  background: rgba(255,255,255,0.10);
  border: 1px solid rgba(255,255,255,0.14);
}

/* FILTER LABELS */
.flabel{
  font-weight: 800;
  margin: 4px 0 6px 0;
}

/* CARDS */
.card-title{
  font-weight: 800;
  font-size: 15px;
  margin: 0 0 10px 0;
}
.meta{
  border-radius: 12px;
  background: #f5f7fb;
  border: 1px solid rgba(0,0,0,.06);
  padding: 10px 12px;
}
.meta-row{
  display:flex;
  gap:8px;
  align-items:flex-start;
  margin: 6px 0;
  font-size: 13px;
}
.meta-ico{width:18px; text-align:center; margin-top:1px;}
.chips{
  margin-top: 10px;
  display:flex;
  gap: 10px;
  flex-wrap: wrap;
}
.chip{
  display:inline-flex;
  align-items:center;
  gap:8px;
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 12px;
  border: 1px solid rgba(0,0,0,.08);
  background: rgba(255,255,255,.7);
}

/* make link buttons look consistent */
div[data-testid="stLinkButton"] > a{
  border-radius: 10px !important;
  font-weight: 700 !important;
}
</style>
        """,
        unsafe_allow_html=True
    )


def render_hero():
    crest_path = "assets/gerb.png"
    crest_ok = os.path.exists(crest_path)

    crest_html = ""
    if crest_ok:
        crest_html = f'<div class="hero-crest"><img src="data:image/png;base64,{get_image_base64(crest_path)}" alt="Герб"></div>'
    else:
        crest_html = '<div class="hero-crest">🏛️</div>'

    st.markdown(
        f"""
<div class="hero-wrap">
  <div class="hero">
    <div class="hero-inner">
      {crest_html}
      <div class="hero-titles">
        <div class="hero-ministry">Министерство восстановления, развития приграничья и строительства Курской области</div>
        <div class="hero-app">Реестр объектов</div>
        <div class="hero-sub">Единый список объектов 2025–2028 с быстрыми фильтрами и переходом в карточку/папку.</div>
        <div class="hero-pill">📄 Источник данных: Google Sheets (CSV)</div>
      </div>
    </div>
  </div>
</div>
        """,
        unsafe_allow_html=True
    )


@st.cache_data(show_spinner=False)
def get_image_base64(path: str) -> str:
    import base64
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def render_card(row: dict, idx: int):
    name = _as_display(row.get("name"))
    sector = _as_display(row.get("sector"))
    district = _as_display(row.get("district"))
    address = _as_display(row.get("address"))
    responsible = _as_display(row.get("responsible"))
    status = _as_display(row.get("status"))
    works = _as_display(row.get("works"))

    card_url = _clean_str(row.get("card_url"))
    folder_url = _clean_str(row.get("folder_url"))

    # Экранируем текст для HTML
    def esc(x): return html.escape(str(x))

    st.markdown(f'<div class="card-title">{esc(name)}</div>', unsafe_allow_html=True)

    st.markdown(
        f"""
<div class="meta">
  <div class="meta-row"><span class="meta-ico">🏷️</span><span><b>Отрасль:</b> {esc(sector)}</span></div>
  <div class="meta-row"><span class="meta-ico">📍</span><span><b>Район:</b> {esc(district)}</span></div>
  <div class="meta-row"><span class="meta-ico">🗺️</span><span><b>Адрес:</b> {esc(address)}</span></div>
  <div class="meta-row"><span class="meta-ico">👤</span><span><b>Ответственный:</b> {esc(responsible)}</span></div>
</div>
<div class="chips">
  <span class="chip">📌 <b>Статус:</b> {esc(status)}</span>
  <span class="chip">🛠️ <b>Работы:</b> {esc(works)}</span>
</div>
        """,
        unsafe_allow_html=True
    )

    b1, b2 = st.columns(2, gap="small")

    with b1:
        if _looks_like_url(card_url):
            st.link_button("📄 Открыть карточку", card_url, use_container_width=True, key=f"card_{idx}")
        else:
            st.button("📄 Открыть карточку", use_container_width=True, disabled=True, key=f"card_dis_{idx}")

    with b2:
        if _looks_like_url(folder_url):
            st.link_button("📁 Открыть папку", folder_url, use_container_width=True, key=f"folder_{idx}")
        else:
            st.button("📁 Открыть папку", use_container_width=True, disabled=True, key=f"folder_dis_{idx}")


# ----------------------------
# UI
# ----------------------------
inject_css()
render_hero()

df = load_data()

# Если данные пустые — покажем понятную причину
if df.empty:
    st.error(
        "Данные не загрузились (реестр пустой). "
        "Проверьте источник CSV_URL в Secrets или наличие .xlsx в репозитории."
    )
    if DEBUG:
        st.write("df.columns:", list(df.columns))
    st.stop()

# Диагностика (включаем только при DEBUG=True)
if DEBUG:
    with st.sidebar:
        st.markdown("### Диагностика")
        st.write("Колонки:", list(df.columns))
        st.write("Пример строки:", df.head(1).to_dict("records"))

# Фильтры
sectors = sorted([s for s in df["sector"].unique().tolist() if _clean_str(s)])
districts = sorted([d for d in df["district"].unique().tolist() if _clean_str(d)], key=district_sort_key)
statuses = sorted([s for s in df["status"].unique().tolist() if _clean_str(s)])

f1, f2, f3 = st.columns([2, 2, 1.3], gap="medium")

with f1:
    st.markdown('<div class="flabel">🏷️ Отрасль</div>', unsafe_allow_html=True)
    sector_sel = st.selectbox("",
                             ["Все"] + sectors,
                             index=0,
                             key="sector_sel")

with f2:
    st.markdown('<div class="flabel">📍 Район</div>', unsafe_allow_html=True)
    district_sel = st.selectbox("",
                                ["Все"] + districts,
                                index=0,
                                key="district_sel")

with f3:
    st.markdown('<div class="flabel">📌 Статус</div>', unsafe_allow_html=True)
    status_sel = st.selectbox("",
                              ["Все"] + statuses,
                              index=0,
                              key="status_sel")

st.markdown('<div class="flabel">🔎 Поиск (наименование / адрес / ответственный / id)</div>', unsafe_allow_html=True)
q = st.text_input("", value="", key="q", placeholder="Введите текст для поиска...")

# Применяем фильтры
dff = df.copy()

if sector_sel != "Все":
    dff = dff[dff["sector"].astype(str) == sector_sel]

if district_sel != "Все":
    dff = dff[dff["district"].astype(str) == district_sel]

if status_sel != "Все":
    dff = dff[dff["status"].astype(str) == status_sel]

if _clean_str(q):
    qq = _clean_str(q).lower()
    def _row_match(r):
        return any(
            qq in _clean_str(r.get(col)).lower()
            for col in ["name", "address", "responsible", "id", "short", "district", "sector", "status"]
        )
    dff = dff[dff.apply(lambda r: _row_match(r), axis=1)]

st.caption(f"Показано объектов: {len(dff)} из {len(df)}")
st.divider()

# Карточки: по 2 в ряд (на телефоне Streamlit сам складывает в 1 колонку)
rows = dff.to_dict("records")

for i in range(0, len(rows), 2):
    c1, c2 = st.columns(2, gap="large")
    with c1:
        render_card(rows[i], i)
    with c2:
        if i + 1 < len(rows):
            render_card(rows[i + 1], i + 1)
