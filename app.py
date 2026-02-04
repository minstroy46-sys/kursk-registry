import base64
import re
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Реестр объектов", layout="wide")


# =========================================================
# HELPERS
# =========================================================

def safe_text(v, fallback="—"):
    if v is None:
        return fallback
    try:
        if pd.isna(v):
            return fallback
    except Exception:
        pass
    s = str(v).strip()
    return s if s else fallback


def format_date(v):
    """
    Приводим:
    45902 -> 02.09.2025
    datetime -> 02.09.2025
    текст -> как есть
    """
    if v is None or v == "" or pd.isna(v):
        return "—"

    # если уже дата
    if isinstance(v, (datetime, pd.Timestamp)):
        return v.strftime("%d.%m.%Y")

    # если число (excel serial)
    try:
        if str(v).isdigit():
            base = datetime(1899, 12, 30)
            d = base + timedelta(days=int(v))
            return d.strftime("%d.%m.%Y")
    except:
        pass

    return str(v)


def format_money(v):
    if v is None or v == "" or pd.isna(v):
        return "—"
    try:
        num = float(v)
        return f"{num:,.0f}".replace(",", " ") + " ₽"
    except:
        return str(v)


def norm_col(s):
    return str(s).strip().lower()


def status_class(status_text: str):
    s = norm_col(status_text)
    if "останов" in s:
        return "status-red"
    if "проектир" in s:
        return "status-yellow"
    if "строитель" in s:
        return "status-green"
    return ""


# =========================================================
# LOAD DATA
# =========================================================

@st.cache_data
def load_data():
    try:
        csv_url = st.secrets.get("CSV_URL", None)
    except:
        csv_url = None

    if csv_url:
        try:
            return pd.read_csv(csv_url)
        except:
            return pd.read_csv(csv_url, sep=";")

    candidates = [
        "РЕЕСТР_объектов_Курская_область_2025-2028.xlsx"
    ]

    for name in candidates:
        p = Path(__file__).parent / name
        if p.exists():
            return pd.read_excel(p)

    return pd.DataFrame()


df = load_data()

if df.empty:
    st.error("Реестр не загрузился.")
    st.stop()

df.columns = [str(c).strip() for c in df.columns]


# =========================================================
# STYLES
# =========================================================

st.markdown("""
<style>

.card {
  background: white;
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 18px;
  box-shadow: 0 12px 24px rgba(0,0,0,.08);
  border: 1px solid rgba(0,0,0,.08);
}

.title {
  font-size: 22px;
  font-weight: 800;
  margin-bottom: 8px;
}

.section {
  margin-top: 18px;
  padding-top: 14px;
  border-top: 1px dashed rgba(0,0,0,.12);
}

.section-title {
  font-size: 15px;
  font-weight: 700;
  margin-bottom: 8px;
  color: #1e3a8a;
}

.row {
  font-size: 14px;
  margin-bottom: 4px;
}

.tag {
  display: inline-block;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
  margin-right: 8px;
}

.status-green {
  background: rgba(34,197,94,.15);
}

.status-yellow {
  background: rgba(245,158,11,.18);
}

.status-red {
  background: rgba(239,68,68,.15);
}

.btn {
  display: inline-block;
  padding: 8px 12px;
  margin-right: 10px;
  border-radius: 8px;
  text-decoration: none;
  font-weight: 600;
  border: 1px solid rgba(0,0,0,.12);
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# RENDER CARD
# =========================================================

def render_card(row):

    st.markdown(f"""
    <div class="card">
        <div class="title">{safe_text(row.get("object_name"))}</div>

        <div>
            <span class="tag {status_class(row.get("status"))}">
                📌 {safe_text(row.get("status"))}
            </span>
            <span class="tag">🏷 {safe_text(row.get("sector"))}</span>
            <span class="tag">📍 {safe_text(row.get("district"))}</span>
        </div>

        <div class="section">
            <div class="section-title">📘 Паспорт проекта</div>
            <div class="row"><b>Адрес:</b> {safe_text(row.get("address"))}</div>
            <div class="row"><b>Тип:</b> {safe_text(row.get("object_type"))}</div>
            <div class="row"><b>Ответственный:</b> {safe_text(row.get("responsible"))}</div>
            <div class="row"><b>Мощность:</b> {safe_text(row.get("capacity_seats"))}</div>
            <div class="row"><b>Площадь:</b> {safe_text(row.get("area_m2"))}</div>
        </div>

        <div class="section">
            <div class="section-title">💰 Финансы</div>
            <div class="row"><b>Стоимость контракта:</b> {format_money(row.get("contract_price"))}</div>
            <div class="row"><b>Оплачено:</b> {format_money(row.get("paid"))}</div>
        </div>

        <div class="section">
            <div class="section-title">📅 Сроки</div>
            <div class="row"><b>Контракт:</b> {format_date(row.get("contract_date"))}</div>
            <div class="row"><b>Окончание (план):</b> {format_date(row.get("end_date_plan"))}</div>
            <div class="row"><b>Окончание (факт):</b> {format_date(row.get("end_date_fact"))}</div>
            <div class="row"><b>Обновлено:</b> {format_date(row.get("updated_at"))}</div>
        </div>

        <div class="section">
            <div class="section-title">📂 Документы</div>
            <a class="btn" href="{safe_text(row.get("card_url"),"")}" target="_blank">📄 Карточка</a>
            <a class="btn" href="{safe_text(row.get("folder_url"),"")}" target="_blank">📁 Папка</a>
        </div>

        <div class="section">
            <div class="section-title">⚠ Проблематика</div>
            <div class="row">{safe_text(row.get("issues"))}</div>
        </div>

    </div>
    """, unsafe_allow_html=True)


# =========================================================
# OUTPUT
# =========================================================

for _, r in df.iterrows():
    render_card(r)
