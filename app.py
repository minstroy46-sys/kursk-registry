import pandas as pd
import streamlit as st

st.set_page_config(page_title="Реестр объектов 2025–2028", layout="wide")

CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQwA5g3ZuBmZlY3vQMbc7nautnpK7c4ioKtTYU_mTskZb6A6nJ_yeokKIvfbVBFH1jTPpzOgoBMD89n/pub?gid=372714191&single=true&output=csv"

st.markdown(
    """
    <style>
      .block-container { padding-top: 1rem; padding-bottom: 1rem; }
      .title { font-size: 1.6rem; font-weight: 700; margin: 0; }
      .subtitle { color: #555; margin-top: .25rem; margin-bottom: 1rem; }
      .card { border:1px solid #e5e7eb; border-radius:14px; padding:14px; margin-bottom:10px; background:#fff; }
      .pill { font-weight:700; font-size:.9rem; padding:4px 10px; border-radius:999px; background:#f3f4f6; border:1px solid #e5e7eb; display:inline-block; }
      .small { color:#666; font-size:.88rem; }
      .meta { color:#222; font-size:1rem; margin-top:6px; }
    </style>
    """,
    unsafe_allow_html=True
)

@st.cache_data(ttl=1800)
def load_df(url: str) -> pd.DataFrame:
    df = pd.read_csv(url, encoding="utf-8")
    df = df.fillna("")
    return df

st.markdown('<div class="title">Система мониторинга объектов строительства 2025–2028</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Минстрой Курской области • Реестр объектов</div>', unsafe_allow_html=True)

try:
    df = load_df(CSV_URL)
except Exception:
    st.error("CSV не загрузился. Проверь: публикация листа registry_public и ссылку pub?output=csv.")
    st.stop()

# Фильтры
c1, c2, c3 = st.columns(3)
sector_list = ["Все"] + sorted([x for x in df["sector"].unique() if x])
district_list = ["Все"] + sorted([x for x in df["district"].unique() if x])
status_list = ["Все"] + sorted([x for x in df["status"].unique() if x])

with c1:
    sector = st.selectbox("Отрасль", sector_list, 0)
with c2:
    district = st.selectbox("Район", district_list, 0)
with c3:
    status = st.selectbox("Статус", status_list, 0)

flt = df.copy()
if sector != "Все":
    flt = flt[flt["sector"] == sector]
if district != "Все":
    flt = flt[flt["district"] == district]
if status != "Все":
    flt = flt[flt["status"] == status]

st.caption(f"Показано объектов: {len(flt)} из {len(df)}")

for _, r in flt.iterrows():
    st.markdown('<div class="card">', unsafe_allow_html=True)

    st.markdown(
        f'<div class="pill">{r.get("id","")}</div> '
        f'<span class="small"> {r.get("sector","")} • {r.get("district","")}</span>',
        unsafe_allow_html=True
    )

    st.markdown(f'<div class="meta"><b>{r.get("name","")}</b></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="small">{r.get("address","")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="small">Ответственный: {r.get("responsible","")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="small">Статус: {r.get("status","")} • Работы: {r.get("work_flag","")}</div>', unsafe_allow_html=True)

    b1, b2 = st.columns(2)
    with b1:
        url = r.get("card_url","")
        st.link_button("📄 Открыть карточку", url, use_container_width=True) if url else st.button("📄 Открыть карточку", disabled=True, use_container_width=True)
    with b2:
        url = r.get("folder_url","")
        st.link_button("📁 Открыть папку", url, use_container_width=True) if url else st.button("📁 Открыть папку", disabled=True, use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)
