const TZ = "Europe/Madrid";
let DATA = null;
let TEACHERS_DATA = null;
let activeFilter = 'all';
let selectedTeacher = null;

/* ---------- Diccionario de siglas y abreviaturas ---------- */
const SUBJECT_ALIASES = {
  "aedii": "algoritmos e estructuras de datos ii",
  "aedi": "algoritmos e estructuras de datos i",
  "bdii": "bases de datos ii",
  "bdi": "bases de datos i",
  "is1": "enxeñaría del software i",
  "is2": "enxeñaría del software ii",
  "so": "sistemas operativos",
  "cd": "ciencia de datos",
  "ia": "intelixencia artificial",
  "redes": "redes de ordenadores"
};

/* Lista negra para filtrar textos del menú web escrapeados por error */
const BLACKLISTED_TERMS = [
  "campus auga", "biblioteca", "deportes", "cultura", "correo uvigo", "moovi", "duvi", 
  "secretaría", "a esei", "benvida do director", "formularios", "prácticas en empresa", 
  "traballos fin de grao", "traballos fin de máster", "normativas", "normativa académica", 
  "normativa de xestión económica", "regulamento de réxime interno", "reclamacións e suxestións", 
  "persoal técnico", "recursos materiais", "aulas, laboratorios", "laboratorio de libre acceso", 
  "seminarios para estudo", "infraestrutura", "rede wireless", "equipo directivo", "órganos de goberno", 
  "xunta de centro", "comisión", "delegación de alumnos", "prevención de riscos", "igualdade", 
  "coddii", "colexios profesionais", "cpeig", "cpetig", "localización e contacto", "guía de benvida", 
  "docencia", "calendario académico", "grupos reducidos", "horarios", "exames", "profesorado", 
  "departamentos", "pat-aneae", "piune", "avaliación por compensación", "estudos", "grao en", 
  "competencias e obxectivos", "guías docentes", "curso ponte", "informes de coordinación", 
  "memoria do", "acceso ao", "recoñecemento de créditos", "suplemento europeo", "pceo", "páxina web", 
  "mástes universitario", "especialidades", "sitio promocional", "gl", "es"
];

/* Helper para limpiar el array de asignaturas de cada profesor */
function cleanSubjects(subjects) {
  if (!Array.isArray(subjects)) return [];
  return subjects.filter(s => {
    if (!s || typeof s !== "string" || s.length > 70) return false;
    const lower = s.toLowerCase().trim();
    return !BLACKLISTED_TERMS.some(black => lower.includes(black));
  });
}

/* Helper para normalizar búsquedas e ignorar acentos */
function normalizeStr(str) {
  return (str || "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").trim();
}

/* Helper para comprobar si una consulta coincide con un profesor de forma flexible */
function matchesTeacher(teacher, rawQuery) {
  const query = normalizeStr(rawQuery);
  if (!query) return true;

  const nameMatch = normalizeStr(teacher.name).includes(query);
  const officeMatch = normalizeStr(teacher.office).includes(query);

  // Expandir alias si la consulta coincide de forma parcial con las claves
  let expandedAliases = [];
  for (const [aliasKey, aliasVal] of Object.entries(SUBJECT_ALIASES)) {
    if (aliasKey.includes(query) || query.includes(aliasKey)) {
      expandedAliases.push(normalizeStr(aliasVal));
    }
  }

  const validSubjects = cleanSubjects(teacher.subjects);
  const subjectMatch = validSubjects.some(s => {
    const subNorm = normalizeStr(s);
    // 1. Coincidencia por texto parcial (ej: "algoritmos", "datos")
    if (subNorm.includes(query)) return true;
    // 2. Coincidencia por alias (ej: "ae" o "aed")
    return expandedAliases.some(alias => subNorm.includes(alias));
  });

  return nameMatch || officeMatch || subjectMatch;
}

/* ---------- floor / room helper filters ---------- */
function getFloor(roomName) {
  if (!roomName) return null;
  const match = roomName.match(/\b([0-3])\.\d+\b/);
  return match ? parseInt(match[1], 10) : null;
}

const PRESET_FILTERS = {
  all: () => true,
  floor1: (room) => getFloor(room) === 1,
  floor2: (room) => getFloor(room) === 2,
  floor3: (room) => getFloor(room) === 3,
  soxAndMagna: (room) => {
    if (!room) return false;
    const r = room.toLowerCase();
    return r.includes("so") || r === "aula magna";
  }
};

/* ---------- time helpers (all in Europe/Madrid) ---------- */
function madridParts(date = new Date()) {
  const p = new Intl.DateTimeFormat("en-GB", {
    timeZone: TZ,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false
  }).formatToParts(date).reduce((a, x) => (a[x.type] = x.value, a), {});
  
  return {
    date: `${p.year}-${p.month}-${p.day}`,
    time: `${p.hour}:${p.minute}`,
    timeFull: `${p.hour}:${p.minute}:${p.second}`
  };
}

function weekdayName(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "short" });
}

const toMin = t => {
  const [a, b] = t.split(":").map(Number);
  return a * 60 + b;
};

/* ---------- data helpers ---------- */
const eventsOn = iso => DATA.events.filter(e => e.date === iso);

function roomKey(r) {
  return (r || "").split(/(\d+)/).map(s => isNaN(s) ? s : +s);
}

function statusAt(evts, time) {
  const t = toMin(time);
  return evts.find(e => toMin(e.start) <= t && t < toMin(e.end));
}

/* ---------- rendering rooms ---------- */
function render() {
  if (!DATA) return;
  const dateEl = document.getElementById("date");
  const timeEl = document.getElementById("time");
  const iso = dateEl.value;
  const time = timeEl.value;
  const nowIso = madridParts().date;
  const viewingNow = (iso === nowIso);
  
  document.getElementById("boardTitle").textContent =
    viewingNow ? "Right now" : `Status on ${weekdayName(iso)} at ${time}`;

  const evts = eventsOn(iso);
  
  let rooms = [...new Set(DATA.events.map(e => e.room).filter(Boolean))].sort((a, b) => {
    const ka = roomKey(a), kb = roomKey(b);
    for (let i = 0; i < Math.max(ka.length, kb.length); i++) {
      if (ka[i] === undefined) return -1;
      if (kb[i] === undefined) return 1;
      if (ka[i] !== kb[i]) return ka[i] < kb[i] ? -1 : 1;
    }
    return 0;
  });

  const filterFn = PRESET_FILTERS[activeFilter] || PRESET_FILTERS.all;
  rooms = rooms.filter(filterFn);

  const board = document.getElementById("board");
  board.innerHTML = "";
  const later = evts.filter(e => toMin(e.start) >= toMin(time))
                    .sort((a, b) => toMin(a.start) - toMin(b.start));

  if (!rooms.length) {
    board.innerHTML = `<div style="grid-column:1/-1; color:var(--muted)">No rooms matching this floor filter.</div>`;
  }

  for (const room of rooms) {
    const roomEvts = evts.filter(e => e.room === room);
    const cur = statusAt(roomEvts, time);
    const nxt = later.find(e => e.room === room);
    const card = document.createElement("div");
    card.className = "card " + (cur ? "busy" : "free");
    card.innerHTML =
      `<div class="room">${room}</div>` +
      `<span class="pill">${cur ? "BUSY" : "FREE"}</span>` +
      (cur ? `<div class="cls">${cur.subject} <span class="time">until ${cur.end}</span></div>`
           : `<div class="cls" style="color:var(--muted)">no class at this time</div>`) +
      (nxt ? `<div class="next">Next: ${nxt.start} · ${nxt.subject}</div>` : "");
    board.appendChild(card);
  }

  const body = document.getElementById("dayBody");
  body.innerHTML = "";
  if (!rooms.length) {
    body.innerHTML = `<tr><td colspan="2" style="color:var(--muted)">No classes or rooms found for this view.</td></tr>`;
  }
  for (const room of rooms) {
    const roomDayEvts = evts.filter(e => e.room === room);
    const chips = roomDayEvts.length 
      ? roomDayEvts.map(e => `<span class="chip"><b>${e.start}–${e.end}</b> ${e.subject}</span>`).join("")
      : `<span style="color:var(--muted); font-size:.8rem">No classes scheduled today</span>`;
      
    body.insertAdjacentHTML("beforeend", `<tr><td><b>${room}</b></td><td>${chips}</td></tr>`);
  }
}

/* ---------- rendering teachers ---------- */
function renderTeachers() {
  if (!TEACHERS_DATA) return;

  const board = document.getElementById("teachersBoard");
  if (!board) return;

  board.innerHTML = "";

  // 1. DETAIL VIEW
  if (selectedTeacher) {
    const t = selectedTeacher;
    const cleanSubs = cleanSubjects(t.subjects);
    const subjectsText = cleanSubs.length 
      ? cleanSubs.map(s => `<span class="chip"><b>${s}</b></span>`).join(" ")
      : "<span style='color:var(--muted);'>Docencia no especificada</span>";

    let extraInfoHtml = "";
    if (t.info || t.events) {
      extraInfoHtml = `
        <div class="teacher-info-section" style="margin-top:16px;">
          <h4 style="margin:0 0 8px 0; font-size:1rem;">Información / Actividad</h4>
          <div style="font-size:0.9rem; line-height:1.5; color:var(--text); white-space: pre-wrap;">
            ${t.info || t.events}
          </div>
        </div>
      `;
    }

    const detailContainer = document.createElement("div");
    detailContainer.style.gridColumn = "1 / -1";
    detailContainer.innerHTML = `
      <button id="backToSearchBtn" style="margin-bottom: 16px; padding: 8px 16px; cursor: pointer; background: var(--panel2); color: var(--accent); border: 1px solid var(--accent); border-radius: 6px;">
        &larr; Volver al buscador
      </button>
      <div class="card free" style="cursor: default; padding:20px;">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:12px;">
          <div>
            <div class="room" style="font-size:1.5rem;">${t.name}</div>
            <div class="cls" style="font-size:1rem; margin-top:6px; display:flex; flex-direction:column; gap:4px;">
              ${t.email ? `<a href="mailto:${t.email}" class="card-link">${t.email}</a>` : '<span style="color:var(--muted);">Sin correo</span>'}
              ${t.phone ? `<span style="color:var(--text); font-size:0.9rem;">Teléfono: <b>${t.phone}</b></span>` : ''}
            </div>
          </div>
          <span class="pill" style="background:var(--panel2); color:var(--accent); font-size:0.95rem; padding: 6px 12px;">
            DESPACHO: ${t.office || 'No especificado'}
          </span>
        </div>

        <div style="margin-top:20px;">
          <b style="display:block; margin-bottom:8px;">Asignaturas:</b>
          <div style="display:flex; flex-wrap:wrap; gap:6px;">${subjectsText}</div>
        </div>

        <!-- ACTION BUTTONS & PORTAL LINKS -->
        <div style="margin-top:20px; display:flex; gap:10px; flex-wrap:wrap;">
          ${t.esei_url ? `
            <a href="${t.esei_url}" target="_blank" rel="noopener" class="card-link" style="padding: 6px 12px; background: var(--panel2); border-radius: 6px; font-size: 0.9rem;">
              Ficha ESEI &nearr;
            </a>
          ` : ''}

          ${t.uvigo_url ? `
            <a href="${t.uvigo_url}" target="_blank" rel="noopener" class="card-link" style="padding: 6px 12px; background: var(--panel2); border-radius: 6px; font-size: 0.9rem;">
              Perfil UVigo / Tutorías &nearr;
            </a>
          ` : ''}

          ${t.virtual_office ? `
            <a href="${t.virtual_office}" target="_blank" rel="noopener" class="card-link" style="padding: 6px 12px; background: var(--panel2); border-radius: 6px; font-size: 0.9rem;">
              Despacho Virtual &nearr;
            </a>
          ` : ''}
        </div>

        ${extraInfoHtml}
      </div>
    `;

    board.appendChild(detailContainer);

    document.getElementById("backToSearchBtn").addEventListener("click", () => {
      selectedTeacher = null;
      renderTeachers();
    });
    return;
  }

  // 2. SEARCH GRID
  const rawQuery = (document.getElementById("teacherSearch")?.value || "").trim();
  const filtered = TEACHERS_DATA.teachers.filter(t => matchesTeacher(t, rawQuery));

  if (!filtered.length) {
    board.innerHTML = `<div style="grid-column:1/-1; color:var(--muted)">No se han encontrado profesores que coincidan con la búsqueda.</div>`;
    return;
  }

  for (const t of filtered) {
    const card = document.createElement("div");
    card.className = "card free";
    card.style.cursor = "pointer";

    card.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:8px;">
        <div>
          <div class="room" style="font-size:1.2rem;">${t.name}</div>
          <div class="cls"><a href="mailto:${t.email}" class="card-link" onclick="event.stopPropagation()">${t.email || 'Sin correo'}</a></div>
        </div>
        <span class="pill" style="background:var(--panel2); color:var(--accent); font-size:0.85rem;">
          DESPACHO: ${t.office || 'No especificado'}
        </span>
      </div>
    `;

    card.addEventListener("click", () => {
      selectedTeacher = t;
      renderTeachers();
    });

    board.appendChild(card);
  }
}

function tick() {
  document.getElementById("clock").textContent =
    weekdayName(madridParts().date) + " · " + madridParts().timeFull + " (Madrid)";
}

async function boot() {
  tick();
  setInterval(tick, 1000);

  try {
    const r = await fetch(`data.json?v=${Date.now()}`, { cache: "no-store" });
    if (!r.ok) throw new Error("HTTP " + r.status);
    DATA = await r.json();
    document.getElementById("freshness").textContent =
      "data updated: " + new Date(DATA.generated_at).toLocaleString();
  } catch (err) {
    const e = document.getElementById("error");
    e.style.display = "block";
    e.textContent = "⚠ Could not load data.json — if you are opening this file locally, run a tiny server first: python -m http.server (or push to GitHub Pages, where it works out of the box).";
    return;
  }

  try {
    const r = await fetch(`teachers.json?v=${Date.now()}`, { cache: "no-store" });
    if (r.ok) {
      TEACHERS_DATA = await r.json();
      const freshnessEl = document.getElementById("teachersFreshness");
      if (freshnessEl) {
        freshnessEl.textContent = "updated: " + new Date(TEACHERS_DATA.generated_at).toLocaleDateString();
      }
    }
  } catch (err) {
    console.warn("teachers.json could not be loaded.");
  }

  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      
      e.target.classList.add('active');
      const tabId = e.target.getAttribute('data-tab') + 'Tab';
      const targetTab = document.getElementById(tabId);
      if (targetTab) targetTab.classList.add('active');

      if (e.target.getAttribute('data-tab') === 'teachers') {
        renderTeachers();
      }
    });
  });

  const today = madridParts().date;
  const dates = [...new Set(DATA.events.map(e => e.date))].sort();
  const def = dates.includes(today) ? today : (dates.find(d => d >= today) || dates[0] || today);
  const dateEl = document.getElementById("date");
  const timeEl = document.getElementById("time");
  dateEl.value = def;
  timeEl.value = madridParts().time;

  const syncNowBtn = () =>
    document.getElementById("nowBtn").classList.toggle("active", dateEl.value === madridParts().date);

  [dateEl, timeEl].forEach(el => el.addEventListener("input", () => {
    syncNowBtn();
    render();
  }));

  document.getElementById("nowBtn").addEventListener("click", () => {
    dateEl.value = madridParts().date;
    timeEl.value = madridParts().time;
    syncNowBtn();
    render();
  });

  document.querySelectorAll('.filter-btn').forEach(button => {
    button.addEventListener('click', (e) => {
      document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
      e.target.classList.add('active');
      activeFilter = e.target.getAttribute('data-filter');
      render();
    });
  });

  const searchInput = document.getElementById("teacherSearch");
  if (searchInput) {
    searchInput.addEventListener("input", () => {
      selectedTeacher = null;
      renderTeachers();
    });
  }

  render();
  renderTeachers();

  setInterval(() => {
    if (document.getElementById("nowBtn").classList.contains("active")) {
      timeEl.value = madridParts().time;
      dateEl.value = madridParts().date;
      render();
    }
  }, 30000);
  setupTeacherAutocomplete();
}

function setupTeacherAutocomplete() {
  const input = document.getElementById("teacherSearch");
  const listContainer = document.getElementById("autocompleteList");
  if (!input || !listContainer) return;

  let currentFocus = -1;

  function closeAllLists(elmnt) {
    if (elmnt !== input && elmnt !== listContainer) {
      listContainer.innerHTML = "";
    }
  }

  function addActive(items) {
    if (!items || !items.length) return false;
    removeActive(items);
    if (currentFocus >= items.length) currentFocus = 0;
    if (currentFocus < 0) currentFocus = items.length - 1;
    items[currentFocus].classList.add("autocomplete-active");
    items[currentFocus].scrollIntoView({ block: "nearest" });
  }

  function removeActive(items) {
    for (let i = 0; i < items.length; i++) {
      items[i].classList.remove("autocomplete-active");
    }
  }

  input.addEventListener("input", function() {
    const rawVal = this.value.trim();
    listContainer.innerHTML = "";
    currentFocus = -1;

    selectedTeacher = null;
    renderTeachers();

    if (!rawVal || !TEACHERS_DATA) return;

    const matches = TEACHERS_DATA.teachers.filter(t => matchesTeacher(t, rawVal)).slice(0, 7);

    matches.forEach(t => {
      const item = document.createElement("div");
      item.innerHTML = `
        <span class="autocomplete-title">${t.name}</span>
        <span class="autocomplete-item-sub">${t.office ? 'Despacho ' + t.office : 'Despacho N/A'}</span>
      `;
      item.addEventListener("click", function(e) {
        e.stopPropagation();
        selectedTeacher = t;
        input.value = t.name;
        listContainer.innerHTML = "";
        renderTeachers();
      });
      listContainer.appendChild(item);
    });
  });

  input.addEventListener("keydown", function(e) {
    let items = listContainer.getElementsByTagName("div");
    if (e.keyCode === 40) {
      currentFocus++;
      addActive(items);
    } else if (e.keyCode === 38) {
      currentFocus--;
      addActive(items);
    } else if (e.keyCode === 13) {
      e.preventDefault();
      if (currentFocus > -1 && items[currentFocus]) {
        items[currentFocus].click();
      }
    } else if (e.keyCode === 27) {
      listContainer.innerHTML = "";
    }
  });

  document.addEventListener("click", function(e) {
    closeAllLists(e.target);
  });
}

boot();
