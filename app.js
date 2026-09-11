const TZ = "Europe/Madrid";
let DATA = null;
let TEACHERS_DATA = null;
let activeFilter = 'all';
let selectedTeacher = null;

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

  // 1. DETAIL VIEW: Runs when a card or autocomplete item is selected
  if (selectedTeacher) {
    const t = selectedTeacher;
    const subjectsText = t.subjects && t.subjects.length 
      ? t.subjects.map(s => `<span class="chip"><b>${s}</b></span>`).join(" ")
      : "Docencia no especificada";

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
        ← Volver al buscador
      </button>
      <div class="card free" style="cursor: default; padding:20px;">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:8px;">
          <div>
            <div class="room" style="font-size:1.5rem;">${t.name}</div>
            <div class="cls" style="font-size:1rem; margin-top:4px;">
              <a href="mailto:${t.email}" class="card-link">${t.email || 'Sin correo'}</a>
            </div>
          </div>
          <span class="pill" style="background:var(--panel2); color:var(--accent); font-size:0.95rem; padding: 6px 12px;">
            DESPACHO: ${t.office || 'N/A'}
          </span>
        </div>

        <div style="margin-top:20px;">
          <b style="display:block; margin-bottom:8px;">Asignaturas:</b>
          <div>${subjectsText}</div>
        </div>

        ${t.tutoring_url ? `
          <div style="margin-top:16px;">
             <a href="${t.tutoring_url}" target="_blank" rel="noopener" class="card-link" style="font-size:1rem;">Ver Horario de Tutorías ↗</a>
          </div>
        ` : ''}

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

  // 2. SEARCH GRID: Concise cards (Name, Email, Office only)
  const query = (document.getElementById("teacherSearch")?.value || "").toLowerCase().trim();

  const filtered = TEACHERS_DATA.teachers.filter(t => {
    const nameMatch = t.name.toLowerCase().includes(query);
    const officeMatch = (t.office || "").toLowerCase().includes(query);
    const subjectMatch = (t.subjects || []).some(s => s.toLowerCase().includes(query));
    return nameMatch || officeMatch || subjectMatch;
  });

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
          DESPACHO: ${t.office || 'N/A'}
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
    const val = this.value.trim().toLowerCase();
    listContainer.innerHTML = "";
    currentFocus = -1;

    selectedTeacher = null;
    renderTeachers();

    if (!val || !TEACHERS_DATA) return;

    const matches = TEACHERS_DATA.teachers.filter(t => {
      const nameMatch = t.name.toLowerCase().includes(val);
      const officeMatch = (t.office || "").toLowerCase().includes(val);
      const subjectMatch = (t.subjects || []).some(s => s.toLowerCase().includes(val));
      return nameMatch || officeMatch || subjectMatch;
    }).slice(0, 7);

    matches.forEach(t => {
      const item = document.createElement("div");
      item.innerHTML = `
        <span class="autocomplete-title">${t.name}</span>
        <span class="autocomplete-item-sub">${t.office ? 'Despacho ' + t.office : ''}</span>
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
    if (e.keyCode === 40) { // Down key
      currentFocus++;
      addActive(items);
    } else if (e.keyCode === 38) { // Up key
      currentFocus--;
      addActive(items);
    } else if (e.keyCode === 13) { // Enter key
      e.preventDefault();
      if (currentFocus > -1 && items[currentFocus]) {
        items[currentFocus].click();
      }
    } else if (e.keyCode === 27) { // Escape key
      listContainer.innerHTML = "";
    }
  });

  document.addEventListener("click", function(e) {
    closeAllLists(e.target);
  });
}

boot();