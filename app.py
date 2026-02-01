import html
import pandas as pd
import streamlit as st

# =========================
# НАСТРОЙКИ
# =========================
st.set_page_config(
    page_title="Министерство восстановления, развития приграничья и строительства Курской области • Реестр объектов",
    page_icon="🏛️",
    layout="wide",
)

CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQwA5g3ZuBmZlY3vQMbc7nautnpK7c4ioKtTYU_mTskZb6A6nJ_yeokKIvfbVBFH1jTPpzOgoBMD89n/pub?gid=372714191&single=true&output=csv"

TITLE_MINISTRY = "Министерство восстановления, развития приграничья и строительства Курской области"
TITLE_APP = "Реестр объектов"
SUBTITLE = "Единый список объектов 2025–2028 с быстрыми фильтрами и переходом в карточку/папку."

# Путь к гербу (варианты):
# 1) Если у вас герб лежит в репозитории рядом с app.py — например assets/gerb.png:
# GERB_PATH = "assets/gerb.png"
# 2) Если хотите временно — можно оставить как None и загрузить позже.
GERB_PATH = "assets/gerb.png"  # <-- положите файл в репозиторий по этому пути


# =========================
# CSS (ШАПКА + КАРТОЧКИ)
# =========================
CSS = """
<style>
/* Убираем лишние отступы Streamlit */
.block-container { padding-top: 1.2rem; padding-bottom: 2rem; }

/* Шапка */
.hero {
  width: 100%;
  border-radius: 18px;
  padding: 22px 26px;
  background: radial-gradient(1100px 500px at 10% 0%, rgba(255,255,255,0.10), rgba(255,255,255,0) 60%),
              linear-gradient(135deg, #1f3b7a 0%, #233c7a 35%, #1c2f63 100%);
  box-shadow: 0 14px 30px rgba(0,0,0,0.18);
  color: #fff;
  position: relative;
  overflow: hidden;
}

/* Лёгкий геометрический паттерн */
.hero:after{
  content:"";
  position:absolute; inset:-120px -120px auto auto;
  width:520px; height:520px;
  background: linear-gradient(135deg, rgba(255,255,255,0.10), rgba(255,255,255,0));
  transform: rotate(25deg);
  border-radius: 40px;
}

/* сетка внутри шапки */
.hero-grid{
  position: relative;
  display:flex;
  gap:18px;
  align-items:center;
}

.hero-logo{
  width:86px; height:86px;
  border-radius: 14px;
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.16);
  display:flex; align-items:center; justify-content:center;
  flex: 0 0 auto;
  overflow:hidden;
}
.hero-logo img{ width:70px; height:70px; object-fit:contain; }

.hero-titles{ display:flex; flex-direction:column; gap:6px; min-width: 0; }
.hero-ministry{
  font-size: 20px; font-weight: 700; line-height: 1.15;
  opacity: 0.98;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.hero-app{
  font-size: 34px; font-weight: 800; line-height: 1.05;
  letter-spacing: 0.2px;
}
.hero-sub{
  font-size: 13.5px; opacity: 0.92;
  max-width: 920px;
}
.pill{
  display:inline-flex; align-items:center; gap:8px;
  margin-top: 10px;
  font-size: 12px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(255,255,255,0.18);
  background: rgba(255,255,255,0.10);
  width: fit-content;
}

/* Фильтры */
.filters-wrap{ margin-top: 14px; }

/* Карточки */
.card {
  border-radius: 16px;
  border: 1px solid rgba(0,0,0,0.08);
  background: #ffffff;
  padding: 14px 14px 12px 14px;
  box-shadow: 0 10px 26px rgba(0,0,0,0.06);
  margin-bottom: 14px;
}

.card-title{
  font-size: 16.5px;
  font-weight: 800;
  line-height: 1.25;
  margin-bottom: 8px;
}

.meta{
  background: #f7f9fc;
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: 12px;
  padding: 10px 12px;
  margin-bottom: 10px;
}
.meta-row{
  display:flex;
  gap:8px;
  align-items:flex-start;
  margin: 3px 0;
  font-size: 13px;
  line-height: 1.35;
}
.meta-ico{ width: 18px; text-align:center; opacity:0.95; }
.meta b{ font-weight: 700; }

/* бейджи */
.badges{ display:flex; gap:8px; flex-wrap: wrap; margin: 8px 0 10px 0; }
.badge{
  display:inline-flex; align-items:center; gap:6px;
  padding: 5px 10px;
  border-radius: 999px;
  font-size: 12px;
  border: 1px solid rgba(0,0,0,0.10);
  background: #ffffff;
}

/* кнопки в строку */
.btnrow{ display:flex; gap:10px; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# =========================
# ЗАГРУЗКА ДАННЫХ
# =========================
@st.cache_data(ttl=300, show_spinner=False)
def load_data(url: str) -> pd.DataFrame:
    df = pd.read_csv(url, dtype=str).fillna("")
    # Нормализуем ожидаемые колонки (если вдруг в CSV чуть другие)
    # Минимум: id, sector, district, name, responsible, status, work_flag, address, card_url, folder_url
    for col in ["id","sector","district","name","responsible","status","work_flag","address","card_url","folder_url"]:
        if col not in df.columns:
            df[col] = ""
    return df


def safe(s: str) -> str:
    """Экранируем текст для HTML, чтобы карточки никогда не ломались."""
    return html.escape("" if s is None else str(s))


def district_sort_key(d: str):
    """
    Требование: Курск первым, потом Курский район, потом по алфавиту.
    """
    x = (d or "").strip().lower()
    if x in ["г. курск", "город курск", "курск"]:
        return (0, x)
    if x in ["курский район", "курский р-н", "курский", "курский р-н."]:
        return (1, x)
    return (2, x)


def render_card(row: pd.Series):
    name = row.get("name","")
    sector = row.get("sector","")
    district = row.get("district","")
    address = row.get("address","")
    responsible = row.get("responsible","")
    status = row.get("status","")
    work_flag = row.get("work_flag","")
    card_url = row.get("card_url","")
    folder_url = row.get("folder_url","")

    # Карточка: НИКАКОГО вывода "id" в заголовке (по вашей просьбе)
    st.markdown('<div class="card">', unsafe_allow_html=True)

    st.markdown(f'<div class="card-title">{safe(name)}</div>', unsafe_allow_html=True)

    meta_html = f"""
    <div class="meta">
      <div class="meta-row"><span class="meta-ico">🏷️</span><span><b>Отрасль:</b> {safe(sector)}</span></div>
      <div class="meta-row"><span class="meta-ico">📍</span><span><b>Район:</b> {safe(district)}</span></div>
      <div class="meta-row"><span class="meta-ico">🗺️</span><span><b>Адрес:</b> {safe(address)}</span></div>
      <div class="meta-row"><span class="meta-ico">👤</span><span><b>Ответственный:</b> {safe(responsible)}</span></div>
    </div>
    """
    st.markdown(meta_html, unsafe_allow_html=True)

    # Бейджи
    badge_status = safe(status) if status.strip() else "—"
    badge_work = safe(work_flag) if work_flag.strip() else "—"

    st.markdown(
        f"""
        <div class="badges">
          <span class="badge">📌 <b>Статус:</b> {badge_status}</span>
          <span class="badge">🛠️ <b>Работы:</b> {badge_work}</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Кнопки
    c1, c2 = st.columns(2)
    with c1:
        if card_url.strip():
            st.link_button("📄 Открыть карточку", card_url, use_container_width=True)
        else:
            st.button("📄 Открыть карточку", disabled=True, use_container_width=True)
    with c2:
        if folder_url.strip():
            st.link_button("📁 Открыть папку", folder_url, use_container_width=True)
        else:
            st.button("📁 Открыть папку", disabled=True, use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)


# =========================
# ШАПКА
# =========================
def header_block():
    logo_html = ""
    try:
        if GERB_PATH:
            logo_html = f'<div class="hero-logo"><img src="data:image/png;base64,{img_to_b64(GERB_PATH)}" /></div>'
    except Exception:
        # если герб не найден — просто не показываем, чтобы ничего не ломалось
        logo_html = ""

    st.markdown(
        f"""
        <div class="hero">
          <div class="hero-grid">
            {logo_html}
            <div class="hero-titles">
              <div class="hero-ministry">{safe(TITLE_MINISTRY)}</div>
              <div class="hero-app">{safe(TITLE_APP)}</div>
              <div class="hero-sub">{safe(SUBTITLE)}</div>
              <div class="pill">🧾 Источник данных: Google Sheets (CSV)</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def img_to_b64(path: str) -> str:
    import base64
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# =========================
# UI
# =========================
header_block()
st.markdown("<div class='filters-wrap'></div>", unsafe_allow_html=True)

df = load_data(CSV_URL)

# Списки для фильтров
sectors = sorted([x for x in df["sector"].unique().tolist() if str(x).strip()])
districts = sorted([x for x in df["district"].unique().tolist() if str(x).strip()], key=district_sort_key)
statuses = sorted([x for x in df["status"].unique().tolist() if str(x).strip()])

col1, col2, col3 = st.columns(3)
with col1:
    sector_choice = st.selectbox("🏷️ Отрасль", ["Все"] + sectors, index=0)
with col2:
    district_choice = st.selectbox("📍 Район", ["Все"] + districts, index=0)
with col3:
    status_choice = st.selectbox("📌 Статус", ["Все"] + statuses, index=0)

query = st.text_input("🔎 Поиск (наименование / адрес / ответственный)", value="").strip().lower()

# Фильтрация
filtered = df.copy()

if sector_choice != "Все":
    filtered = filtered[filtered["sector"] == sector_choice]
if district_choice != "Все":
    filtered = filtered[filtered["district"] == district_choice]
if status_choice != "Все":
    filtered = filtered[filtered["status"] == status_choice]

if query:
    mask = (
        filtered["name"].str.lower().str.contains(query, na=False) |
        filtered["address"].str.lower().str.contains(query, na=False) |
        filtered["responsible"].str.lower().str.contains(query, na=False) |
        filtered["id"].str.lower().str.contains(query, na=False)
    )
    filtered = filtered[mask]

# Сортировка: сначала по району (с вашим приоритетом), потом по отрасли, потом по названию
filtered = filtered.copy()
filtered["_district_key"] = filtered["district"].apply(district_sort_key)
filtered = filtered.sort_values(by=["_district_key", "sector", "name"], ascending=[True, True, True]).drop(columns=["_district_key"])

st.caption(f"Показано объектов: {len(filtered)} из {len(df)}")
st.divider()

# Вывод карточек в 2 колонки
left, right = st.columns(2, gap="large")
rows = filtered.to_dict("records")

for i, r in enumerate(rows):
    target = left if i % 2 == 0 else right
    with target:
        render_card(pd.Series(r))
