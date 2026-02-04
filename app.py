def money_fmt(v) -> str:
    s = safe_text(v, fallback="—")
    if s == "—":
        return s
    try:
        x = str(s).replace(" ", "").replace("\u00A0", "").replace(",", ".")
        x = float(x)
        return f"{x:,.2f}".replace(",", " ").replace(".00", "") + " ₽"
    except Exception:
        return s if "₽" in s or "руб" in s.lower() else f"{s} ₽"


def date_fmt(v) -> str:
    d = try_parse_date(v)
    return d.strftime("%d.%m.%Y") if d else "—"


def readiness_fmt(v) -> str:
    s = safe_text(v, fallback="—")
    if s == "—":
        return s
    try:
        x = float(str(s).replace(" ", "").replace("\u00A0", "").replace(",", "."))
        if 0 <= x <= 1:
            x *= 100
        return f"{x:.0f}%"
    except Exception:
        if "%" in s:
            return s
        return s


def is_http_url(u: str) -> bool:
    u = str(u or "").strip()
    return u.startswith("http://") or u.startswith("https://")


# Сокращения для гибкого поиска
ABBR = {
    "фап": "фельдшерско акушерский пункт фельдшерский пункт",
    "одкб": "областная детская клиническая больница",
    "црб": "центральная районная больница",
    "фок": "физкультурно оздоровительный комплекс",
    "окб": "областная клиническая больница",
}


def expand_query(q: str) -> str:
    qn = norm_col(q)
    tokens = re.findall(r"[a-zа-я0-9]+", qn, flags=re.IGNORECASE)
    extra = []
    for t in tokens:
        if t in ABBR:
            extra.append(ABBR[t])
    return (qn + " " + " ".join(extra)).strip()


# =============================
# DATA LOADING
# =============================
@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    csv_url = None
    try:
        csv_url = st.secrets.get("CSV_URL", None)
    except Exception:
        csv_url = None

    df = pd.DataFrame()

    if csv_url:
        try:
            df = pd.read_csv(csv_url)
        except Exception:
            try:
                df = pd.read_csv(csv_url, sep=";")
            except Exception:
                df = pd.DataFrame()

    # fallback local
    if df.empty:
        candidates = [
            "РЕЕСТР_объектов_Курская_область_2025-2028.xlsx",
            "РЕЕСТР_объектов_Курская_область_2025-2028 (17).xlsx",
            "registry.xlsx",
            "data.xlsx",
        ]
        for name in candidates:
            p = Path(file).parent / name
            if p.exists():
                try:
                    df = pd.read_excel(p, sheet_name=0)
                    break
                except Exception:
                    pass

    if df is None or df.empty:
        return pd.DataFrame()

    df.columns = [str(c).strip() for c in df.columns]
    return df


def normalize_schema(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    def col(*cands):
        return pick_col(df, list(cands))

    out = pd.DataFrame()

    out["id"] = df[col("id", "ID")] if col("id", "ID") else ""

    out["sector"] = df[col("sector", "отрасль")] if col("sector", "отрасль") else ""
    out["district"] = df[col("district", "район")] if col("district", "район") else ""
    out["name"] = df[col("name", "object_name", "наименование_объекта", "наименование объекта", "объект")] if col(
        "name", "object_name", "наименование_объекта", "наименование объекта", "объект"
    ) else ""
    out["object_type"] = df[col("object_type", "тип", "вид объекта")] if col("object_type", "тип", "вид объекта") else ""
    out["address"] = df[col("address", "адрес")] if col("address", "адрес") else ""
    out["responsible"] = df[col("responsible", "ответственный")] if col("responsible", "ответственный") else ""
    out["status"] = df[col("status", "статус")] if col("status", "статус") else ""
    out["work_flag"] = df[col("work_flag", "работы", "works_in_progress", "works")] if col(
"work_flag", "работы", "works_in_progress", "works"
    ) else ""
    out["issues"] = df[col("issues", "проблемы", "проблемные вопросы")] if col(
        "issues", "проблемы", "проблемные вопросы"
    ) else ""
    out["updated_at"] = df[col("updated_at", "last_update", "обновлено", "updated")] if col(
        "updated_at", "last_update", "обновлено", "updated"
    ) else ""

    out["card_url"] = df[col("card_url", "ссылка_на_карточку_(google)", "ссылка на карточку", "ссылка_на_карточку")] if col(
        "card_url", "ссылка_на_карточку_(google)", "ссылка на карточку", "ссылка_на_карточку"
    ) else ""
    out["folder_url"] = df[col("folder_url", "ссылка_на_папку_(drive)", "ссылка на папку", "ссылка_на_папку")] if col(
        "folder_url", "ссылка_на_папку_(drive)", "ссылка на папку", "ссылка_на_папку"
    ) else ""

    # Паспортные поля
    out["state_program"] = df[col("state_program", "гп", "государственная программа")] if col(
        "state_program", "гп", "государственная программа"
    ) else ""
    out["federal_project"] = df[col("federal_project", "фп", "федеральный проект")] if col(
        "federal_project", "фп", "федеральный проект"
    ) else ""
    out["regional_program"] = df[col("regional_program", "рп", "региональная программа")] if col(
        "regional_program", "рп", "региональная программа"
    ) else ""

    out["agreement"] = df[col("agreement", "соглашение", "номер соглашения")] if col(
        "agreement", "соглашение", "номер соглашения"
    ) else ""
    out["agreement_date"] = df[col("agreement_date", "дата соглашения")] if col(
        "agreement_date", "дата соглашения"
    ) else ""
    out["agreement_amount"] = df[col("agreement_amount", "сумма соглашения")] if col(
        "agreement_amount", "сумма соглашения"
    ) else ""

    out["capacity_seats"] = df[col("capacity_seats", "мощность", "мест", "посещений")] if col(
        "capacity_seats", "мощность", "мест", "посещений"
    ) else ""
    out["area_m2"] = df[col("area_m2", "площадь", "м2", "кв.м")] if col(
        "area_m2", "площадь", "м2", "кв.м"
    ) else ""
    out["target_deadline"] = df[col("target_deadline", "целевой срок")] if col(
        "target_deadline", "целевой срок"
    ) else ""

    out["design"] = df[col("design", "проектирование", "псд")] if col("design", "проектирование", "псд") else ""
    out["psd_cost"] = df[col("psd_cost", "стоимость псд")] if col("psd_cost", "стоимость псд") else ""
    out["designer"] = df[col("designer", "проектировщик")] if col("designer", "проектировщик") else ""

    out["expertise"] = df[col("expertise", "экспертиза")] if col("expertise", "экспертиза") else ""
    out["expertise_conclusion"] = df[col("expertise_conclusion", "заключение экспертизы")] if col(
        "expertise_conclusion", "заключение экспертизы"
    ) else ""
    out["expertise_date"] = df[col("expertise_date", "дата экспертизы")] if col(
        "expertise_date", "дата экспертизы"
    ) else ""

    out["rns"] = df[col("rns", "рнс")] if col("rns", "рнс") else ""
    out["rns_date"] = df[col("rns_date", "дата рнс")] if col("rns_date", "дата рнс") else ""
    out["rns_expiry"] = df[col("rns_expiry", "срок действия рнс")] if col("rns_expiry", "срок действия рнс") else ""

    out["contract"] = df[col("contract", "контракт", "номер контракта")] if col(
        "contract", "контракт", "номер контракта"
    ) else ""
    out["contract_date"] = df[col("contract_date", "дата контракта")] if col(
        "contract_date", "дата контракта"
    ) else ""
    out["contractor"] = df[col("contractor", "подрядчик")] if col("contractor", "подрядчик") else ""
    out["contract_price"] = df[col("contract_price", "цена контракта", "стоимость контракта")] if col(
        "contract_price", "цена контракта", "стоимость контракта"
    ) else ""
out["end_date_plan"] = df[col("end_date_plan", "окончание план")] if col(
        "end_date_plan", "окончание план"
    ) else ""
    out["end_date_fact"] = df[col("end_date_fact", "окончание факт")] if col(
        "end_date_fact", "окончание факт"
    ) else ""
    out["readiness"] = df[col("readiness", "готовность")] if col("readiness", "готовность") else ""
    out["paid"] = df[col("paid", "оплачено")] if col("paid", "оплачено") else ""

    for c in out.columns:
        out[c] = out[c].astype(str).replace({"nan": "", "None": "", "null": ""})

    return out


# =============================
# THEME-AWARE STYLES (Light/Dark)
# =============================
crest_b64 = read_local_crest_b64()

st.markdown(
    """
<style>
:root{
  --bg: #f7f8fb;
  --card: #ffffff;
  --card2: rgba(15,23,42,.03);
  --text: #0f172a;
  --muted: rgba(15,23,42,.72);
  --border: rgba(15,23,42,.12);
  --shadow: rgba(0,0,0,.06);
  --chip-bg: rgba(15,23,42,.05);
  --chip-bd: rgba(15,23,42,.12);
  --btn-bg: rgba(255,255,255,.95);
  --btn-bd: rgba(15,23,42,.14);
  --hr: rgba(15,23,42,.12);
}

@media (prefers-color-scheme: dark){
  :root{
    --bg: #0b1220;
    --card: #111a2b;
    --card2: rgba(255,255,255,.04);
    --text: rgba(255,255,255,.92);
    --muted: rgba(255,255,255,.70);
    --border: rgba(255,255,255,.14);
    --shadow: rgba(0,0,0,.35);
    --chip-bg: rgba(255,255,255,.06);
    --chip-bd: rgba(255,255,255,.14);
    --btn-bg: rgba(17,26,43,.90);
    --btn-bd: rgba(255,255,255,.16);
    --hr: rgba(255,255,255,.14);
  }
}

.block-container { padding-top: 18px !important; max-width: 1200px; }
@media (max-width: 1200px){ .block-container { max-width: 96vw; } }
div[data-testid="stHorizontalBlock"]{ gap: 14px; }

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

html, body, [data-testid="stAppViewContainer"]{
  background: var(--bg) !important;
}

/* HERO */
.hero-wrap{ width:100%; display:flex; justify-content:center; margin-bottom: 10px; }
.hero{
  width: 100%;
  border-radius: 18px;
  padding: 18px 18px;
  background: radial-gradient(1200px 380px at 22% 30%, rgba(60,130,255,.22), rgba(0,0,0,0) 55%),
              linear-gradient(135deg, #0b2a57, #1b4c8f);
  box-shadow: 0 18px 34px rgba(0,0,0,.18);
  position: relative;
  overflow: hidden;
}
.hero:after{
  content:"";
  position:absolute;
  inset:-40px -120px auto auto;
  width: 520px; height: 320px;
  background: rgba(255,255,255,.08);
  transform: rotate(14deg);
  border-radius: 32px;
}
.hero-row{
  display:flex;
  align-items:flex-start;
  gap: 16px;
  position: relative;
  z-index: 2;
}
.hero-crest{
  width: 74px; height: 74px;
  border-radius: 14px;
  background: rgba(255,255,255,.10);
  display:flex;
  align-items:center;
  justify-content:center;
  border: 1px solid rgba(255,255,255,.16);
  flex: 0 0 auto;
}
.hero-crest img{
  width: 56px; height: 56px; object-fit: contain;
  filter: drop-shadow(0 6px 10px rgba(0,0,0,.35));
}
.hero-titles{ flex: 1 1 auto; min-width: 0; }
.hero-ministry{
  color: rgba(255,255,255,.95);
  font-weight: 900;
  font-size: 20px;
  line-height: 1.15;
}
.hero-app{
  margin-top: 6px;
  color: rgba(255,255,255,.92);
  font-weight: 800;
  font-size: 16px;
}
.hero-sub{
  margin-top: 6px;
  color: rgba(255,255,255,.78);
  font-size: 13px;
}
@media (max-width: 900px){
  .hero-ministry{ font-size: 16px; }
  .hero-row{ align-items:center; }
}

/* CARDS */
.card{
  background: var(--card);
  border: 2px solid var(--border);
  border-radius: 16px;
  padding: 16px;
  box-shadow: 0 10px 22px var(--shadow);
  margin-bottom: 12px;
}

.border-green{ border-color: rgba(34,197,94,.50) !important; }
.border-yellow{ border-color: rgba(245,158,11,.50) !important; }
.border-red{ border-color: rgba(239,68,68,.45) !important; }
.border-gray{ border-color: var(--border) !important; }
.title-box{
  border: 1px solid var(--border);
  background: linear-gradient(135deg, rgba(60,130,255,.10), rgba(0,0,0,0));
  border-radius: 12px;
  padding: 10px 12px;
  margin-bottom: 10px;
}
.card-title{
  font-size: 18px;
  line-height: 1.18;
  font-weight: 900;
  margin: 0;
  color: var(--text);
}

.card-subchips{
  display:flex;
  gap: 8px;
  flex-wrap: wrap;
  margin: 10px 0 8px 0;
}
.chip{
  display:inline-flex;
  align-items:center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid var(--chip-bd);
  background: var(--chip-bg);
  font-size: 13px;
  color: var(--text);
}

.card-grid{
  display:grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 18px;
  margin-top: 6px;
}
.card-item{
  font-size: 14px;
  color: var(--text);
}
.card-item b{ color: var(--text); }

.card-tags{
  display:flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 10px;
}
.tag{
  display:inline-flex;
  align-items:center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid var(--chip-bd);
  background: var(--chip-bg);
  font-size: 13px;
  color: var(--text);
  font-weight: 800;
}
.tag-gray{ opacity: .92; }
.tag-green{ background: rgba(34,197,94,.12); border-color: rgba(34,197,94,.22); }
.tag-yellow{ background: rgba(245,158,11,.14); border-color: rgba(245,158,11,.25); }
.tag-red{ background: rgba(239,68,68,.12); border-color: rgba(239,68,68,.22); }

.card-actions{
  display:flex;
  gap: 12px;
  margin-top: 12px;
}
.a-btn{
  flex: 1 1 0;
  display:flex;
  justify-content:center;
  align-items:center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid var(--btn-bd);
  background: var(--btn-bg);
  text-decoration:none !important;
  color: var(--text) !important;
  font-weight: 900;
  font-size: 14px;
  transition: .12s ease-in-out;
}
.a-btn:hover{
  transform: translateY(-1px);
  box-shadow: 0 10px 18px rgba(0,0,0,.10);
}
.a-btn.disabled{
  opacity: .45;
  pointer-events:none;
}

.passport{
  margin-top: 10px;
  padding: 12px;
  border-radius: 14px;
  border: 1px solid var(--border);
  background: var(--card2);
}
.section{
  margin-top: 10px;
  padding: 12px;
  border-radius: 14px;
  border: 1px solid var(--border);
  background: rgba(0,0,0,0);
}
.section-title{
  font-weight: 900;
  color: var(--text);
  margin-bottom: 8px;
  font-size: 14px;
}
.row{
  display:flex;
  gap: 10px;
  flex-wrap: wrap;
  color: var(--text);
  font-size: 13.5px;
  margin: 4px 0;
}
.row b{ color: var(--text); }

.issue-box{
  border: 1px solid rgba(239,68,68,.22);
  background: rgba(239,68,68,.08);
  color: var(--text);
  padding: 10px 12px;
  border-radius: 12px;
  font-size: 13.5px;
  line-height: 1.35;
}

@media (max-width: 900px){
  .card-grid{ grid-template-columns: 1fr; }
  .card-actions{ flex-direction: column; }
}
</style>
""",
    unsafe_allow_html=True,
)


# =============================
# HERO
# =============================
crest_html = (
    f'<img src="data:image/png;base64,{crest_b64}" alt="Герб"/>'
    if crest_b64
    else '<span style="color:rgba(255,255,255,.8);font-weight:800;font-size:12px;">герб</span>'
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
        <div class="hero-sub">Единый список объектов 2025–2028 с быстрыми фильтрами и переходом в карточку.</div>
      </div>
    </div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)


# =============================
# AUTH (PASSWORD GATE)
# =============================
def get_app_password() -> str | None:
    try:
        return st.secrets.get("APP_PASSWORD", None)
    except Exception:
        return None


APP_PASSWORD = get_app_password()

if APP_PASSWORD:
    if "auth_ok" not in st.session_state:
        st.session_state.auth_ok = False
if not st.session_state.auth_ok:
        st.markdown("### 🔐 Доступ к реестру")
        st.write("Введите пароль для просмотра данных.")

        with st.form("login_form", clear_on_submit=False):
            pwd = st.text_input("Пароль", type="password")
            submitted = st.form_submit_button("Войти")

        if submitted:
            if pwd == APP_PASSWORD:
                st.session_state.auth_ok = True
                st.success("Доступ разрешён.")
                st.rerun()
            else:
                st.error("Неверный пароль.")
        st.stop()


# =============================
# LOAD + PREPARE
# =============================
raw = load_data()
if raw.empty:
    st.error(
        "Данные не загрузились (реестр пустой). Проверьте CSV_URL в Secrets "
        "или наличие .xlsx в репозитории."
    )
    st.stop()

df = normalize_schema(raw)

# unique lists
sectors = sorted([x for x in df["sector"].unique().tolist() if str(x).strip()])
districts = sorted([x for x in df["district"].unique().tolist() if str(x).strip()])
statuses = sorted([x for x in df["status"].unique().tolist() if str(x).strip()])

sectors = move_prochie_to_bottom(sectors)

sectors = ["Все"] + sectors
districts = ["Все"] + districts
statuses = ["Все"] + statuses


# =============================
# FILTERS (вне form — чтобы не требовал "submit")
# =============================
c1, c2, c3, c4 = st.columns([1.2, 1.2, 1.2, 1.8])
with c1:
    sector_sel = st.selectbox("🏷️ Отрасль", sectors, index=0, key="f_sector")
with c2:
    district_sel = st.selectbox("📍 Район", districts, index=0, key="f_district")
with c3:
    status_sel = st.selectbox("📌 Статус", statuses, index=0, key="f_status")
with c4:
    q = st.text_input(
        "🔎 Поиск (название / адрес / ответственный / сокращения: ФАП, ОДКБ, ЦРБ, ФОК)",
        value="",
        key="f_search",
        placeholder="Например: фап, одкб, курск, црб…",
    ).strip()

filtered = df.copy()

if sector_sel != "Все":
    filtered = filtered[filtered["sector"].astype(str) == str(sector_sel)]
if district_sel != "Все":
    filtered = filtered[filtered["district"].astype(str) == str(district_sel)]
if status_sel != "Все":
    filtered = filtered[filtered["status"].astype(str) == str(status_sel)]

if q:
    eq = expand_query(q)

    def row_match(r):
        s = " ".join(
            [
                str(r.get("name", "")),
                str(r.get("address", "")),
                str(r.get("responsible", "")),
                str(r.get("district", "")),
                str(r.get("sector", "")),
            ]
        )
        s = norm_col(s)
        # проверяем, что все слова из запроса есть в тексте (чуть более умно)
        tokens = [t for t in norm_col(eq).split() if t]
        return all(t in s for t in tokens) if len(tokens) <= 4 else any(t in s for t in tokens)

    filtered = filtered[filtered.apply(row_match, axis=1)]

st.caption(f"Показано объектов: {len(filtered)} из {len(df)}")


# =============================
# CARD RENDER
# =============================
def render_kv(label: str, value: str):
    st.markdown(f'<div class="row"><b>{label}:</b> {value}</div>', unsafe_allow_html=True)


def render_passport(row: pd.Series):
    issues = safe_text(row.get("issues", ""), fallback="—")

    st.markdown('<div class="passport">', unsafe_allow_html=True)

    # Проблемные вопросы
    st.markdown('<div class="section"><div class="section-title">⚠️ Проблемные вопросы</div>', unsafe_allow_html=True)
    if issues != "—":
        st.markdown(f'<div class="issue-box">{issues}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="row">—</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Программы
    st.markdown('<div class="section"><div class="section-title">🏛️ Программы</div>', unsafe_allow_html=True)
render_kv("ГП/СП", safe_text(row.get("state_program", ""), "—"))
    render_kv("ФП", safe_text(row.get("federal_project", ""), "—"))
    render_kv("РП", safe_text(row.get("regional_program", ""), "—"))
    st.markdown("</div>", unsafe_allow_html=True)

    # Соглашение
    st.markdown('<div class="section"><div class="section-title">🧾 Соглашение</div>', unsafe_allow_html=True)
    render_kv("№", safe_text(row.get("agreement", ""), "—"))
    render_kv("Дата", date_fmt(row.get("agreement_date", "")))
    render_kv("Сумма", money_fmt(row.get("agreement_amount", "")))
    st.markdown("</div>", unsafe_allow_html=True)

    # Параметры
    st.markdown('<div class="section"><div class="section-title">📦 Параметры</div>', unsafe_allow_html=True)
    render_kv("Мощность", safe_text(row.get("capacity_seats", ""), "—"))
    render_kv("Площадь", safe_text(row.get("area_m2", ""), "—"))
    render_kv("Целевой срок", date_fmt(row.get("target_deadline", "")))
    st.markdown("</div>", unsafe_allow_html=True)

    # ПСД / Экспертиза
    st.markdown('<div class="section"><div class="section-title">🗂️ ПСД / Экспертиза</div>', unsafe_allow_html=True)
    render_kv("ПСД", safe_text(row.get("design", ""), "—"))
    render_kv("Стоимость ПСД", money_fmt(row.get("psd_cost", "")))
    render_kv("Проектировщик", safe_text(row.get("designer", ""), "—"))
    render_kv("Экспертиза", safe_text(row.get("expertise", ""), "—"))
    render_kv("Дата экспертизы", date_fmt(row.get("expertise_date", "")))
    render_kv("Заключение", safe_text(row.get("expertise_conclusion", ""), "—"))
    st.markdown("</div>", unsafe_allow_html=True)

    # РНС
    st.markdown('<div class="section"><div class="section-title">🏗️ РНС</div>', unsafe_allow_html=True)
    render_kv("№ РНС", safe_text(row.get("rns", ""), "—"))
    render_kv("Дата", date_fmt(row.get("rns_date", "")))
    render_kv("Срок действия", date_fmt(row.get("rns_expiry", "")))
    st.markdown("</div>", unsafe_allow_html=True)

    # Контракт
    st.markdown('<div class="section"><div class="section-title">🧩 Контракт</div>', unsafe_allow_html=True)
    render_kv("№", safe_text(row.get("contract", ""), "—"))
    render_kv("Дата", date_fmt(row.get("contract_date", "")))
    render_kv("Подрядчик", safe_text(row.get("contractor", ""), "—"))
    render_kv("Цена", money_fmt(row.get("contract_price", "")))
    st.markdown("</div>", unsafe_allow_html=True)

    # Сроки/финансы
    st.markdown('<div class="section"><div class="section-title">⏳ Сроки / финансы</div>', unsafe_allow_html=True)
    render_kv("Окончание (план)", date_fmt(row.get("end_date_plan", "")))
    render_kv("Окончание (факт)", date_fmt(row.get("end_date_fact", "")))
    render_kv("Готовность", readiness_fmt(row.get("readiness", "")))
    render_kv("Оплачено", money_fmt(row.get("paid", "")))
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


def render_card(row: pd.Series, key: str):
    title = safe_text(row.get("name", ""), fallback="Объект")
    sector = safe_text(row.get("sector", ""), fallback="—")
    district = safe_text(row.get("district", ""), fallback="—")
    address = safe_text(row.get("address", ""), fallback="—")
    responsible = safe_text(row.get("responsible", ""), fallback="—")

    status = safe_text(row.get("status", ""), fallback="—")
    work_flag = safe_text(row.get("work_flag", ""), fallback="—")

    card_url = safe_text(row.get("card_url", ""), fallback="")

    # Цвета
    border = status_border(status)
    s_tag = status_tag_class(status)

    w_col = works_color(work_flag)
    w_tag = "tag-gray"
    if w_col == "green":
        w_tag = "tag-green"
    elif w_col == "red":
        w_tag = "tag-red"

    u_col, u_txt = update_color(row.get("updated_at", ""))
    u_tag = "tag-gray"
    if u_col == "green":
        u_tag = "tag-green"
    elif u_col == "yellow":
        u_tag = "tag-yellow"
    elif u_col == "red":
        u_tag = "tag-red"
# Кнопка карточки: ТОЛЬКО если это реальный URL
    if is_http_url(card_url):
        btn_card = f'<a class="a-btn" href="{card_url}" target="_blank" rel="noopener noreferrer">📄 Открыть карточку</a>'
    else:
        btn_card = '<span class="a-btn disabled">📄 Карточка не привязана</span>'

    st.markdown(
        f"""
<div class="card {border}">
  <div class="title-box">
    <h3 class="card-title">{title}</h3>
  </div>

  <div class="card-subchips">
    <span class="chip">🏷️ {sector}</span>
    <span class="chip">📍 {district}</span>
  </div>

  <div class="card-grid">
    <div class="card-item">🗺️ <b>Адрес:</b> {address}</div>
    <div class="card-item">👤 <b>Ответственный:</b> {responsible}</div>
  </div>

  <div class="card-tags">
    <span class="tag {s_tag}">📌 Статус: {status}</span>
    <span class="tag {w_tag}">🛠️ Работы: {work_flag}</span>
    <span class="tag {u_tag}">⏱️ Обновлено: {u_txt}</span>
  </div>

  <div class="card-actions">
    {btn_card}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    # Паспорт управляем состоянием (чинит “свернуть снизу”)
    state_key = f"show_pass_{key}"
    if state_key not in st.session_state:
        st.session_state[state_key] = False

    colA, colB = st.columns([1, 5])
    with colA:
        if st.button(("📋 Паспорт" if not st.session_state[state_key] else "📋 Скрыть"), key=f"btn_pass_{key}"):
            st.session_state[state_key] = not st.session_state[state_key]
            st.rerun()

    if st.session_state[state_key]:
        render_passport(row)
        if st.button("Свернуть паспорт", key=f"btn_close_{key}"):
            st.session_state[state_key] = False
            st.rerun()


# =============================
# OUTPUT
# =============================
for i, (_, r) in enumerate(filtered.iterrows()):
    # внутренний ключ (ID не показываем, но используем чтобы кнопки не конфликтовали)
    rid = safe_text(r.get("id", ""), fallback=f"row_{i}")
    render_card(r, key=f"{rid}_{i}")
