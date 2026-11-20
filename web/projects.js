// My projects: save several projects and switch between them (like the fence checker's FC-XXXXXX projects).
//
// Where they're saved: in THIS browser only (localStorage), not on the server. That way, when the site is
// public, nobody can see anyone else's projects, and nothing is lost when the free host restarts.
// "Download a backup" saves them all to a file, and "Restore" loads that file on another computer.
//
// Like the fence checker, only the ANSWERS (plus the AI notes: drawings summary, vibes check, chat) are saved,
// never PASS/FAIL. Results are worked out again every time a project is opened, so they always use the current rules.
//
// How it works: the project you're working on lives in the usual keys (permitCheckerAnswers, permitDrawings...).
// Every time one of those changes, a copy goes into its project in "permitProjects". Opening another project
// copies that project's saved keys back. Loaded after app.js.

const PROJECTS_KEY = "permitProjects", CURRENT_KEY = "permitCurrentProject";
const PROJECT_PARTS = [STORE, DRAWINGS_KEY, VIBES_KEY, CHAT_KEY, YARD_KEY, CHECK_KEY];   // everything one project owns

function projList() { return recallJson(PROJECTS_KEY) || []; }
function projStore(list) {
  try { localStorage.setItem(PROJECTS_KEY, JSON.stringify(list)); return true; }
  catch (e) { return false; }                       // browser storage full or blocked: the current project still works
}
function currentId() { return getPref(CURRENT_KEY); }

function newProjectId() {
  const abc = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";     // no 0/O or 1/I, easy to read aloud (same as the fence checker)
  let id;
  do { id = "PC-" + Array.from(crypto.getRandomValues(new Uint8Array(6)), b => abc[b % abc.length]).join(""); }
  while (projList().some(p => p.id === id));
  return id;
}

function autoName(answers) {
  const type = (answers.project_type || "").replace(/\s*\(.*\)$/, "");
  return [type, answers.address].filter(Boolean).join(" · ") || "Untitled project";
}

function snapshot() {                                 // the current project's saved keys, exactly as stored
  const data = {};
  PROJECT_PARTS.forEach(k => { const v = getPref(k); if (v !== null) data[k] = v; });
  return data;
}

// Called by app.js whenever answers, drawings, vibes, chat, yard direction or the checklist change.
function projectChanged() {
  if (!Object.keys(ANSWERS).length) return;           // nothing to save yet
  const list = projList();
  let p = list.find(x => x.id === currentId());
  const now = new Date().toISOString();
  if (!p) {
    p = {id: newProjectId(), created: now, named: false};
    list.unshift(p);
    setPref(CURRENT_KEY, p.id);
  }
  if (!p.named) p.name = autoName(ANSWERS);
  p.project_type = ANSWERS.project_type || "";
  p.address = ANSWERS.address || "";
  p.updated = now;
  p.data = snapshot();
  projStore(list);
}

function clearCurrent() {
  PROJECT_PARTS.forEach(k => { try { localStorage.removeItem(k); } catch (e) {} });
  try { localStorage.removeItem("permitCheckerReport"); localStorage.removeItem(CURRENT_KEY); } catch (e) {}
  ANSWERS = {}; REPORT = null; FILTER = null; AI_RESULT = null; AI_DONE = ""; CHAT = [];
  chatRender();                                       // an open chat panel shows the new project's chat
}

function newProject() {
  projectChanged();                                   // make sure the one you were on is saved
  clearCurrent();
  go("#/check/1");
}

function openProject(id) {
  const p = projList().find(x => x.id === id);
  if (!p) return;
  projectChanged();
  clearCurrent();
  Object.entries(p.data || {}).forEach(([k, v]) => setPref(k, v));
  setPref(CURRENT_KEY, p.id);
  ANSWERS = load();
  CHAT = recallJson(CHAT_KEY) || [];
  chatRender();
  go(ANSWERS.project_type ? "#/check/5" : "#/check/1");
}

function renameProject(id) {
  const list = projList(), p = list.find(x => x.id === id);
  if (!p) return;
  const name = prompt("New name for this project:", p.name);
  if (name === null) return;
  p.name = name.trim().slice(0, 80) || autoName(recallJson(STORE) || {});
  p.named = !!name.trim();
  projStore(list);
  showProjects();
}

function deleteProject(id) {
  const list = projList(), p = list.find(x => x.id === id);
  if (!p) return;
  if (!confirm(`Delete “${p.name}” (${p.id})? This can't be undone, unless you downloaded a backup.`)) return;
  projStore(list.filter(x => x.id !== id));
  if (id === currentId()) clearCurrent();
  showProjects();
}

// ---------- backup file (move projects to another computer or browser)
function downloadBackup() {
  projectChanged();
  const file = {about: "Toronto Permit Pre-Check projects backup. Answers only: results are worked out again when opened.",
                saved: new Date().toISOString(), projects: projList()};
  download(`permit-projects-${new Date().toISOString().slice(0, 10)}.json`, JSON.stringify(file, null, 1), "application/json");
}

async function restoreBackup(input) {
  const f = input.files[0];
  if (!f) return;
  let added = 0;
  try {
    const file = JSON.parse(await f.text());
    const list = projList();
    for (const p of file.projects || []) {
      if (!p || typeof p !== "object" || !p.data || typeof p.data !== "object") continue;
      const data = {};                                // keep only our own keys, as text
      PROJECT_PARTS.forEach(k => { if (typeof p.data[k] === "string") data[k] = p.data[k]; });
      if (!data[STORE]) continue;
      const same = list.find(x => x.id === p.id);
      if (same && same.data?.[STORE] === data[STORE]) continue;     // already here, unchanged: don't make a duplicate
      const id = /^PC-[A-Z2-9]{6}$/.test(p.id) && !list.some(x => x.id === p.id) ? p.id : newProjectId();
      list.push({id, name: String(p.name || "Restored project").slice(0, 80), named: !!p.named,
                 project_type: String(p.project_type || ""), address: String(p.address || ""),
                 created: String(p.created || new Date().toISOString()), updated: String(p.updated || new Date().toISOString()), data});
      added++;
    }
    if (!projStore(list)) throw new Error("This browser's storage is full.");
    alert(added ? `Restored ${added} project${added === 1 ? "" : "s"}.` : "Nothing new in that file: those projects are already here.");
  } catch (e) {
    alert("That file couldn't be read as a projects backup. " + (e.message || ""));
  }
  showProjects();
}

// ---------- example projects (the three test cases from Nov 18, with their real AI results)
let EXAMPLES = null;
async function examples() {
  if (!EXAMPLES) { try { EXAMPLES = (await (await fetch("/web/examples.json")).json()).examples || []; } catch (e) { EXAMPLES = []; } }
  return EXAMPLES;
}

async function addExample(i) {
  const ex = (await examples())[i];
  if (!ex) return;
  projectChanged();
  clearCurrent();
  ANSWERS = JSON.parse(JSON.stringify(ex.answers));
  save();                                             // creates a new project (and saves it) through projectChanged()
  if (ex.drawings) storeJson(DRAWINGS_KEY, ex.drawings);
  if (ex.vibes) storeJson(VIBES_KEY, {key: answersKey(), result: ex.vibes});
  if (ex.chat) { CHAT = ex.chat; storeJson(CHAT_KEY, CHAT); }
  if (ex.yard) { setPref(YARD_KEY, ex.yard); }
  const list = projList(), p = list.find(x => x.id === currentId());
  if (p) { p.name = ex.name; p.named = true; p.data = snapshot(); projStore(list); }
  go("#/check/5");
}

// ---------- the page
function when(iso) {
  const d = new Date(iso);
  return isNaN(d) ? "" : d.toLocaleString("en-CA", {month: "short", day: "numeric", hour: "numeric", minute: "2-digit"});
}

async function showProjects() {
  projectChanged();
  const list = projList(), cur = currentId(), ex = await examples();
  app.innerHTML = `
    <div class="spread"><div><p class="eyebrow">Saved on this computer</p><h2 style="margin:2px 0 0">My projects</h2></div>
      <button type="button" class="primary" onclick="newProject()">+ New project</button></div>
    <p class="muted">Every project saves itself as you go. Only your answers are saved: the results are worked out again each time
      you open a project, so they always use the latest rules. Projects stay in this browser. Nobody else using this site can see them.</p>

    ${list.length ? `<div class="proj-list">${list.map(p => `
      <div class="card proj ${p.id === cur ? "current" : ""}">
        <div class="proj-main">
          <div class="proj-name"><b>${esc(p.name)}</b>${p.id === cur ? ` <span class="chip">Open now</span>` : ""}</div>
          <div class="muted small">${esc(p.id)} · ${esc(p.project_type || "no project type yet")}${p.address ? " · " + esc(p.address) : ""} · saved ${esc(when(p.updated))}</div>
          <div class="proj-counts small" data-counts="${esc(p.id)}"><span class="muted">Checking…</span></div>
        </div>
        <div class="row">
          <button type="button" class="primary" onclick="openProject('${p.id}')">Open</button>
          <button type="button" onclick="renameProject('${p.id}')">Rename</button>
          <button type="button" class="link danger" onclick="deleteProject('${p.id}')">Delete</button>
        </div>
      </div>`).join("")}</div>`
    : `<div class="card"><b>No projects yet.</b><p class="muted small" style="margin:4px 0 0">Start a check, or open one of the examples below.</p></div>`}

    ${ex.length ? `<h3 style="margin-top:28px">Example projects</h3>
      <p class="muted small">Three made-up projects from our test run, with the real AI results from that run. Opening one adds a copy to your projects.</p>
      <div class="proj-list">${ex.map((e, i) => `
        <div class="card proj">
          <div class="proj-main"><div class="proj-name"><b>${esc(e.name)}</b> <span class="chip">Example</span></div>
            <div class="muted small">${esc(e.blurb)}</div></div>
          <button type="button" onclick="addExample(${i})">Open a copy</button>
        </div>`).join("")}</div>` : ""}

    <div class="card" style="margin-top:28px">
      <b>Backup</b>
      <p class="muted small" style="margin:4px 0 10px">Clearing your browser's data deletes these projects. Download a backup to keep them,
        or to move them to another computer. The file has your answers (and any address), so keep it private.</p>
      <div class="row"><button type="button" onclick="downloadBackup()" ${list.length ? "" : "disabled"}>Download a backup</button>
        <label class="file-pick"><input type="file" accept=".json,application/json" onchange="restoreBackup(this)"><span>Restore from a backup</span></label></div>
    </div>`;
  animateIn(app, "page-enter");
  focusHeading();
  // The fence checker's way: work the results out fresh from the saved answers (our own checker, no AI, nothing saved)
  for (const p of list) {
    const box = app.querySelector(`[data-counts="${p.id}"]`);
    let answers = {};
    try { answers = JSON.parse(p.data?.[STORE] || "{}"); } catch (e) {}
    if (!answers.project_type) { box.innerHTML = `<span class="muted">Not checked yet</span>`; continue; }
    api("/api/check", {inputs: answers}).then(r => {
      const c = r.counts || {};
      box.innerHTML = r.stopped ? `<span class="st-FAIL">${icon("FLAG")} Checks stopped: open it to see why</span>`
        : [["FAIL", "don't pass"], ["NEED MORE INFO", "need an answer"], ["PASS", "pass"]]
            .map(([s, w]) => `<span class="st-${s.split(" ")[0]}">${icon(s)} ${c[s] || 0} ${w}</span>`).join(" ");
    }).catch(() => { box.innerHTML = `<span class="muted">Couldn't check</span>`; });
  }
}
