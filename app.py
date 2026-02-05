import React, { useState, useEffect } from 'react';

// Mock data structure matching the normalized schema from the provided registry
const mockData = [
  {
    id: "ZDR-001",
    sector: "Здравоохранение",
    district: "Курск",
    name: "«Многопрофильная областная детская клиническая больница 3 уровня в г. Курске»",
    object_type: "ОДКБ 3 ур., Курск",
    address: "г. Курск, проспект Надежды Плевицкой",
    responsible: "Бороздина Е.Н.",
    status: "ведется строительство",
    work_flag: "Да",
    issues: "В настоящее время контракт находится в стадии расторжения. На текущую дату завершена выверка объемов выполненных работ в плотном взаимодействии с представителями РосСтройКонтроль, акты по выполненным объемам работ подписаны ОКУ «УКС Курской области», представителем РосСтройКонтроль и подрядной организацией, ведется определение стоимости выполненных работ",
    updated_at: "2026-02-04",
    card_url: "https://docs.google.com/spreadsheets/d/1FPhqCrtgBcWKTV4sxdeklxjT-pegM-TKW7XTwIL3elM/edit?gid=1589732326#gid=1589732326",
    card_url_text: "Многопрофильная областная детская клиническая больница 3 уровня, г. Курске",
    state_program: "ГП РФ \"Развитие здравоохранения\"",
    federal_project: "ФП \"Развитие инфраструктуры здравоохранения\"",
    regional_program: "РП \"Развитие здравоохранения в Курской области\"",
    agreement: "№ 056-09-2026-1794 от 30.12.2025 года с Министерством здравоохранения РФ",
    agreement_date: "2025-12-30",
    agreement_amount: "4034974836",
    capacity_seats: "320 коек",
    area_m2: "64595,23 м2",
    target_deadline: "2031-01-01",
    design: "да",
    psd_cost: "54192700",
    designer: "АО \"Строительный холдинг \"Тезис\"",
    expertise: "да",
    expertise_conclusion: "№ 46-1-1-3-008788-2025 от 20.02.2025 года выдано ФАУ \"Главгосэкспертиза\"",
    expertise_date: "2025-02-20",
    rns: "№ 46-29-448-2025 от 01.07.2025 выдано Комитет архитектуры и градостроительства города Курска",
    rns_date: "2025-07-01",
    rns_expiry: "2027-12-31",
    contract: "ГК №73 от 29.03.2022 на проектирование, строительство и ввод в эксплуатацию",
    contract_date: "2022-03-29",
    contractor: "АО \"Строительный холдинг \"Тезис\"",
    contract_price: "8293070613.86",
    end_date_plan: "2027-12-31",
    end_date_fact: "2027-12-31",
    readiness: "0.38",
    paid: "",
    folder_url: "https://drive.google.com/drive/folders/1IBdbDEQ07L2FKG-5YupjPKoc_n6JyMbf"
  },
  {
    id: "OBR-003",
    sector: "Образование",
    district: "Курский",
    name: "Новопоселеновская средняя общеобразовательная школа на 500 мест",
    object_type: "СОШ 500, 1-е Цветово",
    address: "Курская область, Курский район, д. 1-е Цветово",
    responsible: "Гуляева А.С.",
    status: "строительство остановлено",
    work_flag: "Нет",
    issues: "1) Работы на объекте не ведутся. 2) Не обеспечено финансирование оснащения, контракт не заключен.",
    updated_at: "2026-02-05",
    card_url: "https://docs.google.com/spreadsheets/d/1IF2RVNmqXQCOrSGgvFuylsJ6adiHcL1ZU28AL6wIQko/edit?gid=1589732326#gid=1589732326",
    card_url_text: "Новопоселеновская средняя общеобразовательная школа на 500 мест, Курский район",
    state_program: "ГП РФ \"Развитие образования\"",
    federal_project: "ФП \"Все лучшее детям\"",
    regional_program: "РП \"Развитие образования в Курской области\"",
    agreement: "№ 073-09-2025-457 от 26.12.2024 с Министерством просвещения РФ",
    agreement_date: "2024-12-26",
    agreement_amount: "868743600",
    capacity_seats: "500 посещений",
    area_m2: "15 460,17 м2.",
    target_deadline: "2027-12-31",
    design: "да",
    psd_cost: "6427420",
    designer: "ОБУ «КУРСКГРАЖДАНПРОЕКТ»",
    expertise: "да",
    expertise_conclusion: "№46-1-1-3-024002-2023 от 05.05.2023, выданное АУ КО \"Государственная экспертиза проектов Курской области\"",
    expertise_date: "2023-05-05",
    rns: "№ 46-11-131-2025 от 18.09.2025, выдано Министерство архитектуры и градостроительства Курской области",
    rns_date: "2025-09-18",
    rns_expiry: "2027-04-18",
    contract: "МК от 02.09.2025 № 14",
    contract_date: "2025-09-02",
    contractor: "АО «УКС инженерных коммуникаций, сооружений и дорог»",
    contract_price: "882623791.57",
    end_date_plan: "2027-04-01",
    end_date_fact: "2027-12-31",
    readiness: "0",
    paid: "",
    folder_url: "https://drive.google.com/drive/folders/1F3nxZv3lws3CnI2W5NpRjCXSYT3aJAxD"
  },
  {
    id: "KUL-003",
    sector: "Культура",
    district: "Курск",
    name: "Экспозиционный корпус Курского областного краеведческого музея",
    object_type: "Краеведческий музей, Курск",
    address: "г. Курск, ул. Луначарского, 8, здание литер В",
    responsible: "Сафонова Л.А.",
    status: "ведется строительство",
    work_flag: "Да",
    issues: "1) Работы на объекте не ведутся. 2) Не обеспечено финансирование оснащения, контракт не заключен.",
    updated_at: "2026-02-04",
    card_url: "https://docs.google.com/spreadsheets/d/1cQ0eeBEeGTF_j1iYzr8MIoYiDQxctgbeOGw1S_OMItA/edit?gid=1589732326#gid=1589732326",
    card_url_text: "Экспозиционный корпус Курского областного краеведческого музея, г. Курск",
    state_program: "ГП РФ \"Развитие культуры\"",
    federal_project: "ФП \"Развитие инфраструктуры в сфере культуры\"",
    regional_program: "создание и (или) модернизация инфраструктуры в сфере культуры региональной (муниципальной) собственности",
    agreement: "№ 054-09-2026-544 от 26.12.2025",
    agreement_date: "2025-12-26",
    agreement_amount: "1458369000",
    capacity_seats: "600 посещений",
    area_m2: "8619 м2.",
    target_deadline: "2027-12-31",
    design: "да",
    psd_cost: "6427420",
    designer: "ООО \"ВЕК\"",
    expertise: "да",
    expertise_conclusion: "№46-1-1-2-083067-2024 от 30.12.2024",
    expertise_date: "2024-12-30",
    rns: "№ 46-RU46302000-1-2022 от 18.04.2022",
    rns_date: "2022-04-18",
    rns_expiry: "2027-12-31",
    contract: "МК от 02.09.2025 № 14",
    contract_date: "2025-09-02",
    contractor: "АО «УКС инженерных коммуникаций, сооружений и дорог»",
    contract_price: "882623791.57",
    end_date_plan: "2027-04-01",
    end_date_fact: "2027-12-31",
    readiness: "0",
    paid: "",
    folder_url: "https://drive.google.com/drive/folders/1LovfdlAUDU-u75G9VAXZWLTdvXwD_9_p"
  }
];

// Helper functions ported from Python to JavaScript
const safeText = (v, fallback = "—") => {
  if (v === null || v === undefined) return fallback;
  if (typeof v === 'number' && isNaN(v)) return fallback;
  
  let s = String(v).trim();
  if (s.toLowerCase() === "nan" || s.toLowerCase() === "none" || 
      s.toLowerCase() === "null" || s === "") {
    return fallback;
  }
  return s;
};

const normCol = (s) => {
  if (s === null || s === undefined) return "";
  s = String(s).trim().toLowerCase().replace(/ё/g, "е");
  return s.replace(/\s+/g, " ");
};

const statusAccent = (statusText) => {
  const s = normCol(statusText);
  if (s.includes("останов") || s.includes("приостанов")) return "red";
  if (s.includes("проектир")) return "yellow";
  if (s.includes("строитель")) return "green";
  return "blue";
};

const worksColor = (workFlag) => {
  const s = normCol(workFlag);
  const negativeTerms = ["—", "", "нет", "не ведутся", "не выполня", "отсутств"];
  if (negativeTerms.some(term => s.includes(term)) || s === "не ведутся." || s === "не ведутся..") {
    return "red";
  }
  const positiveTerms = ["да", "ведут", "выполня", "идут"];
  if (positiveTerms.some(term => s.includes(term))) {
    return "green";
  }
  return "gray";
};

const tryParseDate = (v) => {
  if (v === null || v === undefined) return null;
  
  // Handle Date objects
  if (v instanceof Date && !isNaN(v)) {
    return v;
  }
  
  // Handle strings
  let s = String(v).trim();
  if (!s || ["nan", "none", "null", "—"].includes(s.toLowerCase())) {
    return null;
  }
  
  // Handle Excel serial dates (numbers)
  if (/^\d+(\.\d+)?$/.test(s)) {
    try {
      const num = parseFloat(s);
      // Excel serial date: days since 1899-12-30
      const date = new Date("1899-12-30");
      date.setDate(date.getDate() + num);
      if (!isNaN(date)) return date;
    } catch (e) {
      return null;
    }
  }
  
  // Try common date formats
  const formats = ["%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d", "%Y/%m/%d"];
  for (const fmt of formats) {
    try {
      let dateStr = s;
      if (fmt === "%d.%m.%Y" || fmt === "%d.%m.%y") {
        const parts = s.split('.');
        if (parts.length === 3) {
          const day = parts[0].padStart(2, '0');
          const month = parts[1].padStart(2, '0');
          const year = parts[2].length === 2 ? `20${parts[2]}` : parts[2];
          dateStr = `${year}-${month}-${day}`;
        }
      }
      const date = new Date(dateStr);
      if (!isNaN(date)) return date;
    } catch (e) {
      continue;
    }
  }
  
  // Fallback to Date.parse
  const date = new Date(s);
  return isNaN(date) ? null : date;
};

const updateColor = (updatedAtValue) => {
  const d = tryParseDate(updatedAtValue);
  if (!d) return ["gray", "—"];
  
  const today = new Date();
  const diffTime = Math.abs(today - d);
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  
  if (diffDays <= 7) return ["green", d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' })];
  if (diffDays <= 14) return ["yellow", d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' })];
  return ["red", d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' })];
};

const moneyFmt = (v) => {
  const s = safeText(v, "—");
  if (s === "—") return s;
  
  try {
    let x = s.replace(/\s+/g, '').replace(',', '.');
    x = parseFloat(x);
    if (isNaN(x)) throw new Error("Invalid number");
    
    // Format with spaces as thousand separators
    const parts = x.toFixed(2).split(".");
    parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, " ");
    return `${parts.join(",").replace(".00", "")} ₽`;
  } catch (e) {
    return s.includes("₽") || s.toLowerCase().includes("руб") ? s : `${s} ₽`;
  }
};

const numFmt = (v) => {
  const s = safeText(v, "—");
  if (s === "—") return s;
  
  try {
    let x = s.replace(/\s+/g, '').replace(',', '.');
    x = parseFloat(x);
    if (isNaN(x)) throw new Error("Invalid number");
    
    if (Number.isInteger(x)) {
      return x.toLocaleString('ru-RU').replace(/,/g, " ");
    }
    return x.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  } catch (e) {
    return s;
  }
};

const dateFmt = (v) => {
  const d = tryParseDate(v);
  if (!d) return "—";
  return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' });
};

const moveProchieToBottom = (items) => {
  if (!items || items.length === 0) return items;
  
  const isProchie = (x) => {
    const nx = normCol(x);
    return nx === "прочие" || nx === "прочее";
  };
  
  const prochie = items.filter(x => isProchie(x));
  const rest = items.filter(x => !isProchie(x));
  return [...rest, ...prochie];
};

// Status color mapping for borders
const statusColors = {
  green: '#22c55e',
  yellow: '#f59e0b',
  red: '#ef4444',
  blue: '#3b82f6'
};

export default function App() {
  // State for filters
  const [sectorSel, setSectorSel] = useState("Все");
  const [districtSel, setDistrictSel] = useState("Все");
  const [statusSel, setStatusSel] = useState("Все");
  const [searchQuery, setSearchQuery] = useState("");
  const [filteredData, setFilteredData] = useState(mockData);
  
  // Get unique values for filters
  const sectors = ["Все", ...moveProchieToBottom(
    [...new Set(mockData.map(item => safeText(item.sector)))].filter(s => s !== "—")
  )];
  
  const districts = ["Все", ...Array.from(
    new Set(mockData.map(item => safeText(item.district)))
  ).filter(s => s !== "—").sort()];
  
  const statuses = ["Все", ...Array.from(
    new Set(mockData.map(item => safeText(item.status)))
  ).filter(s => s !== "—").sort()];
  
  // Filter data based on selections
  useEffect(() => {
    let result = [...mockData];
    
    if (sectorSel !== "Все") {
      result = result.filter(item => safeText(item.sector) === sectorSel);
    }
    
    if (districtSel !== "Все") {
      result = result.filter(item => safeText(item.district) === districtSel);
    }
    
    if (statusSel !== "Все") {
      result = result.filter(item => safeText(item.status) === statusSel);
    }
    
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      result = result.filter(item => {
        const searchStr = [
          safeText(item.name),
          safeText(item.address),
          safeText(item.responsible)
        ].join(" ").toLowerCase();
        return searchStr.includes(q);
      });
    }
    
    setFilteredData(result);
  }, [sectorSel, districtSel, statusSel, searchQuery]);
  
  // Placeholder for crest image (base64 encoded)
  const crestB64 = null; // In a real app, this would be a base64 string of the image
  
  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--text)] font-sans">
      <style jsx global>{`
        :root {
          --bg: #f7f8fb;
          --card: #ffffff;
          --card2: rgba(15,23,42,.03);
          --text: #0f172a;
          --muted: rgba(15,23,42,.72);
          --border: rgba(15,23,42,.10);
          --shadow: rgba(0,0,0,.06);
          --chip-bg: rgba(15,23,42,.05);
          --chip-bd: rgba(15,23,42,.10);
          --btn-bg: rgba(255,255,255,.95);
          --btn-bd: rgba(15,23,42,.12);
          --hr: rgba(15,23,42,.12);
        }

        @media (prefers-color-scheme: dark) {
          :root {
            --bg: #0b1220;
            --card: #111a2b;
            --card2: rgba(255,255,255,.04);
            --text: rgba(255,255,255,.92);
            --muted: rgba(255,255,255,.70);
            --border: rgba(255,255,255,.12);
            --shadow: rgba(0,0,0,.35);
            --chip-bg: rgba(255,255,255,.06);
            --chip-bd: rgba(255,255,255,.12);
            --btn-bg: rgba(17,26,43,.90);
            --btn-bd: rgba(255,255,255,.14);
            --hr: rgba(255,255,255,.14);
          }
        }

        .hero {
          background: radial-gradient(1200px 380px at 22% 30%, rgba(60,130,255,.22), rgba(0,0,0,0) 55%),
                      linear-gradient(135deg, #0b2a57, #1b4c8f);
          box-shadow: 0 18px 34px rgba(0,0,0,.18);
          position: relative;
          overflow: hidden;
        }
        
        .hero::after {
          content: "";
          position: absolute;
          inset: -40px -120px auto auto;
          width: 520px;
          height: 320px;
          background: rgba(255,255,255,.08);
          transform: rotate(14deg);
          border-radius: 32px;
        }
        
        .tag-green {
          background: rgba(34,197,94,.12);
          border-color: rgba(34,197,94,.22);
        }
        
        .tag-yellow {
          background: rgba(245,158,11,.14);
          border-color: rgba(245,158,11,.25);
        }
        
        .tag-red {
          background: rgba(239,68,68,.12);
          border-color: rgba(239,68,68,.22);
        }
        
        .issue-box {
          border: 1px solid rgba(239,68,68,.25);
          background: rgba(239,68,68,.08);
        }
        
        .card {
          background: var(--card);
          border: 1px solid var(--border);
          border-radius: 16px;
          padding: 16px;
          box-shadow: 0 10px 22px var(--shadow);
          margin-bottom: 14px;
          position: relative;
          transition: all 0.2s ease;
        }
        
        .card:hover {
          transform: translateY(-2px);
          box-shadow: 0 12px 28px var(--shadow);
        }
        
        .a-btn {
          flex: 1 1 0;
          display: flex;
          justify-content: center;
          align-items: center;
          gap: 8px;
          padding: 10px 12px;
          border-radius: 12px;
          border: 1px solid var(--btn-bd);
          background: var(--btn-bg);
          text-decoration: none !important;
          color: var(--text) !important;
          font-weight: 800;
          font-size: 14px;
          transition: .12s ease-in-out;
        }
        
        .a-btn:hover {
          transform: translateY(-1px);
          box-shadow: 0 10px 18px rgba(0,0,0,.10);
        }
        
        .a-btn.disabled {
          opacity: .45;
          pointer-events: none;
        }
      `}</style>
      
      {/* Hero Section */}
      <div className="hero-wrap max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="hero rounded-2xl p-5">
          <div className="hero-row flex flex-col md:flex-row items-start md:items-center gap-4">
            <div className="hero-crest flex-shrink-0 w-16 h-16 rounded-xl bg-white/10 border border-white/16 flex items-center justify-center">
              {crestB64 ? (
                <img 
                  src={`image/png;base64,${crestB64}`} 
                  alt="Герб" 
                  className="w-12 h-12 object-contain drop-shadow-md"
                />
              ) : (
                <span className="text-white/80 font-bold text-xs">герб</span>
              )}
            </div>
            <div className="hero-titles flex-1 min-w-0">
              <div className="hero-ministry text-white font-extrabold text-xl md:text-2xl leading-tight">
                Министерство восстановления, развития приграничья и строительства Курской области
              </div>
              <div className="hero-app text-white font-bold text-lg mt-1">
                Реестр объектов
              </div>
              <div className="hero-sub text-white/78 text-sm mt-1">
                Единый список объектов 2025–2028 с быстрыми фильтрами и переходом в карточку/папку.
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Filters Section */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div>
            <label className="block text-sm font-medium mb-1">🏷️ Отрасль</label>
            <select
              value={sectorSel}
              onChange={(e) => setSectorSel(e.target.value)}
              className="w-full px-3 py-2 border border-[var(--border)] rounded-lg bg-[var(--card)] text-[var(--text)] focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {sectors.map(sector => (
                <option key={sector} value={sector}>{sector}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">📍 Район</label>
            <select
              value={districtSel}
              onChange={(e) => setDistrictSel(e.target.value)}
              className="w-full px-3 py-2 border border-[var(--border)] rounded-lg bg-[var(--card)] text-[var(--text)] focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {districts.map(district => (
                <option key={district} value={district}>{district}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">📌 Статус</label>
            <select
              value={statusSel}
              onChange={(e) => setStatusSel(e.target.value)}
              className="w-full px-3 py-2 border border-[var(--border)] rounded-lg bg-[var(--card)] text-[var(--text)] focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {statuses.map(status => (
                <option key={status} value={status}>{status}</option>
              ))}
            </select>
          </div>
        </div>
        
        <div className="mb-4">
          <label className="block text-sm font-medium mb-1">🔎 Поиск (наименование / адрес / ответственный)</label>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Введите текст для поиска..."
            className="w-full px-4 py-2 border border-[var(--border)] rounded-lg bg-[var(--card)] text-[var(--text)] focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        
        <div className="text-sm text-[var(--muted)] mb-6">
          Показано объектов: {filteredData.length} из {mockData.length}
        </div>
        
        <hr className="border-t border-[var(--hr)] my-8" />
        
        {/* Cards Section */}
        <div className="space-y-6">
          {filteredData.map(item => {
            const title = safeText(item.name, "Объект");
            const sector = safeText(item.sector, "—");
            const district = safeText(item.district, "—");
            const address = safeText(item.address, "—");
            const responsible = safeText(item.responsible, "—");
            
            const status = safeText(item.status, "—");
            const workFlag = safeText(item.work_flag, "—");
            const issues = safeText(item.issues, "—");
            
            const cardUrl = safeText(item.card_url, "");
            
            // Get colors
            const accent = statusAccent(status);
            const wCol = worksColor(workFlag);
            const [uCol, uTxt] = updateColor(item.updated_at);
            
            // Determine tag classes
            const sTagClass = accent === "green" ? "tag-green" : 
                             accent === "yellow" ? "tag-yellow" : 
                             accent === "red" ? "tag-red" : "tag-gray";
            
            const wTagClass = wCol === "green" ? "tag-green" : 
                             wCol === "red" ? "tag-red" : "tag-gray";
            
            const uTagClass = uCol === "green" ? "tag-green" : 
                             uCol === "yellow" ? "tag-yellow" : 
                             uCol === "red" ? "tag-red" : "tag-gray";
            
            // Get border color based on status
            const borderColor = statusColors[accent] || 'var(--border)';
            
            return (
              <div 
                key={item.id} 
                className="card"
                style={{ 
                  borderColor: borderColor,
                  borderLeftWidth: '4px',
                  boxShadow: '0 10px 22px var(--shadow)'
                }}
              >
                <h3 className="card-title text-2xl font-extrabold mb-3">{title}</h3>
                
                <div className="card-subchips flex flex-wrap gap-2 mb-3">
                  <span className="chip inline-flex items-center px-3 py-1.5 border border-[var(--chip-bd)] bg-[var(--chip-bg)] rounded-full text-sm">
                    🏷️ {sector}
                  </span>
                  <span className="chip inline-flex items-center px-3 py-1.5 border border-[var(--chip-bd)] bg-[var(--chip-bg)] rounded-full text-sm">
                    📍 {district}
                  </span>
                </div>
                
                <div className="card-grid grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-3 mb-4">
                  <div className="card-item">
                    🗺️ <span className="font-bold">Адрес:</span> {address}
                  </div>
                  <div className="card-item">
                    👤 <span className="font-bold">Ответственный:</span> {responsible}
                  </div>
                </div>
                
                <div className="card-tags flex flex-wrap gap-2 mb-5">
                  <span className={`tag ${sTagClass} inline-flex items-center px-3 py-1.5 border rounded-full text-sm font-bold`}>
                    📌 Статус: {status}
                  </span>
                  <span className={`tag ${wTagClass} inline-flex items-center px-3 py-1.5 border rounded-full text-sm font-bold`}>
                    🛠️ Работы: {workFlag}
                  </span>
                  <span className={`tag ${uTagClass} inline-flex items-center px-3 py-1.5 border rounded-full text-sm font-bold`}>
                    ⏱️ Обновлено: {uTxt}
                  </span>
                </div>
                
                <div className="card-actions flex flex-col sm:flex-row gap-3 mb-5">
                  {cardUrl && cardUrl !== "—" ? (
                    <a 
                      href={cardUrl} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="a-btn flex-1 flex items-center justify-center gap-2 px-4 py-2.5 border border-[var(--btn-bd)] bg-[var(--btn-bg)] rounded-xl font-bold text-sm hover:translate-y-[-1px] hover:shadow-md transition-all"
                    >
                      📄 Открыть карточку
                    </a>
                  ) : (
                    <span className="a-btn flex-1 flex items-center justify-center gap-2 px-4 py-2.5 border border-[var(--btn-bd)] bg-[var(--btn-bg)] rounded-xl font-bold text-sm opacity-45 cursor-not-allowed">
                      📄 Открыть карточку
                    </span>
                  )}
                </div>
                
                {/* Expandable Passport Section */}
                <details className="mt-6 border-t border-[var(--border)] pt-5">
                  <summary className="cursor-pointer font-bold text-lg flex items-center gap-2">
                    📋 Паспорт объекта и контрольные показатели — нажмите, чтобы раскрыть
                  </summary>
                  
                  <div className="mt-4 space-y-5">
                    {/* Issues Section */}
                    <div className="section rounded-xl border border-[var(--border)] bg-[var(--card2)] p-4">
                      <div className="section-title font-extrabold text-sm mb-2">⚠️ Проблемные вопросы</div>
                      {issues !== "—" ? (
                        <div className="issue-box rounded-lg p-3 text-sm">
                          {issues}
                        </div>
                      ) : (
                        <div className="row text-sm text-[var(--muted)]">—</div>
                      )}
                    </div>
                    
                    {/* Programs Section */}
                    <div className="section rounded-xl border border-[var(--border)] bg-[var(--card2)] p-4">
                      <div className="section-title font-extrabold text-sm mb-3">🏛️ Программы</div>
                      <div className="space-y-2">
                        <div className="row text-sm">
                          <span className="font-bold">ГП/СП:</span> {safeText(item.state_program, "—")}
                        </div>
                        <div className="row text-sm">
                          <span className="font-bold">ФП:</span> {safeText(item.federal_project, "—")}
                        </div>
                        <div className="row text-sm">
                          <span className="font-bold">РП:</span> {safeText(item.regional_program, "—")}
                        </div>
                      </div>
                    </div>
                    
                    {/* Agreement Section */}
                    <div className="section rounded-xl border border-[var(--border)] bg-[var(--card2)] p-4">
                      <div className="section-title font-extrabold text-sm mb-3">🧾 Соглашение</div>
                      <div className="space-y-2">
                        <div className="row text-sm">
                          <span className="font-bold">№:</span> {safeText(item.agreement, "—")}
                        </div>
                        <div className="row text-sm">
                          <span className="font-bold">Дата:</span> {dateFmt(item.agreement_date)}
                        </div>
                        <div className="row text-sm">
                          <span className="font-bold">Сумма:</span> {moneyFmt(item.agreement_amount)}
                        </div>
                      </div>
                    </div>
                    
                    {/* Parameters Section */}
                    <div className="section rounded-xl border border-[var(--border)] bg-[var(--card2)] p-4">
                      <div className="section-title font-extrabold text-sm mb-3">📦 Параметры</div>
                      <div className="space-y-2">
                        <div className="row text-sm">
                          <span className="font-bold">Мощность:</span> {safeText(item.capacity_seats, "—")}
                        </div>
                        <div className="row text-sm">
                          <span className="font-bold">Площадь:</span> {safeText(item.area_m2, "—")}
                        </div>
                        <div className="row text-sm">
                          <span className="font-bold">Целевой срок:</span> {dateFmt(item.target_deadline)}
                        </div>
                      </div>
                    </div>
                    
                    {/* PSD/Expertise Section */}
                    <div className="section rounded-xl border border-[var(--border)] bg-[var(--card2)] p-4">
                      <div className="section-title font-extrabold text-sm mb-3">🗂️ ПСД / Экспертиза</div>
                      <div className="space-y-2">
                        <div className="row text-sm">
                          <span className="font-bold">ПСД:</span> {safeText(item.design, "—")}
                        </div>
                        <div className="row text-sm">
                          <span className="font-bold">Стоимость ПСД:</span> {moneyFmt(item.psd_cost)}
                        </div>
                        <div className="row text-sm">
                          <span className="font-bold">Проектировщик:</span> {safeText(item.designer, "—")}
                        </div>
                        <div className="row text-sm">
                          <span className="font-bold">Экспертиза:</span> {safeText(item.expertise, "—")}
                        </div>
                        <div className="row text-sm">
                          <span className="font-bold">Дата экспертизы:</span> {dateFmt(item.expertise_date)}
                        </div>
                        <div className="row text-sm">
                          <span className="font-bold">Заключение:</span> {safeText(item.expertise_conclusion, "—")}
                        </div>
                      </div>
                    </div>
                    
                    {/* RNS Section */}
                    <div className="section rounded-xl border border-[var(--border)] bg-[var(--card2)] p-4">
                      <div className="section-title font-extrabold text-sm mb-3">🏗️ РНС</div>
                      <div className="space-y-2">
                        <div className="row text-sm">
                          <span className="font-bold">№ РНС:</span> {safeText(item.rns, "—")}
                        </div>
                        <div className="row text-sm">
                          <span className="font-bold">Дата:</span> {dateFmt(item.rns_date)}
                        </div>
                        <div className="row text-sm">
                          <span className="font-bold">Срок действия:</span> {dateFmt(item.rns_expiry)}
                        </div>
                      </div>
                    </div>
                    
                    {/* Contract Section */}
                    <div className="section rounded-xl border border-[var(--border)] bg-[var(--card2)] p-4">
                      <div className="section-title font-extrabold text-sm mb-3">🧩 Контракт</div>
                      <div className="space-y-2">
                        <div className="row text-sm">
                          <span className="font-bold">№:</span> {safeText(item.contract, "—")}
                        </div>
                        <div className="row text-sm">
                          <span className="font-bold">Дата:</span> {dateFmt(item.contract_date)}
                        </div>
                        <div className="row text-sm">
                          <span className="font-bold">Подрядчик:</span> {safeText(item.contractor, "—")}
                        </div>
                        <div className="row text-sm">
                          <span className="font-bold">Цена:</span> {moneyFmt(item.contract_price)}
                        </div>
                      </div>
                    </div>
                    
                    {/* Timeline/Finance Section */}
                    <div className="section rounded-xl border border-[var(--border)] bg-[var(--card2)] p-4">
                      <div className="section-title font-extrabold text-sm mb-3">⏳ Сроки / финансы</div>
                      <div className="space-y-2">
                        <div className="row text-sm">
                          <span className="font-bold">Окончание (план):</span> {dateFmt(item.end_date_plan)}
                        </div>
                        <div className="row text-sm">
                          <span className="font-bold">Окончание (факт):</span> {dateFmt(item.end_date_fact)}
                        </div>
                        <div className="row text-sm">
                          <span className="font-bold">Готовность:</span> {safeText(item.readiness, "—")}
                        </div>
                        <div className="row text-sm">
                          <span className="font-bold">Оплачено:</span> {moneyFmt(item.paid)}
                        </div>
                      </div>
                    </div>
                  </div>
                </details>
              </div>
            );
          })}
          
          {filteredData.length === 0 && (
            <div className="text-center py-12 text-[var(--muted)]">
              Нет объектов, соответствующих выбранным фильтрам
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
