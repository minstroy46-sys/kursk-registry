import base64
import os
import pandas as pd
import streamlit as st

# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(
    page_title="Реестр объектов — Курская область",
    page_icon="🏛️",
    layout="wide",
)

APP_TITLE_1 = "Министерство восстановления, развития приграничья и строительства Курской области"
APP_TITLE_2 = "Реестр объектов"
APP_SUBTITLE = "Единый список объектов 2025–2028 с быстрыми фильтрами и переходом в карточку/папку."
DATA_BADGE = "Источник данных: Google Sheets (CSV)"

CREST_PATH = os.path.join("assets", "gerb.png")

# -----------------------------
# CSS (ширина + шапка + скрытие футера Streamlit)
# -----------------------------
CUSTOM_CSS = """
<style>
/* Сделать контент шире, чтобы шапка была “на всю страницу” в пределах контента */
section.main > div { padding-top: 1.2rem; }
.block-container {
    max-width: 100% !important;
    padding-left: 2.5rem !important;
    padding-right: 2.5rem !important;
}

/* Спрятать элементы Streamlit (по желанию) */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header { visibility: hidden; }

/* Иногда у Streamlit Cloud появляется badge — пробуем убрать */
[class*="viewerBadge"] { display: none !important; }
[data-testid="stToolbar"] { display: none !important; }

/* HERO */
.hero-wrap {
    width: 100%;
    margin: 0 0 16px 0;
}

.hero {
    position: relative;
    width: 100%;
    border-radius: 18px;
    padding: 18px 22px;
    background: linear-gradient(135deg, #0b2d5c 0%, #1e3f77 55%, #284f86 100%);
    box-shadow: 0 18px 36px rgba(0,0,0,0.18);
    overflow: hidden;
}

/* декоративные “волны”, чтобы не было “ломаной” заливки */
.hero:before {
    content: "";
    position: absolute;
    right: -120px;
    top: -120px;
    width: 420px;
    height: 420px;
    background: radial-gradient(circle at 30% 30%, rgba(255,255,255,0.18), rgba(255,255,255,0.0) 65%);
    transform: rotate(15deg);
}
.hero:after {
    content: "";
    position: absolute;
    left: 40%;
    bottom: -160px;
    width: 520px;
    height: 520px;
    background: radial-gradient(circle at 40% 40%, rgba(255,255,255,0.12), rgba(255,255,255,0.0) 70%);
    transform: rotate(-12deg);
}

.hero-row {
    position: relative;
    display: flex;
    gap: 16px;
    align-items: center;
}

.hero-crest {
    width: 68px;
    height: 68px;
    flex: 0 0 68px;
    border-radius: 14px;
    background: rgba(255,255,255,0.10);
    border: 1px solid rgba(255,255,255,0.18);
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
}

.hero-crest img {
    width: 56px;
    height: 56px;
    object-fit: contain;
}

.hero-titles {
    min-width: 0;
}

.hero-ministry {
    color: rgba(255,255,255,0.95);
    font-weight: 700;
    font-size: 22px;
    line-height: 1.18;
    margin: 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.hero-app {
    color: rgba(255,255,255,0.95);
    font-weight: 800;
    font-size: 18px;
    margin: 6px 0 0 0;
}

.hero-sub {
    color: rgba(255,255,255,0.85);
    font-size: 13px;
    margin: 6px 0 0 0;
    max-width: 980px;
}

.hero-pill {
    display: inline-flex;
    gap: 8px;
    align-items: center;
    padding: 6px 10px;
    border-radius: 999px;
    margin-top: 10px;
    background: rgba(255,255,255,0.12);
    border: 1px solid rgba(255,255,255,0.18);
    color: rgba(255,255,255,0.92);
    font-size: 12px;
    width: fit-content;
}

/* На телефоне переносим заголовок и делаем комфортно */
@media (max-width: 768px) {
  .block-container { padding-left: 1rem !important; padding-right: 1rem !important; }
  .hero-ministry { white-space: normal; font-size: 18px; }
  .hero-app { font-size: 16px; }
  .hero-crest { width: 62px; height: 62px; flex: 0 0 62px; }
  .hero-crest img { width: 52px; height: 52px; }
}
</style>
"""


# -----------------------------
# Helpers
# -----------------------------
def _b64_image(path: str) -> str | None:
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def render_hero():
    crest_b64 = _b64_image(CREST_PATH)
    crest_html = (
        f'<img src="data:image/png;base64,{crest_b64}" alt="Герб" />'
        if crest_b64 else
        '<div style="color:rgba(255,255,255,0.9);font-weight:700;">Герб</div>'
    )

    st.markdown(
        f"""
        {CUSTOM_CSS}
        <div class="hero-wrap">
          <div class="hero">
            <div class="hero-row">
              <div class="hero-crest">{crest_html}</div>
              <div class="hero-titles">
                <div class="hero-ministry">{APP_TITLE_1}</div>
                <div class="hero-app">{APP_TITLE_2}</div>
                <div class="hero-sub">{APP_SUBTITLE}</div>
                <div class="hero-pill">📄 {DATA_BADGE}</div>
              </div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    # приводим имена колонок к "безопасному" виду
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]

    # Если вдруг прилетают русские названия — подстрахуемся маппингом
    ru_map = {
        "ид": "id",
        "id": "id",
        "отрасль": "sector",
        "район": "district",
        "наименование_объекта": "name",
        "наименование объекта": "name",
        "наименование": "name",
        "ответственный": "responsible",
        "статус": "status",
        "работы": "work_flag",
        "work_flag": "work_flag",
        "адрес": "address",
        "ссылка_на_карточку": "card_url",
        "ссылка на карточку": "card_url",
        "card_url": "card_url",
        "ссылка_на_папку": "folder_url",
        "ссылка на папку": "folder_url",
        "folder_url": "folder_url",
    }

    new_cols = []
    for c in df.columns:
        c2 = ru_map.get(c, c)
        new_cols.append(c2)
    df.columns = new_cols

    # гарантируем, что нужные колонки существуют
    required = ["id", "sector", "district", "name", "address", "responsible", "status", "work_flag", "card_url", "folder_url"]
    for col in required:
        if col not in df.columns:
            df[col] = None

    return df


@st.cache_data(ttl=120)
def load_data() -> pd.DataFrame:
    # 1) CSV_URL из Secrets (Google Sheets publish CSV)
    csv_url = None
    try:
        csv_url = st.secrets.get("CSV_URL", None)
    except Exception:
        csv_url = None

    if csv_url:
        df = pd.read_csv(csv_url)
        return normalize_columns(df)

    # 2) fallback: если CSV_URL нет — пробуем взять .xlsx из репозитория
    #    (подстраховка, чтобы приложение не “умирало”)
    xlsx_candidates = [
        "РЕЕСТР_объектов_Курская_область_2025-2028.xlsx",
        "РЕЕСТР_объектов_Курская_область_2025-2028 (7).xlsx",
        "registry.xlsx",
    ]
    for fn in xlsx_candidates:
        if os.path.exists(fn):
            try:
                df = pd.read_excel(fn, sheet_name="registry_public")
                return normalize_columns(df)
            except Exception:
                pass

    return pd.DataFrame(columns=["id","sector","district","name","address","responsible","status","work_flag","card_url","folder_url"])


def safe_text(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, float) and pd.isna(v):
        return "—"
    s = str(v).strip()
    return s if s else "—"


def link_button(label: str, url: str, key: str):
    # Красивые ссылки, без st.markdown
    if not url or safe_text(url) == "—":
        st.button(label, key=key, disabled=True)
        return
    try:
        st.link_button(label, url, use_container_width=True)
    except Exception:
        # fallback для старой версии streamlit
        st.markdown(f'<a href="{url}" target="_blank" style="text-decoration:none;"><button style="width:100%;padding:10px;border-radius:10px;border:1px solid #ddd;background:#fff;cursor:pointer;">{label}</button></a>',
                    unsafe_allow_html=True)


# -----------------------------
# UI
# -----------------------------
render_hero()

df = load_data()

if df.empty or df.shape[0] == 0:
    st.error("Данные не загрузились (реестр пустой). Проверьте источник CSV_URL в Secrets или наличие .xlsx в репозитории.")
    st.stop()

# Фильтры
f1, f2, f3 = st.columns([1, 1, 1])

sectors = ["Все"] + sorted([x for x in df["sector"].dropna().astype(str).unique().tolist() if str(x).strip()])
districts = ["Все"] + sorted([x for x in df["district"].dropna().astype(str).unique().tolist() if str(x).strip()])
statuses = ["Все"] + sorted([x for x in df["status"].dropna().astype(str).unique().tolist() if str(x).strip()])

with f1:
    sector_sel = st.selectbox("🏷️ Отрасль", sectors, index=0)
with f2:
    district_sel = st.selectbox("📍 Район", districts, index=0)
with f3:
    status_sel = st.selectbox("📌 Статус", statuses, index=0)

q = st.text_input("🔎 Поиск (наименование / адрес / ответственный / id)", value="")

# Применяем фильтры
view = df.copy()

if sector_sel != "Все":
    view = view[view["sector"].astype(str) == sector_sel]

if district_sel != "Все":
    view = view[view["district"].astype(str) == district_sel]

if status_sel != "Все":
    view = view[view["status"].astype(str) == status_sel]

if q.strip():
    qq = q.strip().lower()
    mask = (
        view["name"].astype(str).str.lower().str.contains(qq, na=False) |
        view["address"].astype(str).str.lower().str.contains(qq, na=False) |
        view["responsible"].astype(str).str.lower().str.contains(qq, na=False) |
        view["id"].astype(str).str.lower().str.contains(qq, na=False)
    )
    view = view[mask]

st.caption(f"Показано объектов: {len(view)} из {len(df)}")
st.divider()

# Карточки: 2 колонки на ПК, 1 колонка на телефоне (Streamlit сам перестраивает)
cols = st.columns(2)

for i, (_, row) in enumerate(view.iterrows()):
    col = cols[i % 2]

    name = safe_text(row.get("name"))
    obj_id = safe_text(row.get("id"))

    sector = safe_text(row.get("sector"))
    district = safe_text(row.get("district"))
    address = safe_text(row.get("address"))
    responsible = safe_text(row.get("responsible"))
    status = safe_text(row.get("status"))
    work_flag = safe_text(row.get("work_flag"))

    card_url = safe_text(row.get("card_url"))
    folder_url = safe_text(row.get("folder_url"))

    # карточка
    with col:
        with st.container(border=True):
            # Заголовок = НАЗВАНИЕ (как ты просил), а id — маленькой строкой
            st.markdown(f"### {name}")
            st.caption(f"ID: **{obj_id}**")

            meta = f"""
- 🏷️ **Отрасль:** {sector}
- 📍 **Район:** {district}
- 🗺️ **Адрес:** {address}
- 👤 **Ответственный:** {responsible}
            """.strip()
            st.markdown(meta)

            # “чипы” статуса
            cA, cB = st.columns([1, 1])
            with cA:
                st.markdown(f"📌 **Статус:** {status}")
            with cB:
                st.markdown(f"🛠️ **Работы:** {work_flag}")

            b1, b2 = st.columns(2)
            with b1:
                link_button("📄 Открыть карточку", card_url if card_url != "—" else "", key=f"card_{obj_id}_{i}")
            with b2:
                link_button("📁 Открыть папку", folder_url if folder_url != "—" else "", key=f"folder_{obj_id}_{i}")
