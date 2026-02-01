import os
import pandas as pd
import streamlit as st

# =========================
# НАСТРОЙКИ
# =========================
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQwA5g3ZuBmZlY3vQMbc7nautnpK7c4ioKtTYU_mTskZb6A6nJ_yeokKIvfbVBFH1jTPpzOgoBMD89n/pub?gid=372714191&single=true&output=csv"

ASSETS_GERB = os.path.join("assets", "gerb.png")

APP_TITLE = "Министерство восстановления, развития приграничья и строительства Курской области • Реестр объектов"


st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🏗️",
    layout="wide",
)

# =========================
# CSS (ШАПКА + КАРТОЧКИ)
# =========================
st.markdown(
    """
<style>
/* Общий фон */
.block-container { padding-top: 28px; }

/* Шапка */
.header-wrap{
  display:flex;
  align-items:center;           /* герб по центру по высоте */
  gap:18px;
  background: linear-gradient(180deg, #314a86 0%, #2b3f73 100%);
  border-radius: 18px;
  padding: 22px 26px;           /* одинаковые отступы сверху/снизу */
  box-shadow: 0 10px 22px rgba(16,24,40,0.15);
  color: #fff;
  margin-bottom: 18px;
}
.header-gerb{
  width:78px;
  height:78px;
  display:flex;
  align-items:center;
  justify-content:center;
  flex: 0 0 78px;
}
.header-gerb img{
  max-width:78px;
  max-height:78px;
}
.header-title{
  font-size: 34px;
  font-weight: 800;
  line-height: 1.15;
  margin: 0;
}
.header-sub{
  margin-top: 6px;
  opacity: 0.92;
  font-size: 14px;
}
.badge{
  display:inline-block;
  margin-top:10px;
  padding:6px 10px;
  border-radius: 999px;
  background: rgba(255,255,255,0.12);
  border: 1px solid rgba(255,255,255,0.22);
  font-size: 12px;
}

/* Карточки */
.card{
  background:#fff;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 18px;
  padding: 16px 16px 14px 16px;
  box-shadow: 0 10px 20px rgba(15,23,42,0.06);
  margin-bottom: 14px;
}
.card-title{
  font-size: 18px;
  font-weight: 800;
  margin: 0 0 6px 0;
  color: #0f172a;
}
.meta{
  color: rgba(15,23,42,0.75);
  font-size: 13px;
  margin: 2px 0;
}
.pills{
  display:flex;
  gap:8px;
  flex-wrap:wrap;
  margin: 10px 0 10px 0;
}
.pill{
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 12px;
  border: 1px solid rgba(15,23,42,0.12);
  background: rgba(15,23,42,0.03);
}
.pill-ok{ background: rgba(34,197,94,0.12); border-color: rgba(34,197,94,0.25); }
.pill-warn{ background: rgba(245,158,11,0.14); border-color: rgba(245,158,11,0.30); }
.pill-neutral{ background: rgba(59,130,246,0.10); border-color: rgba(59,130,246,0.22); }

.card-actions{
  display:flex;
  gap:10px;
  margin-top: 10px;
}

.photo{
  border-radius: 14px;
  overflow:hidden;
  border: 1px solid rgba(15,23,42,0.08);
  margin: 10px 0 10px 0;
}
.small-note{ font-size:12px; opacity: 0.75; }

</style>
""",
    unsafe_allow_html=True,
)

# =========================
# ЗАГРУЗКА ДАННЫХ
# =========================
@st.cache_data(ttl=300)
def load_data(csv_url: str) -> pd.DataFrame:
    df = pd.read_csv(csv_url)

    # Нормализуем колонки (на всякий случай)
    df.columns = [c.strip() for c in df.columns]

    # Приведем типы/пустоты
    for col in ["sector", "district", "name", "responsible", "status", "work_flag", "address", "card_url", "folder_url"]:
        if col in df.columns:
            df[col] = df[col].astype(str).replace({"nan": "", "None": ""}).fillna("")

    # Если есть фото (опционально)
    if "photo_url" in df.columns:
        df["photo_url"] = df["photo_url"].astype(str).replace({"nan": "", "None": ""}).fillna("")

    return df


def nice_value(v: str, default="—") -> str:
    v = (v or "").strip()
    return v if v else default


def district_sort_key(x: str):
    """г. Курск первым, Курский район вторым, далее по алфавиту."""
    s = (x or "").strip().lower()

    # максимально мягко ловим варианты
    if s in ["г. курск", "курск", "г курск", "город курск"]:
        return (0, "курск")
    if s in ["курский район", "курский р-н", "курский рн", "курский"]:
        return (1, "курский район")

    return (2, s)


def pill_class_status(status: str) -> str:
    s = (status or "").strip().lower()
    if not s:
        return "pill"
    # можно расширять под ваши статусы
    if "в работе" in s or "строит" in s or "идут" in s:
        return "pill pill-ok"
    if "проблем" in s or "риск" in s or "срыв" in s:
        return "pill pill-warn"
    return "pill pill-neutral"


def pill_class_workflag(work_flag: str) -> str:
    s = (work_flag or "").strip().lower()
    if s in ["да", "есть", "ведутся", "true", "1"]:
        return "pill pill-ok"
    if s in ["нет", "не ведутся", "false", "0"]:
        return "pill"
    return "pill pill-neutral"


df = load_data(CSV_URL)

# =========================
# ШАПКА
# =========================
gerb_html = ""
if os.path.exists(ASSETS_GERB):
    # показываем герб из репозитория
    gerb_html = f'<div class="header-gerb"><img src="app/static?file={ASSETS_GERB}" /></div>'
    # В Streamlit Cloud "src=..." напрямую из файлов не всегда работает.
    # Поэтому ниже мы продублируем st.image рядом (надежнее).
else:
    gerb_html = '<div class="header-gerb"></div>'

# Надежный способ показать герб: st.columns + st.image
c1, c2 = st.columns([1, 12])
with c1:
    if os.path.exists(ASSETS_GERB):
        st.image(ASSETS_GERB, width=70)
    else:
        st.write("")  # если нет файла — просто пусто

with c2:
    st.markdown(
        f"""
        <div class="header-wrap">
          <div style="flex:1;">
            <div class="header-title">{APP_TITLE}</div>
            <div class="header-sub">Единый список объектов 2025–2028 с фильтрами и переходом в карточку/папку.</div>
            <div class="badge">Источник данных: Google Sheets (CSV)</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# =========================
# ФИЛЬТРЫ
# =========================
left, mid, right = st.columns(3)

sectors = sorted([s for s in df["sector"].unique().tolist() if s.strip()])
districts = sorted([d for d in df["district"].unique().tolist() if d.strip()], key=district_sort_key)
statuses = sorted([s for s in df["status"].unique().tolist() if s.strip()])

with left:
    sector_sel = st.selectbox("Отрасль", options=["Все"] + sectors, index=0)

with mid:
    district_sel = st.selectbox("Район", options=["Все"] + districts, index=0)

with right:
    status_sel = st.selectbox("Статус", options=["Все"] + statuses, index=0)

q = st.text_input("Поиск (наименование / адрес / ответственный)", value="").strip().lower()

# Применяем фильтры
filtered = df.copy()

if sector_sel != "Все":
    filtered = filtered[filtered["sector"] == sector_sel]

if district_sel != "Все":
    filtered = filtered[filtered["district"] == district_sel]

if status_sel != "Все":
    filtered = filtered[filtered["status"] == status_sel]

if q:
    def match_row(row) -> bool:
        hay = " ".join([
            str(row.get("name", "")),
            str(row.get("address", "")),
            str(row.get("responsible", "")),
        ]).lower()
        return q in hay

    filtered = filtered[filtered.apply(match_row, axis=1)]

st.caption(f"Показано объектов: {len(filtered)} из {len(df)}")

st.divider()

# =========================
# ВЫВОД КАРТОЧЕК (2 в ряд)
# =========================
rows = filtered.to_dict(orient="records")

def render_card(rec: dict):
    name = nice_value(rec.get("name", ""))
    sector = nice_value(rec.get("sector", ""))
    district = nice_value(rec.get("district", ""))
    address = nice_value(rec.get("address", ""))
    responsible = nice_value(rec.get("responsible", ""))
    status = (rec.get("status", "") or "").strip()
    work_flag = (rec.get("work_flag", "") or "").strip()

    card_url = (rec.get("card_url", "") or "").strip()
    folder_url = (rec.get("folder_url", "") or "").strip()

    photo_url = (rec.get("photo_url", "") or "").strip() if "photo_url" in rec else ""

    st.markdown('<div class="card">', unsafe_allow_html=True)

    # ВАЖНО: ID НЕ ПОКАЗЫВАЕМ — только название
    st.markdown(f'<div class="card-title">{name}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="meta"><b>Отрасль:</b> {sector}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="meta"><b>Район:</b> {district}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="meta"><b>Адрес:</b> {address}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="meta"><b>Ответственный:</b> {responsible}</div>', unsafe_allow_html=True)

    # Плашки
    st.markdown(
        f"""
        <div class="pills">
          <div class="{pill_class_status(status)}">Статус: {nice_value(status, "—")}</div>
          <div class="{pill_class_workflag(work_flag)}">Работы: {nice_value(work_flag, "—")}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Фото (если будет колонка photo_url и она заполнена)
    if photo_url:
        try:
            st.markdown('<div class="photo">', unsafe_allow_html=True)
            st.image(photo_url, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        except Exception:
            st.caption("Фото не удалось загрузить (проверь ссылку photo_url).")

    # Кнопки
    b1, b2 = st.columns(2)
    with b1:
        if card_url:
            st.link_button("📄 Открыть карточку", card_url, use_container_width=True)
        else:
            st.button("📄 Открыть карточку", disabled=True, use_container_width=True)

    with b2:
        if folder_url:
            st.link_button("📁 Открыть папку", folder_url, use_container_width=True)
        else:
            st.button("📁 Открыть папку", disabled=True, use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)


# Рендерим 2 карточки в строку
for i in range(0, len(rows), 2):
    col_a, col_b = st.columns(2)
    with col_a:
        render_card(rows[i])
    with col_b:
        if i + 1 < len(rows):
            render_card(rows[i + 1])
        else:
            st.write("")
