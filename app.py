import streamlit as st
import pandas as pd

# ====== НАСТРОЙКИ ======
st.set_page_config(page_title="Реестр объектов", layout="wide")

CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQwA5g3ZuBmZlY3vQMbc7nautnpK7c4ioKtTYU_mTskZb6A6nJ_yeokKIvfbVBFH1jTPpzOgoBMD89n/pub?gid=372714191&single=true&output=csv"

# ====== ЗАГРУЗКА ДАННЫХ ======
@st.cache_data
def load_data():
    df = pd.read_csv(CSV_URL)
    df.columns = df.columns.str.strip()
    return df

df = load_data()

# ====== ЗАГОЛОВОК ======
st.title("Министрой Курской области • Реестр объектов")

# ====== ФИЛЬТРЫ ======
col1, col2, col3 = st.columns(3)

with col1:
    sector_list = ["Все"] + sorted(df["sector"].dropna().unique())
    selected_sector = st.selectbox("Отрасль", sector_list)

with col2:
    district_list = ["Все"] + sorted(df["district"].dropna().unique())
    selected_district = st.selectbox("Район", district_list)

with col3:
    status_list = ["Все"] + sorted(df["status"].dropna().unique())
    selected_status = st.selectbox("Статус", status_list)

# ====== ПРИМЕНЕНИЕ ФИЛЬТРОВ ======
filtered = df.copy()

if selected_sector != "Все":
    filtered = filtered[filtered["sector"] == selected_sector]

if selected_district != "Все":
    filtered = filtered[filtered["district"] == selected_district]

if selected_status != "Все":
    filtered = filtered[filtered["status"] == selected_status]

st.write(f"Показано объектов: {len(filtered)} из {len(df)}")

st.divider()

# ====== ВЫВОД КАРТОЧЕК ======
for _, row in filtered.iterrows():
    with st.container():
        st.markdown(f"### {row['id']} • {row['name']}")
        st.write(f"**Отрасль:** {row['sector']}")
        st.write(f"**Район:** {row['district']}")
        st.write(f"**Адрес:** {row['address']}")
        st.write(f"**Ответственный:** {row['responsible']}")
        st.write(f"**Статус:** {row['status']}")

        card_url = row.get("card_url", "")
        folder_url = row.get("folder_url", "")

        c1, c2 = st.columns(2)

        with c1:
            if pd.notna(card_url) and str(card_url).strip():
                st.link_button("📄 Открыть карточку", card_url, use_container_width=True)
            else:
                st.button("📄 Открыть карточку", disabled=True, use_container_width=True)

        with c2:
            if pd.notna(folder_url) and str(folder_url).strip():
                st.link_button("📁 Открыть папку", folder_url, use_container_width=True)
            else:
                st.button("📁 Открыть папку", disabled=True, use_container_width=True)

        st.divider()
