import os
import pandas as pd
import streamlit as st

# =========================
# НАСТРОЙКИ
# =========================
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQwA5g3ZuBmZlY3vQMbc7nautnpK7c4ioKtTYU_mTskZb6A6nJ_yeokKIvfbVBFH1jTPpzOgoBMD89n/pub?gid=372714191&single=true&output=csv"
GERB_PATH = os.path.join("assets", "gerb.png")

MINISTRY_TITLE = "Министерство восстановления, развития приграничья и строительства Курской области"
APP_TITLE = f"{MINISTRY_TITLE} • Реестр объектов"


st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🏗️",
    layout="wide",
)

# =========================
# CSS (ШРИФТ + ШАПКА + UI)
# =========================
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

html, body, [class*="css"]  {
  font-family: 'Inter', system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif !important;
}

.block-container { padding-top: 22px; }

/* ---------- ШАПКА ---------- */
.hero{
  background: linear-gradient(180deg, #2f4b8a 0%, #263e73 100%);
  border-radius: 18px;
  padding: 18px 22px;
  box-shadow: 0 12px 26px rgba(15, 23, 42, 0.14);
  margin-bottom: 14px;
  border: 1px solid rgba(255,255,255,0.10);
}

.hero-inner{
  display:flex;
  align-items:center;     /* вертикально ровно */
  gap:16px;
}

.gerb-box{
  width:74px;
  height:74px;
  border-radius: 16px;
  background: rgba(255,255,255,0.10);
  border: 1px solid rgba(255,255,255,0.16);
  display:flex;
  align-items:center;
  justify-content:center;
  flex: 0 0 74px;
}

.title-top{
  color: rgba(255,255,255,0.92);
  font-weight: 700;
  font-size: 15px;
  line-height: 1.25;
  margin: 0;
}

.title-main{
  color: #ffffff;
  font-weight: 800;
  font-size: 32px;
  line-height: 1.12;
  margin: 6px 0 0 0;
  letter-spacing: -0.2px;
}

.subtitle{
  color: rgba(255,255,255,0.86);
  font-size: 13px;
  margin-top: 8px;
}

.badge{
  display:inline-flex;
  align-items:center;
  gap:8px;
  margin-top: 10px;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(255,255,255,0.10);
  border: 1px solid rgba(255,255,255,0.18);
  color: rgba(255,255,255,0.92);
  font-size: 12px;
}

/* ---------- Карточки ---------- */
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
  margin: 0 0 8px 0;
  color: #0f172a;
}

.meta{
  color: rgba(15,23,42,0.78);
  font-size: 13px;
  margin: 3px 0;
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
.pill-bad{ background: rgba(239,68,68,0.12); border-color: rgba(239,68,68,0.26); }
.pill-neutral{ background: rgba(59,130,246,0.10); border-color: rgba(59,130,246,0.22); }

/* Фото */
.photo{
  border-radius: 14px;
  overflow:hidden;
  border: 1px solid rgba(15,23,42,0.08);
  margin: 10px 0 10px 0;
}

/* Чуть красивее поля */
label { font-weight: 600 !important; }
</style>
""",
    unsafe_allow_html=True,
)

# =========================
# ДАННЫЕ
# =========================
@st.cache_data(ttl=300)
def load_data(csv_url: str) -> pd.DataFrame:
    df = pd.read_csv(csv_url)
    df.columns = [c.strip() for c in df.columns]

    # ожидаемые поля (если где-то пусто — будет просто "")
    cols = ["sector", "district", "name", "responsible", "status", "work_flag", "address", "card_url", "folder_url"]
    for col in cols:
        if col in df.columns:
            df[col] = df[col].astype(str).replace({"nan": "", "None": ""}).fillna("")

    # опционально: фото
    if "photo_url" in df.columns:
        df["photo_url"] = df["photo_url"].astype(str).replace({"nan": "", "None": ""}).fillna("")

    return df


def nice(v: str, default="—") -> str:
    v = (v or "").strip()
    return v if v else default


def district_sort_key(x: str):
    s = (x or "").strip().lower()
    if s in ["г. курск", "курск", "г курск", "город курск"]:
        return (0, "курск")
    if s in ["курский район", "курский р-н", "курский рн", "курский"]:
        return (1, "курский район")
    return (2, s)


def pill_for_status(status: str) -> str:
    s = (status or "").strip().lower()
    if not s:
        return "pill pill-neutral"
    if any(w in s for w in ["риск", "проблем", "срыв", "отстав"]):
        return "pill pill-warn"
    if any(w in s for w in ["заверш", "выполн", "готов", "сдан"]):
        return "pill pill-ok"
    if any(w in s for w in ["останов", "заморож", "не начат"]):
        return "pill pill-bad"
    return "pill pill-neutral"


def pill_for_workflag(work_flag: str) -> str:
    s = (work_flag or "").strip().lower()
    if s in ["да", "есть", "ведутся", "true", "1"]:
        return "pill pill-ok"
    if s in ["нет", "не ведутся", "false", "0"]:
        return "pill"
    return "pill pill-neutral"


df = load_data(CSV_URL)

# =========================
# ШАПКА (ГЕРБ + 2 строки)
# =========================
left, right = st.columns([1.2, 12])

with left:
    # герб строго внутри шапки: если файла нет — покажем заглушку
    if os.path.exists(GERB_PATH):
        st.markdown('<div class="gerb-box">', unsafe_allow_html=True)
        st.image(GERB_PATH, width=52)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="gerb-box" title="Файл не найден: assets/gerb.png">🏛️</div>', unsafe_allow_html=True)

with right:
    st.markdown(
        f"""
        <div class="hero">
          <div class="hero-inner">
            <div style="flex:1;">
              <div class="title-top">{MINISTRY_TITLE}</div>
              <div class="title-main">Реестр объектов</div>
              <div class="subtitle">Единый список объектов 2025–2028 с фильтрами и переходом в карточку/папку.</div>
              <div class="badge">📎 Источник данных: Google Sheets (CSV)</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# =========================
# ФИЛЬТРЫ (с иконками)
# =========================
f1, f2, f3 = st.columns(3)

sectors = sorted([s for s in df.get("sector", pd.Series([])).unique().tolist() if str(s).strip()])
districts = sorted([d for d in df.get("district", pd.Series([])).unique().tolist() if str(d).strip()], key=district_sort_key)
statuses = sorted([s for s in df.get("status", pd.Series([])).unique().tolist() if str(s).strip()])

with f1:
    sector_sel = st.selectbox("🏷️ Отрасль", options=["Все"] + sectors, index=0)

with f2:
    district_sel = st.selectbox("📍 Район", options=["Все"] + districts, index=0)

with f3:
    status_sel = st.selectbox("⚑ Статус", options=["Все"] + statuses, index=0)

q = st.text_input("🔎 Поиск (наименование / адрес / ответственный)", value="").strip().lower()

# =========================
# ФИЛЬТРАЦИЯ
# =========================
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
# КАРТОЧКИ (2 в ряд)
# =========================
rows = filtered.to_dict(orient="records")

def render_card(rec: dict):
    name = nice(rec.get("name", ""))
    sector = nice(rec.get("sector", ""))
    district = nice(rec.get("district", ""))
    address = nice(rec.get("address", ""))
    responsible = nice(rec.get("responsible", ""))
    status = (rec.get("status", "") or "").strip()
    work_flag = (rec.get("work_flag", "") or "").strip()

    card_url = (rec.get("card_url", "") or "").strip()
    folder_url = (rec.get("folder_url", "") or "").strip()
    photo_url = (rec.get("photo_url", "") or "").strip() if "photo_url" in rec else ""

    st.markdown('<div class="card">', unsafe_allow_html=True)

    # ID НЕ ПОКАЗЫВАЕМ — только название
    st.markdown(f'<div class="card-title">{name}</div>', unsafe_allow_html=True)

    st.markdown(f'<div class="meta">🏷️ <b>Отрасль:</b> {sector}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="meta">📍 <b>Район:</b> {district}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="meta">🗺️ <b>Адрес:</b> {address}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="meta">👤 <b>Ответственный:</b> {responsible}</div>', unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="pills">
          <div class="{pill_for_status(status)}">⚑ Статус: {nice(status, "—")}</div>
          <div class="{pill_for_workflag(work_flag)}">🛠️ Работы: {nice(work_flag, "—")}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if photo_url:
        try:
            st.markdown('<div class="photo">', unsafe_allow_html=True)
            st.image(photo_url, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        except Exception:
            st.caption("Фото не удалось загрузить — проверь ссылку в photo_url.")

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

for i in range(0, len(rows), 2):
    c1, c2 = st.columns(2)
    with c1:
        render_card(rows[i])
    with c2:
        if i + 1 < len(rows):
            render_card(rows[i + 1])
        else:
            st.write("")
