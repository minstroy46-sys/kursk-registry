import streamlit as st
import pandas as pd

# ========== НАСТРОЙКИ ==========
st.set_page_config(page_title="Реестр объектов", layout="wide")

CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQwA5g3ZuBmZlY3vQMbc7nautnpK7c4ioKtTYU_mTskZb6A6nJ_yeokKIvfbVBFH1jTPpzOgoBMD89n/pub?gid=372714191&single=true&output=csv"


# ========== УТИЛИТЫ ==========
def clean_str(x):
    """Пустые/NaN -> ''"""
    if pd.isna(x):
        return ""
    s = str(x).strip()
    if s.lower() in ("nan", "none", "null"):
        return ""
    return s


def show_or_dash(x):
    s = clean_str(x)
    return s if s else "—"


def status_color(status: str) -> str:
    s = clean_str(status).lower()
    if not s:
        return "#6b7280"  # gray
    if "выполн" in s or "заверш" in s or "готов" in s:
        return "#16a34a"  # green
    if "работ" in s or "в процессе" in s or "строит" in s:
        return "#2563eb"  # blue
    if "приост" in s or "проблем" in s or "рис" in s:
        return "#dc2626"  # red
    if "план" in s or "подготов" in s:
        return "#f59e0b"  # orange
    return "#6b7280"


def pill(text: str, color: str = "#111827", bg: str = "#e5e7eb"):
    t = clean_str(text)
    if not t:
        t = "—"
    return f"""
    <span style="
        display:inline-block;
        padding:6px 10px;
        margin-right:8px;
        border-radius:999px;
        background:{bg};
        color:{color};
        font-size:12px;
        line-height:1;
        border:1px solid rgba(0,0,0,0.06);
    ">{t}</span>
    """


# ========== СТИЛИ ==========
st.markdown(
    """
<style>
/* общий фон */
.main { background: #ffffff; }

/* заголовок */
.h-title {
  font-size: 34px;
  font-weight: 800;
  margin: 0 0 6px 0;
}
.h-sub {
  color: #6b7280;
  margin: 0 0 18px 0;
}

/* блок фильтров */
.filters {
  padding: 14px 14px 6px 14px;
  border: 1px solid rgba(0,0,0,0.08);
  border-radius: 14px;
  background: #fafafa;
  margin-bottom: 18px;
}

/* карточки-аккордеоны: уменьшаем «воздух» */
div[data-testid="stExpander"] details {
  border-radius: 14px;
  border: 1px solid rgba(0,0,0,0.08);
  background: #ffffff;
}
div[data-testid="stExpander"] summary {
  padding-top: 10px !important;
  padding-bottom: 10px !important;
}
.small-label {
  color:#6b7280;
  font-size: 12px;
}
.value {
  font-size: 14px;
}
hr {
  border: none;
  border-top: 1px solid rgba(0,0,0,0.08);
}
</style>
""",
    unsafe_allow_html=True,
)

# ========== ЗАГРУЗКА ДАННЫХ ==========
@st.cache_data
def load_data():
    df = pd.read_csv(CSV_URL)
    df.columns = df.columns.str.strip()
    # гарантируем наличие колонок
    for col in ["id", "sector", "district", "name", "responsible", "status", "work_flag", "address", "card_url", "folder_url"]:
        if col not in df.columns:
            df[col] = ""
    # чистим NaN
    for c in df.columns:
        df[c] = df[c].apply(clean_str)
    return df


df = load_data()

# ========== ШАПКА ==========
st.markdown('<div class="h-title">Министрой Курской области • Реестр объектов</div>', unsafe_allow_html=True)
st.markdown('<div class="h-sub">Фильтруйте объекты и открывайте карточки/папки одним кликом.</div>', unsafe_allow_html=True)

# ========== ФИЛЬТРЫ + ПОИСК ==========
st.markdown('<div class="filters">', unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns([1.2, 1.2, 1.0, 1.6])

with c1:
    sector_list = ["Все"] + sorted([x for x in df["sector"].unique() if x])
    selected_sector = st.selectbox("Отрасль", sector_list, index=0)

with c2:
    district_list = ["Все"] + sorted([x for x in df["district"].unique() if x])
    selected_district = st.selectbox("Район", district_list, index=0)

with c3:
    status_list = ["Все"] + sorted([x for x in df["status"].unique() if x])
    selected_status = st.selectbox("Статус", status_list, index=0)

with c4:
    q = st.text_input("Поиск (id / название / адрес / ответственный)", value="")

st.markdown("</div>", unsafe_allow_html=True)

# ========== ПРИМЕНЯЕМ ФИЛЬТРЫ ==========
filtered = df.copy()

if selected_sector != "Все":
    filtered = filtered[filtered["sector"] == selected_sector]
if selected_district != "Все":
    filtered = filtered[filtered["district"] == selected_district]
if selected_status != "Все":
    filtered = filtered[filtered["status"] == selected_status]

query = clean_str(q).lower()
if query:
    mask = (
        filtered["id"].str.lower().str.contains(query, na=False)
        | filtered["name"].str.lower().str.contains(query, na=False)
        | filtered["address"].str.lower().str.contains(query, na=False)
        | filtered["responsible"].str.lower().str.contains(query, na=False)
    )
    filtered = filtered[mask]

st.write(f"Показано объектов: **{len(filtered)}** из **{len(df)}**")
st.divider()

# ========== ВЫВОД (КРАСИВЫЕ КАРТОЧКИ) ==========
if len(filtered) == 0:
    st.info("По выбранным фильтрам ничего не найдено.")
else:
    # сортировка по id
    if "id" in filtered.columns:
        filtered = filtered.sort_values(by="id", ascending=True)

    for _, row in filtered.iterrows():
        obj_id = show_or_dash(row.get("id"))
        name = show_or_dash(row.get("name"))
        sector = show_or_dash(row.get("sector"))
        district = show_or_dash(row.get("district"))
        address = show_or_dash(row.get("address"))
        responsible = show_or_dash(row.get("responsible"))
        status = clean_str(row.get("status"))
        work_flag = clean_str(row.get("work_flag"))

        card_url = clean_str(row.get("card_url"))
        folder_url = clean_str(row.get("folder_url"))

        # заголовок аккордеона
        status_txt = status if status else "—"
        sc = status_color(status_txt)
        header = f"{obj_id} • {name}"

        with st.expander(header, expanded=False):
            # бейджи
            st.markdown(
                pill(sector, color="#111827", bg="#eef2ff")
                + pill(district, color="#111827", bg="#ecfeff")
                + pill(status_txt, color="#ffffff", bg=sc),
                unsafe_allow_html=True,
            )

            st.markdown(
                f"""
<div class="small-label">Адрес</div>
<div class="value">{address}</div>
<br/>
<div class="small-label">Ответственный</div>
<div class="value">{responsible}</div>
<br/>
<div class="small-label">Работы</div>
<div class="value">{work_flag if work_flag else "—"}</div>
""",
                unsafe_allow_html=True,
            )

            st.markdown("<hr/>", unsafe_allow_html=True)

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
