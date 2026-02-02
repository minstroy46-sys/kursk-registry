import base64
import os
from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd
import streamlit as st


# =========================
# 0) БАЗОВЫЕ НАСТРОЙКИ
# =========================
st.set_page_config(
    page_title="Реестр объектов",
    page_icon="📋",
    layout="wide",
)

# Скрываем служебные элементы Streamlit (водяные/меню) — насколько это возможно CSS-ом
HIDE_STREAMLIT = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
/* Иногда Streamlit Cloud оставляет маленькую плашку/иконку — полностью убрать нельзя,
   но футер/меню убираются. */
</style>
"""
st.markdown(HIDE_STREAMLIT, unsafe_allow_html=True)


# =========================
# 1) ПРОСТАЯ АВТОРИЗАЦИЯ ПО ПАРОЛЮ
# =========================
def require_password() -> None:
    """
    Требует пароль, заданный в st.secrets["APP_PASSWORD"].
    Пока пароль не введён верно — приложение не показывает данные.
    """
    # Если пароль не задан — не блокируем (на случай локальной отладки)
    app_pwd = st.secrets.get("APP_PASSWORD", "").strip()
    if not app_pwd:
        return

    if st.session_state.get("auth_ok") is True:
        return

    st.markdown(
        """
        <style>
        .auth-box{
            max-width: 520px;
            margin: 60px auto 0 auto;
            padding: 22px 22px;
            border-radius: 16px;
            border: 1px solid rgba(0,0,0,.08);
            box-shadow: 0 10px 30px rgba(0,0,0,.06);
            background: #fff;
        }
        .auth-title{font-size: 22px; font-weight: 700; margin: 0 0 6px 0;}
        .auth-sub{color: rgba(0,0,0,.65); margin: 0 0 16px 0;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="auth-box">', unsafe_allow_html=True)
    st.markdown('<div class="auth-title">🔒 Доступ по паролю</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="auth-sub">Введите пароль для входа в реестр.</div>',
        unsafe_allow_html=True,
    )

    pwd = st.text_input("Пароль", type="password", label_visibility="collapsed")
    col1, col2 = st.columns([1, 2])
    with col1:
        btn = st.button("Войти", use_container_width=True)

    if btn:
        if pwd == app_pwd:
            st.session_state["auth_ok"] = True
            st.rerun()
        else:
            st.error("Неверный пароль.")

    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()


require_password()


# =========================
# 2) ЗАГРУЗКА ДАННЫХ (CSV_URL или fallback на xlsx)
# =========================
@st.cache_data(show_spinner=False)
def load_data() -> Tuple[pd.DataFrame, str]:
    """
    1) Пытаемся прочитать CSV по ссылке из Secrets: CSV_URL
    2) Если не вышло — пытаемся найти .xlsx в репозитории
    Возвращаем (df, source_label)
    """
    # 2.1 CSV из Secrets
    csv_url = st.secrets.get("CSV_URL", "").strip()
    if csv_url:
        try:
            df = pd.read_csv(csv_url)
            return df, "Google Sheets (CSV)"
        except Exception:
            pass

    # 2.2 fallback xlsx в корне репо (если лежит рядом)
    # (ты можешь держать резервный .xlsx, а основной источник всё равно CSV_URL)
    candidates = []
    for p in Path(".").glob("*.xlsx"):
        candidates.append(p)
    # также часто кладут в assets/
    for p in Path("assets").glob("*.xlsx"):
        candidates.append(p)

    if candidates:
        try:
            df = pd.read_excel(candidates[0])
            return df, f"XLSX: {candidates[0].name}"
        except Exception:
            pass

    return pd.DataFrame(), "нет данных"


df_raw, source_label = load_data()


# =========================
# 3) НОРМАЛИЗАЦИЯ КОЛОНОК (чтобы не ломалось при рус/eng заголовках)
# =========================
def _norm(s: str) -> str:
    return (
        str(s).strip().lower()
        .replace("ё", "е")
        .replace("\n", " ")
        .replace("\t", " ")
        .replace("  ", " ")
    )


def detect_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """
    Пытаемся найти нужные колонки в любом наборе заголовков.
    Возвращает словарь ключ->название_колонки_в_df
    """
    if df.empty:
        return {
            "id": None,
            "name": None,
            "sector": None,
            "district": None,
            "address": None,
            "responsible": None,
            "status": None,
            "works": None,
            "card_url": None,
            "folder_url": None,
        }

    cols = list(df.columns)
    nmap = {_norm(c): c for c in cols}

    def pick(*variants: str) -> Optional[str]:
        for v in variants:
            v = _norm(v)
            # точное совпадение
            if v in nmap:
                return nmap[v]
        # частичные эвристики
        for k, orig in nmap.items():
            for v in variants:
                vv = _norm(v)
                if vv and vv in k:
                    return orig
        return None

    return {
        "id": pick("id", "ID", "Идентификатор", "код", "код объекта"),
        "name": pick("наименование_объекта", "наименование объекта", "объект", "название", "name"),
        "sector": pick("отрасль", "sector", "направление"),
        "district": pick("район", "муниципалитет", "district", "территория"),
        "address": pick("адрес", "address", "местоположение"),
        "responsible": pick("ответственный", "ответственные", "responsible", "куратор"),
        "status": pick("статус", "status", "состояние"),
        "works": pick("работы", "works"),
        "card_url": pick("ссылка_на_карточку", "ссылка на карточку", "card_url", "карточка", "google drive карточка"),
        "folder_url": pick("ссылка_на_папку", "ссылка на папку", "folder_url", "папка", "google drive папка"),
    }


col = detect_columns(df_raw)

# Если реестр пустой — показываем сообщение и выходим (но шапку покажем)
# (ниже мы всё равно рисуем hero, поэтому выход — после hero)


# =========================
# 4) ШАПКА (HERO) — СТРОГО СТАБИЛЬНО
# =========================
def img_to_base64(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    data = path.read_bytes()
    return base64.b64encode(data).decode("utf-8")


def render_hero(source_label_local: str) -> None:
    crest_path = Path("assets") / "gerb.png"
    crest_b64 = img_to_base64(crest_path)

    # ВАЖНО: если b64 не найден — всё равно рисуем шапку, но без картинки (чтобы не ломалось)
    crest_html = ""
    if crest_b64:
        crest_html = f'<img alt="Герб" src="data:image/png;base64,{crest_b64}" />'
    else:
        crest_html = '<div class="crest-fallback">Герб</div>'

    st.markdown(
        """
        <style>
        /* Центровка и ширина */
        .hero-wrap{
            max-width: 1180px;
            margin: 28px auto 12px auto;
            padding: 0 12px;
        }
        .hero{
            position: relative;
            border-radius: 18px;
            padding: 22px 26px;
            color: #fff;
            overflow: hidden;
            box-shadow: 0 18px 40px rgba(0,0,0,.12);
            background: linear-gradient(135deg, #0b2a5b 0%, #214a86 55%, #1e3f75 100%);
        }
        /* декоративные пятна */
        .hero:before{
            content:"";
            position:absolute;
            inset:-40px -120px auto auto;
            width: 420px;
            height: 240px;
            background: rgba(255,255,255,.10);
            transform: rotate(12deg);
            border-radius: 36px;
            filter: blur(0px);
        }
        .hero:after{
            content:"";
            position:absolute;
            right:-80px;
            bottom:-80px;
            width: 260px;
            height: 260px;
            background: rgba(255,255,255,.08);
            border-radius: 999px;
        }

        .hero-row{
            display:flex;
            gap: 18px;
            align-items:flex-start;
            position: relative;
            z-index: 2;
        }
        .hero-crest{
            width: 74px;
            height: 74px;
            border-radius: 14px;
            background: rgba(255,255,255,.10);
            border: 1px solid rgba(255,255,255,.18);
            display:flex;
            align-items:center;
            justify-content:center;
            overflow:hidden;
            flex: 0 0 auto;
        }
        .hero-crest img{
            width: 60px;
            height: 60px;
            object-fit: contain;
        }
        .crest-fallback{
            width:60px;height:60px;
            display:flex;align-items:center;justify-content:center;
            font-size: 12px;
            color: rgba(255,255,255,.85);
            border: 1px dashed rgba(255,255,255,.35);
            border-radius: 10px;
        }

        .hero-titles{flex: 1 1 auto;}
        .hero-ministry{
            font-size: 18px;
            font-weight: 800;
            line-height: 1.15;
            margin: 0 0 6px 0;
            letter-spacing: .2px;
        }
        .hero-app{
            font-size: 16px;
            font-weight: 800;
            margin: 0 0 6px 0;
            opacity: .98;
        }
        .hero-sub{
            font-size: 12.5px;
            opacity: .90;
            margin: 0 0 10px 0;
        }
        .hero-pill{
            display:inline-flex;
            gap: 8px;
            align-items:center;
            padding: 6px 10px;
            border-radius: 999px;
            background: rgba(0,0,0,.20);
            border: 1px solid rgba(255,255,255,.18);
            font-size: 12px;
            opacity: .95;
        }

        /* Мобильная адаптация */
        @media (max-width: 640px){
            .hero{padding: 16px 16px;}
            .hero-row{gap: 12px;}
            .hero-crest{width: 62px; height: 62px;}
            .hero-crest img{width: 50px; height: 50px;}
            .hero-ministry{font-size: 16px;}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="hero-wrap">
          <div class="hero">
            <div class="hero-row">
              <div class="hero-crest">{crest_html}</div>
              <div class="hero-titles">
                <div class="hero-ministry">Министерство восстановления, развития приграничья и строительства Курской области</div>
                <div class="hero-app">Реестр объектов</div>
                <div class="hero-sub">Единый список объектов 2025–2028 с быстрыми фильтрами и переходом в карточку/папку.</div>
                <div class="hero-pill">🧾 Источник данных: {source_label_local}</div>
              </div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


render_hero(source_label)

if df_raw.empty:
    st.error("Данные не загрузились (реестр пустой). Проверьте CSV_URL в Secrets или наличие .xlsx в репозитории.")
    st.stop()


# =========================
# 5) ПРИВЕДЕНИЕ ДАННЫХ К ВИДУ (строки, пустые значения)
# =========================
df = df_raw.copy()

# гарантируем строки
for k, c in col.items():
    if c and c in df.columns:
        df[c] = df[c].astype(str).replace({"nan": "", "None": ""}).fillna("")

# =========================
# 6) ФИЛЬТРЫ (КАСКАД)
# =========================
def uniq_sorted(series: pd.Series) -> list:
    vals = [v.strip() for v in series.dropna().astype(str).tolist()]
    vals = [v for v in vals if v and v.lower() != "nan"]
    vals = sorted(set(vals), key=lambda x: x.lower())
    return vals


# Базовые списки
sector_col = col["sector"]
district_col = col["district"]
status_col = col["status"]

# Если колонок нет — делаем безопасно
all_sectors = uniq_sorted(df[sector_col]) if sector_col else []
all_districts = uniq_sorted(df[district_col]) if district_col else []
all_statuses = uniq_sorted(df[status_col]) if status_col else []

filters_wrap_css = """
<style>
.filters-wrap{
    max-width: 1180px;
    margin: 0 auto;
    padding: 0 12px;
}
</style>
"""
st.markdown(filters_wrap_css, unsafe_allow_html=True)
st.markdown('<div class="filters-wrap">', unsafe_allow_html=True)

f1, f2, f3 = st.columns([1, 1, 1])

# 6.1 Отрасль
with f1:
    sector_sel = st.selectbox(
        "🏷️ Отрасль",
        ["Все"] + all_sectors if all_sectors else ["Все"],
        index=0,
    )

df1 = df
if sector_sel != "Все" and sector_col:
    df1 = df1[df1[sector_col].str.strip() == sector_sel].copy()

# 6.2 Район (только где реально есть объекты в df1)
district_options = uniq_sorted(df1[district_col]) if district_col else []
with f2:
    district_sel = st.selectbox(
        "📍 Район",
        ["Все"] + district_options if district_options else ["Все"],
        index=0,
    )

df2 = df1
if district_sel != "Все" and district_col:
    df2 = df2[df2[district_col].str.strip() == district_sel].copy()

# 6.3 Статус (только где реально есть объекты в df2)
status_options = uniq_sorted(df2[status_col]) if status_col else []
with f3:
    status_sel = st.selectbox(
        "📌 Статус",
        ["Все"] + status_options if status_options else ["Все"],
        index=0,
    )

df3 = df2
if status_sel != "Все" and status_col:
    df3 = df3[df3[status_col].str.strip() == status_sel].copy()

# 6.4 Поиск
q = st.text_input("🔎 Поиск (наименование / адрес / ответственный / id)", value="").strip()

def contains_any(row_text: str, needle: str) -> bool:
    return needle.lower() in row_text.lower()

if q:
    search_cols = []
    for key in ("id", "name", "address", "responsible"):
        c = col.get(key)
        if c and c in df3.columns:
            search_cols.append(c)

    if search_cols:
        combined = df3[search_cols].astype(str).agg(" | ".join, axis=1)
        mask = combined.str.lower().str.contains(q.lower(), na=False)
        df3 = df3[mask].copy()

st.markdown("</div>", unsafe_allow_html=True)

# Счетчик
total_cnt = len(df)
shown_cnt = len(df3)
st.markdown(
    f"<div style='max-width:1180px;margin:0 auto;padding:0 12px;color:rgba(0,0,0,.55);font-size:12px;'>"
    f"Показано объектов: <b>{shown_cnt}</b> из <b>{total_cnt}</b>"
    f"</div>",
    unsafe_allow_html=True,
)

st.markdown("<hr style='max-width:1180px;margin:14px auto 18px auto;opacity:.25;'>", unsafe_allow_html=True)


# =========================
# 7) КАРТОЧКА (ОДНА КОЛОНКА) — РОВНАЯ, ВЫТЯНУТАЯ, С МЕСТОМ ПОД ФОТО
# =========================
CARDS_CSS = """
<style>
.cards-wrap{
    max-width: 1180px;
    margin: 0 auto;
    padding: 0 12px 28px 12px;
}
.obj-card{
    border: 1px solid rgba(0,0,0,.08);
    border-radius: 18px;
    padding: 18px 18px 14px 18px;
    background: #fff;
    box-shadow: 0 10px 24px rgba(0,0,0,.06);
    margin-bottom: 14px;
}
.obj-title{
    font-size: 20px;
    font-weight: 800;
    line-height: 1.2;
    margin: 0 0 10px 0;
}
.obj-meta{
    color: rgba(0,0,0,.55);
    font-size: 12px;
    margin: 0 0 10px 0;
}
.obj-grid{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px 18px;
    padding: 10px 12px;
    border-radius: 14px;
    background: rgba(0,0,0,.03);
    border: 1px solid rgba(0,0,0,.06);
}
.obj-item{
    display:flex;
    gap: 8px;
    align-items:flex-start;
    font-size: 13px;
    line-height: 1.25;
}
.obj-k{
    font-weight: 700;
    white-space: nowrap;
}
.badges{
    display:flex;
    gap: 10px;
    margin: 10px 0 12px 0;
    flex-wrap: wrap;
}
.badge{
    display:inline-flex;
    gap: 8px;
    align-items:center;
    padding: 6px 10px;
    border-radius: 999px;
    border: 1px solid rgba(0,0,0,.10);
    background: rgba(0,0,0,.02);
    font-size: 12px;
}
.card-actions{
    display:grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-top: 10px;
}
.placeholder{
    margin-top: 12px;
    padding-top: 10px;
    border-top: 1px dashed rgba(0,0,0,.18);
    color: rgba(0,0,0,.45);
    font-size: 12px;
}
@media (max-width: 820px){
    .obj-grid{grid-template-columns: 1fr;}
    .card-actions{grid-template-columns: 1fr;}
    .obj-title{font-size: 18px;}
}
</style>
"""
st.markdown(CARDS_CSS, unsafe_allow_html=True)


def safe_get(row: pd.Series, key: str) -> str:
    c = col.get(key)
    if not c or c not in row.index:
        return ""
    v = str(row[c]).strip()
    if v.lower() == "nan":
        return ""
    return v


def render_card(row: pd.Series) -> None:
    obj_id = safe_get(row, "id")
    name = safe_get(row, "name") or "Объект"
    sector = safe_get(row, "sector")
    district = safe_get(row, "district")
    address = safe_get(row, "address")
    responsible = safe_get(row, "responsible")
    status = safe_get(row, "status")
    works = safe_get(row, "works")
    card_url = safe_get(row, "card_url")
    folder_url = safe_get(row, "folder_url")

    # HTML часть карточки (визуал)
    st.markdown(
        f"""
        <div class="obj-card">
          <div class="obj-title">{name}</div>
          {"<div class='obj-meta'>ID: " + obj_id + "</div>" if obj_id else ""}
          <div class="obj-grid">
            <div class="obj-item"><span>🏷️</span><span><span class="obj-k">Отрасль:</span> {sector or "—"}</span></div>
            <div class="obj-item"><span>📍</span><span><span class="obj-k">Район:</span> {district or "—"}</span></div>
            <div class="obj-item"><span>🗺️</span><span><span class="obj-k">Адрес:</span> {address or "—"}</span></div>
            <div class="obj-item"><span>👤</span><span><span class="obj-k">Ответственный:</span> {responsible or "—"}</span></div>
          </div>
          <div class="badges">
            <div class="badge">📌 <span class="obj-k">Статус:</span> {status or "—"}</div>
            <div class="badge">🛠️ <span class="obj-k">Работы:</span> {works or "—"}</div>
          </div>
        """,
        unsafe_allow_html=True,
    )

    # Кнопки (Streamlit)
    c1, c2 = st.columns([1, 1])
    with c1:
        if card_url:
            st.link_button("📄 Открыть карточку", card_url, use_container_width=True)
        else:
            st.button("📄 Открыть карточку", use_container_width=True, disabled=True)
    with c2:
        if folder_url:
            st.link_button("📁 Открыть папку", folder_url, use_container_width=True)
        else:
            st.button("📁 Открыть папку", use_container_width=True, disabled=True)

    st.markdown(
        """
        <div class="placeholder">
          Место под фото и дополнительные пункты (заполнишь в реестре — мы красиво выведем позже).
        </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.markdown('<div class="cards-wrap">', unsafe_allow_html=True)

if df3.empty:
    st.info("По выбранным фильтрам объектов не найдено.")
else:
    # ВАЖНО: одна колонка — просто рендерим подряд
    for _, r in df3.iterrows():
        render_card(r)

st.markdown("</div>", unsafe_allow_html=True)
