# app.py
# -*- coding: utf-8 -*-
import os
import html
import base64
import pandas as pd
import streamlit as st

# =========================
# НАСТРОЙКИ (ПРИ НЕОБХОДИМОСТИ МЕНЯТЬ ТОЛЬКО ТУТ)
# =========================
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQwA5g3ZuBmZlY3vQMbc7nautnpK7c4ioKtTYU_mTskZb6A6nJ_yeokKIvfbVBFH1jTPpzOgoBMD89n/pub?gid=372714191&single=true&output=csv"

TITLE_MINISTRY = "Министерство восстановления, развития приграничья и строительства Курской области"
TITLE_APP = "Реестр объектов"
SUBTITLE = "Единый список объектов 2025–2028 с быстрыми фильтрами и переходом в карточку/папку."

# Положите герб рядом с app.py (или в assets/). Название файла должно совпадать.
GERB_PATH = "gerb.png"

# Приоритет района
DISTRICT_PRIORITY = ["г. Курск", "Курский"]

st.set_page_config(
    page_title="Реестр объектов — Курская область",
    page_icon="🏛️",
    layout="wide"
)

# =========================
# HELPERS
# =========================
def _norm(x) -> str:
    if x is None:
        return ""
    if isinstance(x, float) and pd.isna(x):
        return ""
    return str(x).strip()

def _safe(x) -> str:
    """Экранируем текст, чтобы НИ ОДНА строка из CSV не могла сломать HTML."""
    return html.escape(_norm(x), quote=True)

def _clean_url(x: str) -> str:
    x = _norm(x)
    return x if x.lower().startswith("http") else ""

def _district_sort_key(name: str):
    name = _norm(name)
    if not name:
        return (9, "")
    if name == DISTRICT_PRIORITY[0]:
        return (0, name)
    if name == DISTRICT_PRIORITY[1]:
        return (1, name)
    return (2, name.lower())

def _img_to_b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

@st.cache_data(ttl=300, show_spinner=False)
def load_data(url: str) -> pd.DataFrame:
    df = pd.read_csv(url)
    df.columns = [c.strip().lower() for c in df.columns]

    needed = ["id","sector","district","name","responsible","status","work_flag","address","card_url","folder_url"]
    for col in needed:
        if col not in df.columns:
            df[col] = ""

    for col in df.columns:
        df[col] = df[col].apply(_norm)

    df["card_url"] = df["card_url"].apply(_clean_url)
    df["folder_url"] = df["folder_url"].apply(_clean_url)

    df["status"] = df["status"].replace("", "—")
    df["work_flag"] = df["work_flag"].replace("", "—")

    return df


# =========================
# СТИЛИ (ВАЖНО: ЭТО НЕ ЛОМАЕТСЯ И НЕ "РЕЖЕТСЯ")
# =========================
CSS = """
<style>
.block-container { padding-top: 14px; padding-bottom: 30px; }
.stApp { background: #f3f6fb; }
header[data-testid="stHeader"] { background: transparent; }
div[data-testid="stToolbar"] { right: 10px; }

/* ШАПКА на всю ширину — без обрезаний */
.hero-bleed{
  position: relative;
  left: 50%;
  margin-left: -50vw;
  width: 100vw;
  padding: 18px 0 14px 0;
}

.hero-inner{
  max-width: 1320px;
  margin: 0 auto;
  padding: 0 18px;
}

.hero{
  width: 100%;
  border-radius: 22px;
  padding: 22px 24px;
  background:
    radial-gradient(1000px 520px at 10% 0%, rgba(255,255,255,0.12), rgba(255,255,255,0) 60%),
    linear-gradient(135deg, #1f3b7a 0%, #233c7a 35%, #1c2f63 100%);
  box-shadow: 0 14px 30px rgba(0,0,0,0.18);
  color: #fff;
  position: relative;
  overflow: hidden;
}

.hero:after{
  content:"";
  position:absolute;
  right:-160px; top:-170px;
  width:780px; height:580px;
  background: linear-gradient(135deg, rgba(255,255,255,0.14), rgba(255,255,255,0));
  transform: rotate(18deg);
  border-radius: 52px;
}

.hero-grid{
  position: relative;
  display:flex;
  gap:18px;
  align-items:center;
}

.hero-logo{
  width:102px; height:102px;
  border-radius: 18px;
  background: rgba(255,255,255,0.10);
  border: 1px solid rgba(255,255,255,0.18);
  display:flex; align-items:center; justify-content:center;
  flex: 0 0 auto;
  overflow:hidden;
  box-shadow: inset 0 0 0 1px rgba(255,255,255,0.10);
}

.hero-logo img{ width:82px; height:82px; object-fit:contain; }

.hero-titles{ display:flex; flex-direction:column; gap:6px; min-width: 0; }
.hero-ministry{
  font-size: 30px;
  font-weight: 900;
  line-height: 1.12;
  opacity: 0.98;
}
.hero-app{
  font-size: 42px;
  font-weight: 900;
  line-height: 1.04;
  letter-spacing: 0.2px;
}
.hero-sub{
  font-size: 13.5px;
  opacity: 0.92;
  max-width: 980px;
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

/* Блок фильтров */
.filters-card {
  background: rgba(255,255,255,0.62);
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: 16px;
  padding: 12px 14px;
}

/* Карточки */
.obj-card {
  background: #ffffff;
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: 16px;
  padding: 14px 14px 12px 14px;
  box-shadow: 0 6px 18px rgba(0,0,0,0.05);
}

.obj-title{
  font-size: 16px;
  font-weight: 800;
  line-height: 1.2;
  margin-bottom: 10px;
}

.meta-box{
  background: #f4f7fb;
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: 12px;
  padding: 10px 12px;
  margin-bottom: 10px;
}

.meta-row{
  display:flex;
  gap:10px;
  align-items:flex-start;
  margin: 4px 0;
  font-size: 13px;
  color: #0f172a;
}

.meta-ico{ width: 18px; text-align:center; opacity: 0.95; }
.meta-key{ font-weight: 700; margin-right: 6px; }

.badge{
  display:inline-flex;
  align-items:center;
  gap:8px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(15,23,42,0.10);
  background: #ffffff;
  font-size: 12px;
  margin-right: 8px;
}

div.stButton>button, a[role="button"]{
  border-radius: 12px !important;
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# =========================
# ШАПКА (ВАЖНО: ТОЛЬКО unsafe_allow_html=True)
# =========================
def render_header():
    logo_html = ""
    try:
        if GERB_PATH and os.path.exists(GERB_PATH):
            b64 = _img_to_b64(GERB_PATH)
            logo_html = f'<div class="hero-logo"><img src="data:image/png;base64,{b64}" alt="Герб"/></div>'
    except Exception:
        logo_html = ""

    hero_html = (
        f'<div class="hero-bleed">'
        f'  <div class="hero-inner">'
        f'    <div class="hero">'
        f'      <div class="hero-grid">'
        f'        {logo_html}'
        f'        <div class="hero-titles">'
        f'          <div class="hero-ministry">{_safe(TITLE_MINISTRY)}</div>'
        f'          <div class="hero-app">{_safe(TITLE_APP)}</div>'
        f'          <div class="hero-sub">{_safe(SUBTITLE)}</div>'
        f'          <div class="pill">🧾 Источник данных: Google Sheets (CSV)</div>'
        f'        </div>'
        f'      </div>'
        f'    </div>'
        f'  </div>'
        f'</div>'
    )

    # ВАЖНО: ТОЛЬКО так. НИКАКИХ st.code/st.write для hero_html!
    st.markdown(hero_html, unsafe_allow_html=True)

render_header()


# =========================
# ДАННЫЕ
# =========================
df = load_data(CSV_URL)

sectors = sorted([x for x in df["sector"].unique() if x], key=lambda s: s.lower())
districts = sorted([x for x in df["district"].unique() if x], key=_district_sort_key)
statuses = sorted([x for x in df["status"].unique() if x], key=lambda s: s.lower())


# =========================
# ФИЛЬТРЫ
# =========================
st.markdown('<div class="filters-card">', unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
with c1:
    sector_sel = st.selectbox("🏷️ Отрасль", ["Все"] + sectors, index=0)
with c2:
    district_sel = st.selectbox("📍 Район", ["Все"] + districts, index=0)
with c3:
    status_sel = st.selectbox("📌 Статус", ["Все"] + statuses, index=0)

q = st.text_input("🔎 Поиск (наименование / адрес / ответственный / id)", value="").strip()

st.markdown('</div>', unsafe_allow_html=True)


# =========================
# ФИЛЬТРАЦИЯ
# =========================
f = df.copy()

if sector_sel != "Все":
    f = f[f["sector"] == sector_sel]
if district_sel != "Все":
    f = f[f["district"] == district_sel]
if status_sel != "Все":
    f = f[f["status"] == status_sel]
if q:
    qq = q.lower()
    f = f[
        f["name"].str.lower().str.contains(qq, na=False)
        | f["address"].str.lower().str.contains(qq, na=False)
        | f["responsible"].str.lower().str.contains(qq, na=False)
        | f["id"].str.lower().str.contains(qq, na=False)
    ]

st.caption(f"Показано объектов: **{len(f)}** из **{len(df)}**")
st.divider()


# =========================
# ОТРИСОВКА КАРТОЧЕК (НЕ ЛОМАЕТСЯ НА ОДНОЙ СТРОКЕ)
# =========================
def render_card(row: pd.Series):
    name = _safe(row.get("name", ""))
    sector = _safe(row.get("sector", "—"))
    district = _safe(row.get("district", "—"))
    address = _safe(row.get("address", "—"))
    responsible = _safe(row.get("responsible", "—"))
    status = _safe(row.get("status", "—"))
    work_flag = _safe(row.get("work_flag", "—"))

    card_url = _clean_url(row.get("card_url", ""))
    folder_url = _clean_url(row.get("folder_url", ""))

    st.markdown(
        f"""
        <div class="obj-card">
          <div class="obj-title">{name}</div>

          <div class="meta-box">
            <div class="meta-row"><span class="meta-ico">🏷️</span><span><span class="meta-key">Отрасль:</span>{sector}</span></div>
            <div class="meta-row"><span class="meta-ico">📍</span><span><span class="meta-key">Район:</span>{district}</span></div>
            <div class="meta-row"><span class="meta-ico">🗺️</span><span><span class="meta-key">Адрес:</span>{address}</span></div>
            <div class="meta-row"><span class="meta-ico">👤</span><span><span class="meta-key">Ответственный:</span>{responsible}</span></div>
          </div>

          <div style="margin: 6px 0 10px 0;">
            <span class="badge">📌 <b>Статус:</b> {status}</span>
            <span class="badge">🛠️ <b>Работы:</b> {work_flag}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    b1, b2 = st.columns(2)
    with b1:
        if card_url:
            st.link_button("📄 Открыть карточку", card_url, use_container_width=True)
        else:
            st.button("📄 Открыть карточку", use_container_width=True, disabled=True)
    with b2:
        if folder_url:
            st.link_button("📁 Открыть папку", folder_url, use_container_width=True)
        else:
            st.button("📁 Открыть папку", use_container_width=True, disabled=True)


# Стабильная сортировка: район (приоритет) → название
f2 = f.copy()
f2["_dk"] = f2["district"].apply(_district_sort_key)
f2["_nk"] = f2["name"].str.lower()
f2 = f2.sort_values(by=["_dk", "_nk"], ascending=True).drop(columns=["_dk", "_nk"])

cols = st.columns(2)
i = 0
for _, row in f2.iterrows():
    with cols[i % 2]:
        try:
            render_card(row)
        except Exception:
            # Даже если одна строка совсем плохая — приложение не ломаем
            st.error("⚠️ Карточка не отрисовалась из-за некорректных данных в строке.")
            st.write({"id": row.get("id", ""), "name": row.get("name", "")})
    i += 1


# =========================
# БЭКАП (ПОДСКАЗКА)
# =========================
with st.expander("🧷 Как сделать бэкап (чтобы откатиться за минуту)", expanded=False):
    st.markdown(
        """
**Лучший способ — бэкап через GitHub ветку:**

1) Откройте GitHub → репозиторий `kursk-registry` → вкладка **Code**  
2) Слева сверху нажмите на список веток (обычно написано **main**)  
3) Введите имя: `backup-ideal-01`  
4) Нажмите **Create branch: backup-ideal-01 from main**

Теперь это “сейв”. Если что-то сломали — просто возвращаемся к этой ветке.
        """.strip()
    )
