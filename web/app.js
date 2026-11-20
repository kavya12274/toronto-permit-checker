// The main page: home, the 5 steps, and the results.
// All PASS/FAIL decisions happen in Python (checker/). This file only asks the questions and shows answers.
//
// Pages (the part of the address after #):
//   #/          home
//   #/check/1   Step 1 Project       (pick a project type)
//   #/check/2   Step 2 Property      (address lookup, zone, map values, approvals questions)
//   #/check/3   Step 3 Lot & house
//   #/check/4   Step 4 Measurements  (only the sections that matter for the project type)
//   #/check/5   Step 5 Results

const app = document.getElementById("app");
let SETUP = null;        // questions, sections and project profiles from /api/setup
let ANSWERS = {};        // the user's answers (this is what a future AI plan reader would fill in)
let REPORT = null;       // the last results
let FILTER = null;       // which summary tile is selected on the results page
const STORE = "permitCheckerAnswers";

// Which sections go on which step
const STEP_SECTIONS = {
  2: ["property", "overlay", "approvals"],
  3: ["lot", "house"],
};
const NOT_ON_STEP4 = ["project", "property", "overlay", "approvals", "lot", "house"];

// A line icon and one-line explanation for each project type (shown on step 1).
// Icons are drawn here (24x24, same stroke everywhere) so they match each other and the page colours.
const ICONS = {
  rear: "M2 11l8-6 8 6M4 10v10h12V10M16 13h5v7h-5",
  second: "M4 21V9l8-6 8 6v12zM4 14h16M10 21v-4h4v4",
  porch: "M3 11l9-7 9 7M5 10v8h14v-8M10 18v-5h4v5M5 21h14",
  deck: "M3 10h18v3H3zM5 13v8M19 13v8M12 13v8M3 10V6M21 10V6M3 6h18",
  shed: "M4 21V10l8-5 8 5v11zM10 21v-6h4v6",
  garage: "M3 21V9l9-5 9 5v12M7 21v-8h10v8M7 16h10M7 18.5h10",
  pool: "M2 17c2 0 2-1.5 4-1.5s2 1.5 4 1.5 2-1.5 4-1.5 2 1.5 4 1.5 2-1.5 4-1.5M2 21c2 0 2-1.5 4-1.5s2 1.5 4 1.5 2-1.5 4-1.5 2 1.5 4 1.5 2-1.5 4-1.5M8 13V6a2 2 0 0 1 4 0M14 13V6a2 2 0 0 1 4 0M8 9h4M14 9h4",
  garden: "M3 21v-7l5-4 5 4v7zM18 21v-5M18 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM2 21h20",
  laneway: "M3 21v-8l6-5 6 5v8zM8 21v-4h2v4M19 4v2M19 9v2M19 14v2M19 19v2",
  secondary: "M3 11l9-7 9 7M5 10v11h14V10M5 15h14M9 18h6",
  multiplex: "M5 21V4h14v17M9 8h2M13 8h2M9 12h2M13 12h2M10 21v-4h4v4M3 21h18",
  newhouse: "M3 12l7-6 7 6M5 11v10h10V11M9 21v-5h2v5M19 3v4M17 5h4",
  interior: "M4 20l10-10M13 4l7 7-3 3-7-7z",
  driveway: "M8 21l2-18M16 21l-2-18M12 5v2M12 10v2M12 15v2",
  solar: "M3 21l3-8h12l3 8zM9.5 13L8 21M14.5 13L16 21M4.5 17h15M12 3v2M7 5l1.2 1.5M17 5l-1.2 1.5",
  demolition: "M3 11l9-7 9 7M5 10v11h14V10M12 10l-2 4 3 2-2 5",
};
function lineIcon(name, cls = "ico") {
  return `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true"><path d="${ICONS[name] || ICONS.rear}"/></svg>`;
}
const PROJECT_INFO = {
  "Rear addition (1 or 2 storey)": ["rear", "Add space at the back"],
  "Second-storey addition": ["second", "Build up a floor"],
  "Front porch / front addition": ["porch", "Porch or addition at the front"],
  "Deck / platform": ["deck", "Deck, platform or balcony"],
  "Shed / accessory building": ["shed", "Shed, workshop, pool house"],
  "Detached garage": ["garage", "Garage or carport"],
  "Pool": ["pool", "In-ground or above-ground pool"],
  "Garden suite": ["garden", "A small home in the back yard"],
  "Laneway suite": ["laneway", "A small home on the lane"],
  "Secondary suite (e.g. basement apartment)": ["secondary", "A second unit inside the house"],
  "Multiplex conversion (house to 2-4 units)": ["multiplex", "Turn a house into 2–4 units"],
  "New detached house / houseplex (replacement)": ["newhouse", "Replace the house with a new one"],
  "Interior alterations / basement finishing": ["interior", "Renovate inside or finish a basement"],
  "Driveway / parking pad": ["driveway", "Driveway, parking pad, curb cut"],
  "Solar panels": ["solar", "Panels on the roof"],
  "Demolition only": ["demolition", "Take down all or part of a building"],
};

// Step 4 shows the key measurements first; the rest of a section folds away under "More questions".
const CORE = {
  main: ["height", "storeys", "building_length", "building_depth", "front_setback", "rear_setback", "side_setback",
         "side_setback_other", "side_wall_openings", "fsi", "lot_coverage", "roof_type", "main_wall_height"],
  ancillary: ["anc_area", "anc_storeys", "anc_height", "anc_to_house", "anc_rear_setback", "anc_side_setback", "anc_attached", "anc_plumbing", "anc_storage_only"],
  deck: ["deck_height", "deck_is_exit", "deck_level", "deck_location", "deck_encroachment", "deck_setback"],
  garden: ["other_suite_building", "gs_height", "gs_storeys", "gs_to_house", "gs_rear_setback", "gs_side_setback", "gs_side_openings", "gs_gfa"],
  laneway: ["ls_length", "ls_width", "ls_height", "ls_storeys", "ls_to_house", "ls_rear_setback", "ls_side_setback"],
};
// Sections that fold closed (they open by themselves if "Answer this question" points into them)
const OPTIONAL_SECTIONS = ["overlay", "approvals", "permit", "projections", "landscape", "code"];

// ---------------------------------------------------------------- small helpers
function save() { try { localStorage.setItem(STORE, JSON.stringify(ANSWERS)); } catch (e) { /* private window: fine */ } window.projectChanged?.(); }
function load() { try { return JSON.parse(localStorage.getItem(STORE)) || {}; } catch (e) { return {}; } }
function setPref(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
function getPref(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }

async function api(path, body) {
  let res;
  try {
    res = await fetch(path, body ? {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)} : {});
  } catch (e) {
    throw new Error("Can't reach the checker. Check your internet, or try again in a minute. (On your own computer: is python3 app.py still running?)");
  }
  const data = await res.json();
  if (data.error) throw new Error(data.error);
  return data;
}

function field(key) { return SETUP.fields.find(f => f.key === key); }

// "Simple words" switch: plain wording everywhere (English only; other languages use their own translation)
function isSimple() { return LANG === "en" && !!document.getElementById("simple")?.checked; }

// Homeowner mode: plain words, the essentials. Designer mode: every number, section reference and export.
function isDesigner() { return document.documentElement.classList.contains("mode-designer"); }
function profile() { return SETUP.profiles[ANSWERS.project_type] || null; }

function sectionsForStep(step) {
  if (step === 1) return ["project"];
  if (STEP_SECTIONS[step]) return STEP_SECTIONS[step];
  const p = profile();
  return p ? p.sections.filter(s => !NOT_ON_STEP4.includes(s)) : [];
}

function stepOfField(key) {
  const sec = field(key)?.section;
  for (const s of [1, 2, 3, 4]) if (sectionsForStep(s).includes(sec)) return s;
  return 4;
}

// Restart a small entry animation (styles in style.css, "motion"). Skipped automatically if motion is reduced.
function animateIn(el, cls) {
  if (!el) return;
  el.classList.remove(cls);
  void el.offsetWidth;          // lets the browser notice the class was removed, so the animation plays again
  el.classList.add(cls);
}

// Move focus to the new page's heading, so keyboard and screen-reader users know the page changed.
function focusHeading() {
  window.scrollTo(0, 0);
  if (document.querySelector("dialog.guide[open]")) return;
  const h = app.querySelector("h2");
  if (h) { h.setAttribute("tabindex", "-1"); h.focus({preventScroll: true}); }
}

// ---------------------------------------------------------------- routing
function route() {
  const hash = location.hash || "#/";
  GLOSS_USED = new Set();
  const m = hash.match(/^#\/check\/(\d)/);
  document.querySelectorAll("[data-nav]").forEach(a => a.removeAttribute("aria-current"));
  document.body.dataset.page = /^#\/check\/5/.test(hash) ? "results" : "other";   // the draft label is strongest on results
  document.getElementById("settings-menu")?.removeAttribute("open");
  if (hash.startsWith("#/stats")) {
    document.querySelector('[data-nav="stats"]').setAttribute("aria-current", "page");
    showStats();
  } else if (hash.startsWith("#/dictionary")) {
    showDictionary();
  } else if (hash.startsWith("#/build")) {
    document.querySelector('[data-nav="build"]').setAttribute("aria-current", "page");
    showBuild();
  } else if (hash.startsWith("#/projects")) {
    document.querySelector('[data-nav="projects"]')?.setAttribute("aria-current", "page");
    showProjects();
  } else if (hash.startsWith("#/compare")) {
    document.querySelector('[data-nav="check"]').setAttribute("aria-current", "page");
    showCompare();
  } else if (m) {
    document.querySelector('[data-nav="check"]').setAttribute("aria-current", "page");
    const step = Math.min(5, Math.max(1, +m[1]));
    if (step > 1 && !ANSWERS.project_type) { location.hash = "#/check/1"; return; }
    step === 5 ? showResults() : showStep(step);
  } else {
    document.querySelector('[data-nav="home"]').setAttribute("aria-current", "page");
    showHome();
  }
}
function go(hash) { if (location.hash === hash) route(); else location.hash = hash; }

// ---------------------------------------------------------------- home page
function showHome() {
  const n = Object.keys(ANSWERS).length;
  const types = SETUP.profiles ? Object.keys(SETUP.profiles).length : 16;
  app.innerHTML = `
    <section class="hero">
      <div>
        <p class="eyebrow"><span class="live" aria-hidden="true"></span>Toronto · Zoning By-law 569-2013</p>
        <h2>Can you <span class="grad">build it?</span></h2>
        <p>${isSimple()
          ? "Tell us what you want to build. We check it against Toronto's rules and show what's OK, what's not, and how to fix it. It's free."
          : "Tell us about your home project. We check it against Toronto's zoning rules, key Building Code rules and other approvals, and show you what passes, what doesn't, and how to fix it. Free, and it runs on your own computer."}</p>
        <div class="row">
          <button class="primary big" onclick="${n ? "newProject()" : "go('#/check/1')"}">${n ? "Start a new project" : "Start a pre-check"}</button>
          <button class="big" onclick="openGuide()">▶ How it works</button>
        </div>
        <div class="hero-stats" aria-label="What the checker covers">
          <span><b>174</b>rules</span><span><b>${types}</b>project types</span>
          ${SETUP.stats ? `<span><b>${SETUP.stats.overall.permits.toLocaleString("en-CA")}</b>permits analysed</span>` : ""}
          <span><b>47</b>terms explained</span>
        </div>
      </div>
      <div class="art">${heroArt()}</div>
    </section>

    ${n && ANSWERS.project_type ? `
    <div class="card spread">
      <div><b>Continue where you left off</b>
        <div class="muted small">${esc(ANSWERS.project_type)} · ${n} answers saved on this computer</div></div>
      <div class="row"><button class="primary" onclick="go('#/check/5')">See results</button>
        <button onclick="go('#/check/2')">Keep answering</button>
        <button onclick="go('#/projects')">All my projects</button></div>
    </div>` : ""}

    <div class="card feature spread">
      <div><p class="eyebrow">New</p><h3 style="margin:2px 0 4px">What can I build on my lot?</h3>
        <p class="muted small" style="margin:0">Don't have a design yet? Enter your lot and we work the rules backwards to show the
          biggest addition, garden suite, laneway suite or multiplex allowed.</p></div>
      <button class="primary" onclick="go('#/build')">Find out →</button>
    </div>

    <div class="howto">
      ${[["Pick your project", "Addition, deck, garden suite, basement apartment…"],
         ["About the property", "Type the address and we look up the zoning map for you."],
         ["Add measurements", "Only the ones that matter. Skip what you don't know."],
         ["Get your report", "Every rule with its by-law section, ready to print."]]
        .map(([b, s], i) => `<div><span class="num" aria-hidden="true">${i + 1}</span><b>${b}</b>${s}</div>`).join("")}
    </div>

    <div class="card example">
      <div class="spread"><h3>What a result looks like</h3><span class="chip NEED">Example</span></div>
      <p class="muted small" style="margin:0 0 4px">Every rule says PASS, FAIL, NEED MORE INFO or FLAG, with the limit, your number,
        the by-law section and how sure we are. A FAIL tells you the smallest change that would pass.</p>
      ${resultCard({status: "FAIL", title: "Min side setback 0.9 m", category: "Side setback", rule_id: "RD-18",
        section: "10.20.40.70(3)(B)", limit: 0.9, value: 0.8, unit: "m", confidence: "High", link: "",
        message: "Frontage 10.0 m needs 0.9 m side setbacks. Yours: 0.8 m.",
        fix: "Move the wall 0.1 m in, so the side setback goes 0.8 → 0.9 m."})}
      <p class="muted small" style="margin-top:12px">${types} project types · 174 rules from Toronto's Zoning By-law 569-2013,
        the Ontario Building Code and provincial rules · approvals like heritage, trees and TRCA. Building Code results always
        need a qualified designer to confirm. A draft pre-check, not an approval.</p>
    </div>`;
  animateIn(app, "page-enter");
  focusHeading();
}

// ---------------------------------------------------------------- the steps
function stepper(current) {
  const names = [t("step1"), t("step2"), t("step3"), t("step4"), t("step5")];
  const full = `<ol class="stepper no-print" aria-label="Progress">${names.map((name, i) => {
    const n = i + 1, cls = n < current ? "done" : n === current ? "current" : "";
    const disabled = n > 1 && !ANSWERS.project_type;
    return `<li class="${cls}"><button type="button" onclick="go('#/check/${n}')" ${disabled ? "disabled" : ""}
      ${n === current ? 'aria-current="step"' : ""}>${esc(name)}</button></li>`;
  }).join("")}</ol>`;
  // phones: one short line and a bar instead of five buttons
  const compact = `<div class="step-compact no-print" aria-hidden="true"><span>Step ${current} of 5 · <b>${esc(names[current - 1])}</b></span>
    <span class="bar"><span style="width:${current * 20}%"></span></span></div>`;
  return full + compact + contextLine(current);
}

// "Rear addition · 123 Example St · RD · lot 10 × 36 m": what you've told us so far. Each part opens its step.
function contextLine(current) {
  if (!ANSWERS.project_type || current === 1) return "";
  const a = ANSWERS, parts = [];
  parts.push([1, a.project_type.replace(/ \(.*\)$/, "")]);
  if (a.address || a.zone_label || a.zone) parts.push([2, [a.address, a.zone_label || a.zone].filter(Boolean).join(" · ")]);
  if (a.lot_frontage || a.lot_depth) parts.push([3, `lot ${a.lot_frontage ?? "?"} × ${a.lot_depth ?? "?"} m`]);
  return `<p class="context no-print">${parts.map(([n, text]) =>
    `<a href="#/check/${n}" title="Change">${esc(text)}</a>`).join('<span aria-hidden="true">·</span>')}</p>`;
}

const STEP_TEXT = {
  1: ["What are you building?", "Pick the project type. You can change it later."],
  2: ["Tell us about the property", "Type the address and press Look up: we fill in the zoning map values for you. Check what it fills in."],
  3: ["The lot and the house", "Lot size and the house as it will be after the project. Skip anything you don't know."],
  4: ["Your project's measurements", "From your drawings or a tape measure. Leave a question blank if you don't know: it will say NEED MORE INFO, never PASS."],
};

const STEP_TEXT_SIMPLE = {
  1: ["What are you building?", "Tap the one that fits best."],
  2: ["Where is it?", "Type the address and tap Look up. We fill in the map details for you."],
  3: ["Your lot and house", "Fill in what you know. Skip the rest."],
  4: ["Your measurements", "Use your drawings or a tape measure. Don't know one? Skip it. We'll tell you what's missing."],
};

function showStep(step) {
  GLOSS_USED = new Set();
  const [title, intro] = (isSimple() ? STEP_TEXT_SIMPLE : STEP_TEXT)[step];
  let body = "";
  if (step === 1) body = projectPicker();
  else {
    // main sections first, optional (folded) ones after
    const all = sectionsForStep(step);
    const secs = [...all.filter(sec => !OPTIONAL_SECTIONS.includes(sec)), ...all.filter(sec => OPTIONAL_SECTIONS.includes(sec))];
    // fold optional sections only if the step still has a main one open
    const hasMain = secs.some(sec => !OPTIONAL_SECTIONS.includes(sec)) && !isDesigner();   // designers see every section open
    body = secs.map(sec => sectionCard(sec, step, hasMain && OPTIONAL_SECTIONS.includes(sec))).join("") ||
      `<div class="card"><p>No extra measurements are needed for this project type. Go to the results.</p></div>`;
  }
  app.innerHTML = `
    ${stepper(step)}
    <div class="step-head card"><h2>${esc(title)}</h2><p class="muted">${esc(intro)}</p></div>
    <form id="form" onsubmit="return false" novalidate>${body}</form>
    <div class="step-foot no-print">
      ${step > 1 ? `<button type="button" onclick="go('#/check/${step - 1}')">${esc(t("back"))}</button>` : "<span></span>"}
      <div class="row">
        ${step < 4 && ANSWERS.project_type ? `<button type="button" class="link" onclick="go('#/check/5')">${esc(t("see_results"))}</button>` : ""}
        <button type="button" class="primary big" onclick="go('#/check/${step + 1}')" ${step === 1 && !ANSWERS.project_type ? "disabled" : ""}
          id="next">${step === 4 ? esc(t("check")) : esc(t("next"))}</button>
      </div>
    </div>`;
  wireForm();
  if (step === 2) wireLookup();
  if (step === 1) wireAiBox();
  animateIn(app, "page-enter");
  focusHeading();
}

function projectPicker() {
  const types = SETUP.fields.find(f => f.key === "project_type").choices;
  return `<div class="card"><fieldset style="border:none;margin:0;padding:0">
      <legend class="sr-only">Project type</legend>
      <div class="choices">${types.map(type => {
        const [ico, sub] = PROJECT_INFO[type] || ["rear", ""];
        return `<label class="choice"><input type="radio" name="project_type" value="${esc(type)}" ${ANSWERS.project_type === type ? "checked" : ""}>
          ${lineIcon(ico)}<span>${esc(type)}<span class="sub">${esc(sub)}</span></span></label>`;
      }).join("")}</div></fieldset>
      ${fieldHtml(field("description"))}
    </div>
    ${aiBox()}`;
}

const SECTION_HELP = {
  overlay: "These numbers change from property to property. Look up fills them in, or find them on the City's zoning map (toronto.ca/zoning).",
  approvals: "These decide which other approvals you need. Look up fills in some of them.",
  permit: "These decide whether a building permit is needed.",
  code: "Building Code safety basics. A qualified designer must always confirm these.",
};

const SECTION_HELP_SIMPLE = {
  overlay: "These numbers come from the City's map. Look up fills them in.",
  approvals: "These tell us if you need other permits. Look up fills in some.",
  permit: "These tell us if you need a building permit.",
  code: "Safety basics. A qualified designer must always check these.",
};

function sectionCard(sec, step, folded = false) {
  const title = (SETUP.sections.find(s => s[0] === sec) || [sec, sec])[1];
  const fields = SETUP.fields.filter(f => f.section === sec && !(sec === "property" && f.key === "address"));
  const answered = fields.filter(f => f.key in ANSWERS).length;
  const count = answered === 0 ? (folded ? "Optional" : "")
    : answered === fields.length ? "All answered" : `${answered} of ${fields.length} answered`;
  const core = step === 4 && CORE[sec] ? fields.filter(f => CORE[sec].includes(f.key)) : fields;
  const more = fields.filter(f => !core.includes(f));
  const moreAnswered = more.filter(f => f.key in ANSWERS).length;
  const inner = `
    ${(isSimple() ? SECTION_HELP_SIMPLE : SECTION_HELP)[sec] ? `<p class="muted small" style="margin:0">${esc((isSimple() ? SECTION_HELP_SIMPLE : SECTION_HELP)[sec])}</p>` : ""}
    ${sec === "property" ? lookupBox() : ""}
    ${core.map(fieldHtml).join("")}
    ${more.length ? `<details class="more" ${moreAnswered || isDesigner() ? "open" : ""}><summary>More questions (${more.length})${moreAnswered ? ` · ${moreAnswered} answered` : ""}</summary>
      ${more.map(fieldHtml).join("")}</details>` : ""}`;
  if (folded) {
    return `<details class="card form-section folded">
      <summary><h3 id="sec-${sec}">${esc(title)}</h3><span class="muted small" data-count="${sec}">${count}</span></summary>${inner}</details>`;
  }
  return `<section class="card form-section" aria-labelledby="sec-${sec}">
    <h3 id="sec-${sec}">${esc(title)} <span class="muted small" data-count="${sec}">${count}</span></h3>${inner}
  </section>`;
}

function lookupBox() {
  const f = field("address");
  return `<div class="lookup-box field" data-key="address">
    <label for="f_address">${esc(f.label)}</label>
    <div class="row" style="flex-wrap:nowrap"><input type="text" id="f_address" name="address" value="${esc(ANSWERS.address || "")}"
      placeholder="e.g. 123 Example St" autocomplete="street-address">
      ${SETUP.lookup_available ? `<button type="button" class="primary" id="lookup">Look up</button>` : ""}</div>
    <div class="lookup-status" id="lookup-status" role="status"></div>
    <div class="help">Looks up the City of Toronto's zoning map and TRCA's map. Your address is sent to the City's map search.</div>
  </div>`;
}

// One question
function fieldHtml(f) {
  if (!f) return "";
  if (isSimple() && f.simple) f = Object.assign({}, f, {label: f.simple});   // plain wording
  const id = `f_${f.key}`, v = ANSWERS[f.key];
  const answered = f.key in ANSWERS ? " answered" : "";
  const helpId = f.help ? `${id}_help` : "";
  const help = f.help ? (f.help.length > 110
    ? `<details class="where" id="${helpId}"><summary>Where do I find this?</summary>${esc(f.help)}</details>`
    : `<div class="help" id="${helpId}">${esc(f.help)}</div>`) : "";
  const described = helpId ? `aria-describedby="${helpId}"` : "";

  if (f.type === "yesno") {
    const opt = (val, label, cls = "") => `<label class="pill ${cls}"><input type="radio" name="${f.key}" value="${val}"
      ${(val === "yes" && v === true) || (val === "no" && v === false) || (val === "" && v === undefined) ? "checked" : ""}>${label}</label>`;
    return `<div class="field${answered}" data-key="${f.key}"><fieldset ${described}><legend>${glossify(esc(f.label))}</legend>
      <div class="pills">${opt("yes", "Yes")}${opt("no", "No")}${opt("", "Don't know", "unknown")}</div></fieldset>${help}</div>`;
  }
  if (f.type === "choice" && f.choices.length <= 5) {
    return `<div class="field${answered}" data-key="${f.key}"><fieldset ${described}><legend>${glossify(esc(f.label))}</legend>
      <div class="pills">${f.choices.map(c => `<label class="pill"><input type="radio" name="${f.key}" value="${esc(c)}" ${v === c ? "checked" : ""}>${esc(c)}</label>`).join("")}
      <label class="pill unknown"><input type="radio" name="${f.key}" value="" ${v === undefined ? "checked" : ""}>Don't know</label></div></fieldset>${help}</div>`;
  }
  let input;
  if (f.type === "choice") {
    input = `<select id="${id}" name="${f.key}" ${described}><option value="">Don't know / pick one</option>${
      f.choices.map(c => `<option ${v === c ? "selected" : ""}>${esc(c)}</option>`).join("")}</select>`;
  } else if (f.type === "overlay") {
    input = `<div class="row"><div class="with-unit"><input type="number" step="any" inputmode="decimal" id="${id}" name="${f.key}"
      value="${typeof v === "number" ? v : ""}" ${v === "none" ? "disabled" : ""} ${described}><span class="unit">${esc(f.unit)}</span></div>
      <label class="none-box"><input type="checkbox" data-none="${f.key}" ${v === "none" ? "checked" : ""}> None shown on the map</label></div>`;
  } else if (f.type === "number") {
    input = `<div class="with-unit"><input type="number" step="any" inputmode="decimal" id="${id}" name="${f.key}"
      value="${v ?? ""}" ${described}><span class="unit">${esc(f.unit)}</span></div>`;
  } else if (f.key === "description") {
    input = `<textarea id="${id}" name="${f.key}" ${described}>${esc(v || "")}</textarea>`;
  } else {
    input = `<input type="text" id="${id}" name="${f.key}" value="${esc(v || "")}" ${described}>`;
  }
  return `<div class="field${answered}" data-key="${f.key}"><label for="${id}">${glossify(esc(f.label))}</label>${input}${help}</div>`;
}

// Keep ANSWERS in step with the form
function wireForm() {
  const form = document.getElementById("form");
  const update = (e) => {
    const el = e.target;
    if (el.dataset.none) {
      const input = form.querySelector(`[name="${el.dataset.none}"]`);
      input.disabled = el.checked;
      if (el.checked) { ANSWERS[el.dataset.none] = "none"; input.value = ""; } else delete ANSWERS[el.dataset.none];
    } else if (el.name) {
      const f = field(el.name);
      let val = el.value;
      if (f && f.type === "yesno") val = val === "yes" ? true : val === "no" ? false : "";
      if (val === "" || val === null) delete ANSWERS[el.name]; else ANSWERS[el.name] = (f && (f.type === "number" || f.type === "overlay")) ? Number(val) : val;
      if (el.name === "project_type") document.getElementById("next").disabled = false;
    }
    save();
    const picked = el.closest(".pill, .choice");
    if (picked) animateIn(picked, "just-picked");
    const div = el.closest(".field");
    if (div) div.classList.toggle("answered", div.dataset.key in ANSWERS);
  };
  form.addEventListener("change", update);
  form.addEventListener("input", (e) => { if (e.target.matches("input[type=number], input[type=text], textarea")) update(e); });
}

// ---------------------------------------------------------------- address lookup
function wireLookup(onDone = () => showStep(2)) {
  const btn = document.getElementById("lookup");
  const input = document.getElementById("f_address");
  if (!btn) return;
  input.addEventListener("keydown", e => { if (e.key === "Enter") { e.preventDefault(); btn.click(); } });
  btn.addEventListener("click", async () => {
    const status = document.getElementById("lookup-status");
    const address = input.value.trim();
    if (!address) { status.textContent = "Type an address first."; input.focus(); return; }
    btn.disabled = true;
    status.textContent = "Looking up Toronto's zoning map…";
    try {
      const res = await api("/api/lookup", {address});
      for (const [k, v] of Object.entries(res.values || {})) {
        const f = field(k);
        ANSWERS[k] = f && f.type === "yesno" ? v === "yes" : v;
      }
      save();
      onDone();
      document.getElementById("lookup-status").innerHTML =
        `<b>${esc(res.summary)}</b><ul style="margin:6px 0 0;padding-left:20px">${(res.messages || []).map(m => `<li>${esc(m)}</li>`).join("")}</ul>`;
      document.getElementById("lookup-status").focus?.();
    } catch (e) {
      status.textContent = "Lookup didn't work: " + e.message + " You can still fill everything in by hand.";
      btn.disabled = false;
    }
  });
}

// ---------------------------------------------------------------- results
async function showResults() {
  app.innerHTML = `${stepper(5)}<div class="card"><h2>Checking…</h2><p class="muted">Running every rule for your project.</p></div>`;
  try {
    REPORT = await api("/api/check", {inputs: ANSWERS});
    try { localStorage.setItem("permitCheckerReport", JSON.stringify(REPORT)); } catch (e) {}
    drawResults();
    focusHeading();
  } catch (e) {
    app.innerHTML = `${stepper(5)}<div class="stop">${icon("FAIL")}Something went wrong: ${esc(e.message)}</div>`;
  }
}

function drawResults(onlyList = false) {
  GLOSS_USED = new Set();
  const r = REPORT, simple = isSimple();
  const c = r.counts;
  let html = stepper(5);

  if (r.stopped) {
    html += `<div class="card"><h2>${esc(t("stop"))}: check with Toronto Building first</h2>
      <div class="stop">${icon("FAIL")}${esc(r.results[0]?.message || r.overall)}</div></div>`;
    app.innerHTML = html + resultButtons();
    return;
  }

  const answer = r.permit?.answer || "";
  const verdictCls = answer === "Permit needed" ? "FLAG" : answer.startsWith("No") ? "PASS" : "NEED";
  html += `<div class="card">
    <h2>${esc(t("permit_q"))}</h2>
    <div class="verdict ${verdictCls}">${icon(verdictCls === "PASS" ? "PASS" : verdictCls === "FLAG" ? "FLAG" : "NEED MORE INFO")}
      <span class="big">${esc(answer)}</span><p>${esc(r.permit?.reason || "")}</p><p class="muted small">${esc(r.permit?.note || "")}</p></div>
  </div>`;

  // summary tiles: tap one to show only that kind
  const tiles = [["FAIL", "FAIL"], ["NEED MORE INFO", "NEED"], ["FLAG", "FLAG"], ["PASS", "PASS"]];
  html += `<div class="card">
    <h2>${esc(t("overall"))}</h2><p><b>${esc(r.overall)}</b></p>
    <div class="summary" role="group" aria-label="Filter results">${tiles.map(([s, k]) =>
      `<button type="button" class="tile ${k}" aria-pressed="${FILTER === s}" onclick="setFilter('${s}')">
        <b>${c[s] || 0}</b>${esc(t("tile_" + k))}<span class="more">${esc(t("tile_more_" + k))}</span></button>`).join("")}</div>
    ${nextUp(r)}
    ${FILTER ? `<button class="link" onclick="setFilter(null)">${esc(t("show_all"))}</button>` : ""}
    ${(r.notes || []).map(n => `<p class="muted small">• ${esc(n)}</p>`).join("")}
    ${isDesigner() ? exportBar() : ""}
    <div id="result-list">${isDesigner() && !FILTER ? designerTable(r) : resultList(r, simple)}</div>
  </div>`;
  html += warningsHtml(r);

  if (r.variance) html += `<div class="card"><h2>${esc(r.variance.title)}</h2><p>${esc(r.variance.intro)}</p>
    <ol>${r.variance.four_tests.map(x => `<li><b>${esc(x.test)}</b> ${esc(x.question)}</li>`).join("")}</ol>
    <h3>Steps</h3><ol>${r.variance.steps.map(s => `<li>${esc(s)}</li>`).join("")}</ol>
    <p class="muted small">${esc(r.variance.source)}</p></div>`;
  if (r.diagram && r.diagram.svg) html += `<div class="card diagram"><h2>Where you can build</h2>${r.diagram.svg}
    <p class="muted small">${esc(r.diagram.caption)}</p></div>`;
  else if (r.diagram) html += `<div class="card"><h2>Where you can build</h2><p class="muted">${esc(r.diagram.caption)}</p></div>`;
  if (r.costs) html += `<div class="card"><h2>Cost and timeline (rough estimate)</h2><table class="simple"><tbody>${
    r.costs.lines.map(l => `<tr><td>${esc(l.item)}</td><td><b>${esc(l.amount)}</b></td><td class="muted">${esc(l.note)}</td></tr>`).join("")
    }</tbody></table><p class="muted small">${esc(r.costs.disclaimer)}</p></div>`;
  if (r.roadmap) html += roadmapHtml(r.roadmap);
  if (isDesigner()) html += `<div class="card"><details><summary><h3 style="margin:0">Your answers (${Object.keys(r.inputs).length})</h3></summary>
    <table class="simple"><tbody>${Object.entries(r.inputs).map(([k, v]) => `<tr><td>${esc(field(k)?.label || k)}</td><td><code>${esc(k)}</code></td><td><b>${esc(fmtNum(v, field(k)?.unit || ""))}</b></td></tr>`).join("")}</tbody></table></details></div>`;
  html += `<div class="card feature spread"><div><h3 style="margin:0 0 4px">Not sure which design is best?</h3>
    <p class="muted small" style="margin:0">Compare two or three versions side by side: which passes, which needs a variance, and what each costs.</p></div>
    <button class="primary" onclick="go('#/compare')">Compare designs →</button></div>`;
  html += drawingsCard() + shadowCard(r) + (r.ai ? vibesCard(r) : "");
  if (r.tracker) html += `<div class="card"><h3>Rules version</h3><p class="small">${esc(r.tracker.summary)}</p>
    <details><summary class="small">Warnings (${r.tracker.warnings.length})</summary><ul class="small">${
      r.tracker.warnings.map(w => `<li>${esc(w)}</li>`).join("")}</ul></details></div>`;

  app.innerHTML = html + resultButtons();
  if (!onlyList) animateIn(app, "page-enter");
  animateIn(document.getElementById("result-list"), "list-enter");
  app.querySelectorAll("[data-answer]").forEach(b => b.addEventListener("click", () => goToField(b.dataset.answer)));
  wireChecklist();
  wireResultsAi();
  document.getElementById("exp-csv")?.addEventListener("click", exportCsv);
  document.getElementById("exp-json")?.addEventListener("click", () => download("permit-precheck.json", JSON.stringify(REPORT, null, 1), "application/json"));
  document.getElementById("exp-copy")?.addEventListener("click", copySummary);
}

function resultList(r, simple) {
  let html = "";
  for (const g of GROUP_ORDER) {
    let rs = r.results.filter(x => x.group === g);
    if (FILTER) rs = rs.filter(x => x.status === FILTER);
    if (!rs.length) continue;
    const order = {"FAIL": 0, "NEED MORE INFO": 1, "FLAG": 2};      // most important first
    const notPass = rs.filter(x => x.status !== "PASS").sort((a, b) => order[a.status] - order[b.status]);
    const pass = rs.filter(x => x.status === "PASS");
    html += `<h3 class="group-title">${esc(t(GROUP_KEY[g]))}</h3>`;
    html += notPass.map(x => resultCard(x, {simple, onAnswer: true})).join("");
    if (pass.length) {
      html += FILTER === "PASS" ? pass.map(x => resultCard(x, {simple})).join("")
        : `<details class="passed"><summary>✓ ${pass.length} ${esc(t("passed_n"))}</summary>${pass.map(x => resultCard(x, {simple})).join("")}</details>`;
    }
    if (g === "Building Code (safety)") html += `<p class="safety-note">Safety results never mean "safe" or "approved". <b>A qualified designer must confirm.</b></p>`;
  }
  return html || `<p class="muted">Nothing in this group.</p>`;
}

// "Answer 5 more questions to check 16 more rules": makes NEED MORE INFO feel finishable
function nextUp(r) {
  const needs = r.results.filter(x => x.status === "NEED MORE INFO");
  const keys = [...new Set(needs.map(x => (x.asks || [])[0]).filter(Boolean))];   // one question per rule
  if (!needs.length || !keys.length) return "";
  const q = keys.length === 1 ? "1 more question" : `${keys.length} more questions`;
  const rules = needs.length === 1 ? "1 more rule" : `${needs.length} more rules`;
  return `<div class="next-up"><span>Answer <b>${q}</b> to check <b>${rules}</b>.</span>
    <button type="button" class="primary" data-answer="${esc(keys[0])}">Answer the next one →</button></div>`;
}

function setFilter(s) { FILTER = FILTER === s ? null : s; drawResults(true); document.querySelector(".summary")?.scrollIntoView({block: "nearest"}); }

function resultButtons() {
  return `<div class="step-foot no-print">
    <button type="button" onclick="go('#/check/4')">${esc(t("change"))}</button>
    <div class="row">
      <button type="button" onclick="startOver()">${esc(t("start_over"))}</button>
      <button type="button" class="primary big" onclick="window.open('/report','_blank')">${esc(t("open_report"))}</button>
    </div></div>`;
}

// "Answer this question" on a NEED MORE INFO result: jump to that question and highlight it.
function goToField(key) {
  const step = stepOfField(key);
  go(`#/check/${step}`);
  setTimeout(() => {
    const div = app.querySelector(`.field[data-key="${key}"]`);
    if (!div) return;
    let d = div.closest("details");
    while (d) { d.open = true; d = d.parentElement.closest("details"); }
    div.scrollIntoView({block: "center"});
    div.classList.add("highlight");
    div.querySelector("input, select, textarea")?.focus({preventScroll: true});
  }, 50);
}

function startOver() {          // "Start over" now starts a NEW project; the old one stays in My projects
  if (!confirm("Start a new project? This one stays saved in My projects.")) return;
  newProject();
}

// ---------------------------------------------------------------- pictures
// A blueprint of a lot: dimension lines, setbacks, the buildable zone, and a scan line "checking" it.
// Drawn in code, so it stays sharp at any size. The scan stops if the computer is set to reduce motion.
function heroArt() {
  return `<svg viewBox="0 0 340 260" role="img" aria-label="Blueprint of a lot showing setbacks and the buildable area">
    <defs>
      <linearGradient id="scanGrad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#22d3ee" stop-opacity="0"/><stop offset=".85" stop-color="#22d3ee" stop-opacity=".22"/>
        <stop offset="1" stop-color="#67e8f9" stop-opacity=".9"/></linearGradient>
      <clipPath id="lotClip"><rect x="60" y="30" width="200" height="196"/></clipPath>
    </defs>
    <!-- lot -->
    <rect x="60" y="30" width="200" height="196" class="bp-line"/>
    <!-- setback lines -->
    <line x1="60" y1="70" x2="260" y2="70" class="bp-dash"/><line x1="60" y1="176" x2="260" y2="176" class="bp-dash"/>
    <line x1="78" y1="30" x2="78" y2="226" class="bp-dash"/><line x1="242" y1="30" x2="242" y2="226" class="bp-dash"/>
    <!-- buildable zone + house + suite -->
    <rect x="78" y="70" width="164" height="106" class="bp-zone"/>
    <rect x="96" y="104" width="96" height="66" rx="2" fill="rgba(226,232,240,.08)" stroke="#e2e8f0" stroke-width="1.2"/>
    <rect x="180" y="40" width="48" height="24" rx="2" fill="none" stroke="#a5b4fc" stroke-width="1" stroke-dasharray="3 2"/>
    <text x="144" y="141" class="bp-text" text-anchor="middle" fill="#e2e8f0">HOUSE</text>
    <text x="204" y="55" class="bp-text" text-anchor="middle">SUITE</text>
    <text x="160" y="90" class="bp-text hi" text-anchor="middle">BUILDABLE AREA</text>
    <!-- scan -->
    <g clip-path="url(#lotClip)"><rect x="60" y="0" width="200" height="30" class="bp-scan"/></g>
    <!-- dimensions -->
    <line x1="60" y1="242" x2="260" y2="242" class="bp-dim"/><line x1="60" y1="237" x2="60" y2="247" class="bp-dim"/><line x1="260" y1="237" x2="260" y2="247" class="bp-dim"/>
    <text x="160" y="256" class="bp-text hi" text-anchor="middle">FRONTAGE 10.0 m</text>
    <line x1="40" y1="30" x2="40" y2="226" class="bp-dim"/><line x1="35" y1="30" x2="45" y2="30" class="bp-dim"/><line x1="35" y1="226" x2="45" y2="226" class="bp-dim"/>
    <text x="30" y="128" class="bp-text hi" text-anchor="middle" transform="rotate(-90 30 128)">DEPTH 36.0 m</text>
    <text x="266" y="52" class="bp-text">REAR 9.0</text><text x="266" y="200" class="bp-text">FRONT 6.0</text>
    <text x="266" y="128" class="bp-text">SIDE 0.9</text>
    <!-- street -->
    <line x1="20" y1="232" x2="320" y2="232" stroke="rgba(148,163,184,.35)" stroke-width="1"/>
    <!-- result badge -->
    <g class="bp-ok"><rect x="196" y="150" width="86" height="22" rx="6" fill="#052e24" stroke="#34d399"/>
      <text x="239" y="165" text-anchor="middle" style="font:600 9.5px var(--mono);fill:#34d399;letter-spacing:.06em">✓ RD-18 PASS</text></g>
  </svg>`;
}

// ---------------------------------------------------------------- language and settings
function translatePage() {
  document.documentElement.lang = LANG === "zh-Hans" ? "zh-Hans" : LANG;
  document.querySelectorAll("[data-t]").forEach(el => { el.textContent = t(el.dataset.t); });
}

async function start() {
  try { SETUP = await api("/api/setup"); } catch (e) { app.innerHTML = `<div class="stop">${icon("FAIL")}${esc(e.message)}</div>`; return; }
  TRANSLATIONS = SETUP.translations || {};
  ANSWERS = load();
  projectChanged();                       // answers saved before "My projects" existed become a project

  const lang = document.getElementById("lang");
  for (const [code, tr] of Object.entries(TRANSLATIONS)) {
    if (code !== "en" && !code.startsWith("_")) lang.insertAdjacentHTML("beforeend", `<option value="${esc(code)}">${esc(tr.name)}</option>`);
  }
  LANG = getPref("permitLang") || "en";
  lang.value = LANG;
  lang.addEventListener("change", () => { LANG = lang.value; setPref("permitLang", LANG); translatePage(); route(); });

  const simple = document.getElementById("simple");
  simple.checked = getPref("permitSimple") === "1";
  document.documentElement.classList.toggle("simple-mode", simple.checked);
  simple.addEventListener("change", () => {
    setPref("permitSimple", simple.checked ? "1" : "0");
    document.documentElement.classList.toggle("simple-mode", simple.checked);
    if (REPORT && location.hash.startsWith("#/check/5")) drawResults(true); else route();   // redraw this page in the new wording
  });

  // Colours: Auto (follow the computer), Light or Dark
  const theme = getPref("permitTheme") || "dark";          // dark is the default look
  document.querySelectorAll('input[name="theme"]').forEach(r => {
    r.checked = r.value === theme;
    r.addEventListener("change", () => {
      setPref("permitTheme", r.value);
      if (r.value === "auto") delete document.documentElement.dataset.theme;
      else document.documentElement.dataset.theme = r.value;
    });
  });

  const big = document.getElementById("bigtext");
  big.checked = getPref("permitBig") === "1";
  document.documentElement.classList.toggle("big-text", big.checked);
  big.addEventListener("change", () => { setPref("permitBig", big.checked ? "1" : "0"); document.documentElement.classList.toggle("big-text", big.checked); });

  const menu = document.getElementById("settings-menu");
  document.addEventListener("click", e => { if (menu.open && !menu.contains(e.target)) menu.open = false; });
  document.addEventListener("keydown", e => { if (e.key === "Escape" && menu.open) { menu.open = false; menu.querySelector("summary").focus(); } });

  // Mode: Homeowner (plain words, essentials) or Designer (every number, all sections open, exports)
  const mode = getPref("permitMode") || "homeowner";
  document.documentElement.classList.toggle("mode-designer", mode === "designer");
  document.querySelectorAll('input[name="mode"]').forEach(r => {
    r.checked = r.value === mode;
    r.addEventListener("change", () => {
      setPref("permitMode", r.value);
      document.documentElement.classList.toggle("mode-designer", r.value === "designer");
      const simpleBox = document.getElementById("simple");
      simpleBox.checked = r.value === "homeowner";          // homeowners get plain words; designers get the full wording
      setPref("permitSimple", simpleBox.checked ? "1" : "0");
      if (REPORT && location.hash.startsWith("#/check/5")) drawResults(true); else route();
    });
  });
  if (getPref("permitSimple") === null && mode === "homeowner") { simple.checked = true; }

  api("/api/ai-status").then(st => { AI_STATUS = st; refreshAiBox(); }).catch(() => {});
  buildTerms();
  wireTerms();
  translatePage();
  window.addEventListener("hashchange", route);
  route();
  if (!guideSeen()) openGuide();          // the how-to guide pops up the first time
}

start();


// ================================================================ the permit roadmap (on the results page)
// Checklist ticks are saved on this computer, so you can work through it over several days.
const CHECK_KEY = "permitChecklist";
function ticks() { try { return JSON.parse(localStorage.getItem(CHECK_KEY)) || {}; } catch (e) { return {}; } }

function roadmapHtml(rm) {
  const done = ticks();
  const box = (group, item, detail) => {
    const id = `${group}:${item}`;
    return `<li><label class="tick"><input type="checkbox" data-tick="${esc(id)}" ${done[id] ? "checked" : ""}>
      <span><b>${esc(item)}</b>${detail ? `<span class="muted small">${esc(detail)}</span>` : ""}</span></label></li>`;
  };
  const c = rm.checklist;
  const total = c.drawings.length + c.forms.length;
  const ticked = [...c.drawings.map(d => "drawing:" + d.item), ...c.forms.map(f => "form:" + f.item)].filter(id => done[id]).length;
  return `<div class="card roadmap" id="roadmap">
    <h2>Your permit roadmap</h2>
    <p class="muted small" style="margin-top:0">What happens after this check: what to send in, the inspections, and the steps from idea to closed permit.</p>

    <h3 class="group-title">1. Timeline</h3>
    <ol class="timeline">${rm.timeline.map((st, i) => `<li class="${i === 0 ? "now" : ""}">
      <span class="dot" aria-hidden="true">${i + 1}</span>
      <div><b>${esc(st.title)}</b>${st.time ? ` <span class="chip time">${esc(st.time)}</span>` : ""}<p class="muted small">${esc(st.detail)}</p></div></li>`).join("")}</ol>

    <h3 class="group-title">2. What to send in ${total ? `<span class="muted small" id="tick-count">${ticked} of ${total} ready</span>` : ""}</h3>
    ${c.none ? `<p>${esc(c.none)}</p>` : `
      <details class="more"><summary>Rules for every drawing (${c.general.length})</summary><ul class="small">${c.general.map(g => `<li>${esc(g)}</li>`).join("")}</ul></details>
      <p class="label-sm">Drawings</p><ul class="ticks">${c.drawings.map(d => box("drawing", d.item, d.detail)).join("")}</ul>
      <p class="label-sm">Forms</p><ul class="ticks">${c.forms.map(f => box("form", f.item, f.detail)).join("")}</ul>`}

    ${rm.inspections.length ? `<h3 class="group-title">3. Inspections the City will do</h3>
      <ol class="inspections">${rm.inspections.map(x => `<li><b>${esc(x.item)}</b><span class="muted small">Call when: ${esc(x.call)}</span></li>`).join("")}</ol>
      <ul class="small muted">${rm.inspection_notes.map(n => `<li>${esc(n)}</li>`).join("")}</ul>` : ""}

    <p class="muted small">Sources: ${rm.sources.map(s => `<a href="${esc(s.link)}" target="_blank" rel="noopener">${esc(s.name)}</a>`).join(" · ")}.
      Check the City's pages before you apply: requirements change.</p>
  </div>`;
}

function wireChecklist() {
  app.querySelectorAll("[data-tick]").forEach(cb => cb.addEventListener("change", () => {
    const t = ticks(); if (cb.checked) t[cb.dataset.tick] = 1; else delete t[cb.dataset.tick];
    try { localStorage.setItem(CHECK_KEY, JSON.stringify(t)); } catch (e) {}
    window.projectChanged?.();
    const all = app.querySelectorAll("[data-tick]"), n = [...all].filter(x => x.checked).length;
    const count = document.getElementById("tick-count"); if (count) count.textContent = `${n} of ${all.length} ready`;
  }));
}

// ================================================================ "What can I build?"
// You give the lot; the rules run backwards to show the biggest design allowed. Uses the same answers as the checker.
const BUILD_FIELDS = ["zone", "zone_label", "grey_property", "ht", "st", "coverage_overlay",
                      "lot_frontage", "lot_depth", "lot_area", "lane_frontage", "rear_setback", "house_gfa"];
const BUILD_LABELS = {rear_setback: "Space behind your house now (back wall to back lot line)", house_gfa: "Floor area of your house now",
                      lane_frontage: "If there's a lane: length of lot touching it"};
let BUILD = null;

function showBuild() {
  const fields = BUILD_FIELDS.map(k => {
    const f = field(k); if (!f) return "";
    return fieldHtml(BUILD_LABELS[k] ? Object.assign({}, f, {label: BUILD_LABELS[k], simple: ""}) : f);
  });
  app.innerHTML = `
    <div class="card step-head"><p class="eyebrow">What can I build?</p><h2>The biggest design your lot allows</h2>
      <p class="muted">Enter your lot. We run Toronto's rules backwards and show the largest addition, garden suite, laneway suite
        or multiplex allowed. Then we check each one with the normal checker to make sure it really passes.</p></div>
    <form id="form" onsubmit="return false" novalidate>
      <section class="card form-section"><h3>Your lot</h3>
        ${lookupBox()}
        ${fields.join("")}
      </section>
    </form>
    <div class="step-foot no-print"><span class="muted small">Your answers are shared with "Check a project".</span>
      <button type="button" class="primary big" id="calc">Show what I can build</button></div>
    <div id="build-out" aria-live="polite">${BUILD ? buildHtml(BUILD) : ""}</div>`;
  wireForm();
  wireLookup(() => { showBuild(); });
  document.getElementById("calc").addEventListener("click", calcBuild);
  wireBuildButtons();
  animateIn(app, "page-enter");
  focusHeading();
}

async function calcBuild() {
  const out = document.getElementById("build-out");
  out.innerHTML = `<div class="card"><p class="muted">Working it out…</p></div>`;
  try {
    BUILD = await api("/api/whatcan", {inputs: ANSWERS});
    out.innerHTML = buildHtml(BUILD);
    wireBuildButtons();
    animateIn(out, "list-enter");
    out.scrollIntoView({block: "start", behavior: "smooth"});
  } catch (e) { out.innerHTML = `<div class="stop">${icon("FAIL")}${esc(e.message)}</div>`; }
}

function buildHtml(b) {
  if (b.stop) return `<div class="stop">${icon("FAIL")}${esc(b.stop)}</div>`;
  if (b.needed && b.needed.length) return `<div class="card next-up"><span>To work it out we still need: <b>${esc(b.needed.join(", "))}</b>.</span></div>`;
  return `<h2 class="group-title" style="font-size:1.3rem">What your lot allows</h2>
    ${(b.notes || []).filter(Boolean).map(n => `<p class="muted small">• ${esc(n)}</p>`).join("")}
    <div class="options">${b.options.map((o, i) => `<article class="card option">
      <div class="spread"><h3 style="margin:0">${esc(o.title)}</h3>${o.check ? (o.check.passed
        ? `<span class="chip PASS">✓ Passes the checker</span>` : `<span class="chip FAIL">Check found ${o.check.fails.length} issue(s)</span>`) : ""}</div>
      <p class="option-headline">${esc(o.headline)}</p>
      <dl class="facts">${(o.facts || []).map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("")}</dl>
      ${o.check && !o.check.passed ? `<ul class="small">${o.check.fails.map(f => `<li>${esc(f)}</li>`).join("")}</ul>` : ""}
      <p class="muted small">Rules used: ${esc((o.rules || []).join(", "))}</p>
      ${o.design ? `<div class="row"><button type="button" class="primary" data-use="${i}">Check this design →</button>
        <button type="button" data-tweak="${i}">Start from it and adjust</button></div>` : ""}
    </article>`).join("")}</div>
    <p class="muted small">These are the limits from the rules we have. Real lots have odd shapes, site-specific exceptions and other
      details this tool doesn't read, so treat this as a starting point for your designer. A draft pre-check, not an approval.</p>`;
}

function wireBuildButtons() {
  const use = (i, step) => { Object.assign(ANSWERS, BUILD.options[i].design); save(); go(`#/check/${step}`); };
  app.querySelectorAll("[data-use]").forEach(b => b.addEventListener("click", () => use(+b.dataset.use, 5)));
  app.querySelectorAll("[data-tweak]").forEach(b => b.addEventListener("click", () => use(+b.dataset.tweak, 4)));
}

// ================================================================ what-if comparison
// Two or three versions of your design side by side. Each one goes through the normal checker.
let COMPARE = null;   // {keys, designs: [{name, inputs}], result}

function compareKeys() {
  const p = profile();
  const main = p ? sectionsForStep(4).find(sec => !OPTIONAL_SECTIONS.includes(sec)) : null;
  const keys = (main && CORE[main]) ? CORE[main] : (main ? SETUP.fields.filter(f => f.section === main).slice(0, 8).map(f => f.key) : []);
  return [...keys.filter(k => field(k) && ["number", "choice", "yesno"].includes(field(k).type)), "work_area"];
}

function showCompare() {
  if (!ANSWERS.project_type) {
    app.innerHTML = `<div class="card"><h2>Compare designs</h2><p>Start a check first, so we know what you're building.</p>
      <button class="primary" onclick="go('#/check/1')">Start a check</button></div>`;
    focusHeading(); return;
  }
  if (!COMPARE || COMPARE.type !== ANSWERS.project_type) {
    const base = JSON.parse(JSON.stringify(ANSWERS));
    COMPARE = {type: ANSWERS.project_type, keys: compareKeys(), result: null,
               designs: [{name: "Design A (yours)", inputs: base}, {name: "Design B", inputs: JSON.parse(JSON.stringify(base))}]};
  }
  drawCompare();
}

function compareInput(k, d, di) {
  const f = field(k), v = d.inputs[k];
  const label = isSimple() && f.simple ? f.simple : f.label;
  if (f.type === "number") return `<input type="number" step="any" inputmode="decimal" aria-label="${esc(label)}, ${esc(d.name)}"
    data-c="${di}" data-k="${k}" value="${v ?? ""}">`;
  const opts = f.type === "yesno" ? [["", "Don't know"], ["yes", "Yes"], ["no", "No"]] : [["", "Don't know"], ...f.choices.map(c => [c, c])];
  const cur = f.type === "yesno" ? (v === true ? "yes" : v === false ? "no" : "") : (v ?? "");
  return `<select aria-label="${esc(label)}, ${esc(d.name)}" data-c="${di}" data-k="${k}">${opts.map(([val, txt]) =>
    `<option value="${esc(val)}" ${String(cur) === val ? "selected" : ""}>${esc(txt)}</option>`).join("")}</select>`;
}

function drawCompare() {
  const C = COMPARE, n = C.designs.length;
  const res = C.result;
  const head = C.designs.map((d, i) => `<th><input type="text" class="cname" data-name="${i}" value="${esc(d.name)}" aria-label="Name of design ${i + 1}">
      ${n > 2 && i > 0 ? `<button type="button" class="link small" data-remove="${i}">Remove</button>` : ""}</th>`).join("");
  const rows = C.keys.map(k => `<tr><th scope="row">${esc(isSimple() && field(k).simple ? field(k).simple : field(k).label)}
      ${field(k).unit ? `<span class="muted small">(${esc(field(k).unit)})</span>` : ""}</th>
      ${C.designs.map((d, i) => `<td>${compareInput(k, d, i)}</td>`).join("")}</tr>`).join("");
  const out = !res ? "" : `<table class="compare result"><thead><tr><th></th>${res.designs.map((d, i) =>
      `<th>${esc(d.name)}${res.best === i ? ` <span class="chip PASS">Best fit</span>` : ""}</th>`).join("")}</tr></thead><tbody>
    <tr><th scope="row">Building permit</th>${res.designs.map(d => `<td>${esc(d.stopped ? "Stopped: contact Toronto Building" : d.permit)}</td>`).join("")}</tr>
    <tr><th scope="row">Rules that don't pass</th>${res.designs.map(d => `<td>${d.fails.length
      ? `<span class="chip FAIL">${d.fails.length}</span><ul class="small">${d.fails.map(f => `<li><b>${esc(f.rule_id)}</b> ${esc(f.message)}</li>`).join("")}</ul>`
      : `<span class="chip PASS">None</span>`}</td>`).join("")}</tr>
    <tr><th scope="row">Minor variance needed?</th>${res.designs.map(d => `<td>${d.needs_variance ? "<b>Yes</b> (Committee of Adjustment)" : "No"}</td>`).join("")}</tr>
    <tr><th scope="row">Building Code issues</th>${res.designs.map(d => `<td>${d.safety_fails ? `${d.safety_fails} (a designer must confirm)` : "None found"}</td>`).join("")}</tr>
    <tr><th scope="row">Questions still open</th>${res.designs.map(d => `<td>${d.need_info}</td>`).join("")}</tr>
    <tr><th scope="row">Permit fees (rough)</th>${res.designs.map(d => `<td>${d.fee !== null ? `<b>$${d.fee.toLocaleString("en-CA", {minimumFractionDigits: 2})}</b>` : `<span class="muted small">${esc(d.fee_note)}</span>`}</td>`).join("")}</tr>
    <tr><th scope="row">City review</th>${res.designs.map(d => `<td>${esc(d.review || "—")}</td>`).join("")}</tr>
    <tr><th scope="row"></th>${res.designs.map((d, i) => `<td><button type="button" data-pick="${i}">Use ${esc(d.name)}</button></td>`).join("")}</tr>
  </tbody></table>
  <p class="muted small">"Best fit" = fewest rules that don't pass, then fewest open questions, then the lowest fee. Fees are a rough estimate.</p>`;

  app.innerHTML = `
    <div class="card step-head"><p class="eyebrow">What-if comparison</p><h2>Compare designs</h2>
      <p class="muted">Change a few numbers in each column (for example one storey vs two). Everything else stays the same as your answers.
        Each design goes through the full checker.</p></div>
    <div class="card"><div class="table-scroll"><table class="compare"><thead><tr><th>${esc(C.type)}</th>${head}</tr></thead><tbody>${rows}</tbody></table></div>
      <div class="row" style="margin-top:12px">
        ${n < 3 ? `<button type="button" id="add-design">+ Add a third design</button>` : ""}
        <button type="button" class="primary big" id="run-compare">Compare</button></div></div>
    <div id="compare-out" class="card" ${res ? "" : "hidden"}><div class="table-scroll">${out}</div></div>
    <div class="step-foot no-print"><button type="button" onclick="go('#/check/5')">← Back to results</button><span></span></div>`;

  app.querySelectorAll("[data-c]").forEach(el => el.addEventListener("change", () => {
    const d = C.designs[+el.dataset.c], f = field(el.dataset.k);
    let v = el.value;
    if (v === "") delete d.inputs[el.dataset.k];
    else d.inputs[el.dataset.k] = f.type === "number" ? Number(v) : f.type === "yesno" ? v === "yes" : v;
  }));
  app.querySelectorAll("[data-name]").forEach(el => el.addEventListener("input", () => { C.designs[+el.dataset.name].name = el.value; }));
  app.querySelectorAll("[data-remove]").forEach(b => b.addEventListener("click", () => { C.designs.splice(+b.dataset.remove, 1); C.result = null; drawCompare(); }));
  document.getElementById("add-design")?.addEventListener("click", () => {
    C.designs.push({name: `Design ${String.fromCharCode(65 + C.designs.length)}`, inputs: JSON.parse(JSON.stringify(C.designs[C.designs.length - 1].inputs))});
    C.result = null; drawCompare();
  });
  document.getElementById("run-compare").addEventListener("click", async () => {
    try {
      C.result = await api("/api/compare", {designs: C.designs});
      drawCompare();
      const o = document.getElementById("compare-out"); animateIn(o, "list-enter"); o.scrollIntoView({block: "start", behavior: "smooth"});
    } catch (e) { alert(e.message); }
  });
  app.querySelectorAll("[data-pick]").forEach(b => b.addEventListener("click", () => {
    ANSWERS = JSON.parse(JSON.stringify(C.designs[+b.dataset.pick].inputs)); save(); go("#/check/5");
  }));
  animateIn(app, "page-enter");
}


// ================================================================ common rejection warnings (results page)
function warningsHtml(r) {
  const w = r.warnings || [], wait = r.wait;
  if (!w.length && !wait) return "";
  const top = isDesigner() ? w : w.slice(0, 5);
  return `<div class="card warnings">
    <h2>Avoid getting sent back</h2>
    ${wait ? `<div class="wait"><b class="wait-num">${wait.median_days}</b><span><b>days</b> is the typical wait for a ${esc(wait.name.toLowerCase())}
        permit in Toronto, from application to permit issued (${wait.permits.toLocaleString("en-CA")} permits since 2017).
        Half took between ${wait.p25_days} and ${wait.p75_days} days; only ${wait.within_14_days_pct}% were issued within two weeks.
        <a href="#/stats">See all Toronto stats</a></span></div>` : ""}
    ${top.length ? `<p class="muted small" style="margin:10px 0 4px">Applications like yours often get sent back for these reasons:</p>
    <ol class="warn-list">${top.map(x => `<li><b>${esc(x.title)}</b><span>${glossify(esc(x.why))}</span>
      <span class="warn-fix"><b>Do this:</b> ${esc(x.fix)}</span>
      <span class="muted small">${x.source_link ? `Source: <a href="${esc(x.source_link)}" target="_blank" rel="noopener">${esc(x.source_name)}</a>` : esc(x.source_name)}</span></li>`).join("")}</ol>
    ${w.length > top.length ? `<p class="muted small">${w.length - top.length} more in Designer mode (Settings).</p>` : ""}` : ""}
  </div>`;
}

// ================================================================ Designer mode: compact table and exports
function designerTable(r) {
  const order = {"FAIL": 0, "NEED MORE INFO": 1, "FLAG": 2, "PASS": 3};
  const rows = [...r.results].sort((a, b) => order[a.status] - order[b.status]);
  return `<div class="table-scroll">${resultsTable(rows)}</div>`;
}

function exportBar() {
  return `<div class="export-bar no-print"><span class="muted small">Export:</span>
    <button type="button" id="exp-csv">Results (CSV)</button>
    <button type="button" id="exp-json">Full data (JSON)</button>
    <button type="button" id="exp-copy">Copy summary</button>
    <button type="button" onclick="window.open('/report','_blank')">Printable report</button></div>`;
}

function download(name, text, type) {
  const a = Object.assign(document.createElement("a"), {href: URL.createObjectURL(new Blob([text], {type})), download: name});
  a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

function exportCsv() {
  const cols = ["rule_id", "status", "group", "title", "limit", "value", "unit", "section", "confidence", "message", "fix"];
  const cell = v => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const lines = [cols.join(","), ...REPORT.results.map(r => cols.map(c => cell(r[c])).join(","))];
  download("permit-precheck-results.csv", lines.join("\n"), "text/csv");
}

async function copySummary() {
  const r = REPORT;
  const fails = r.results.filter(x => x.status === "FAIL").map(x => `- ${x.rule_id} (${x.section}): ${x.message}`);
  const text = [`Permit pre-check (draft, not an approval): ${r.project_type}`, `Permit: ${r.permit?.answer || ""}`, r.overall,
                fails.length ? "Rules that don't pass:\n" + fails.join("\n") : "", `Counts: ${JSON.stringify(r.counts)}`].filter(Boolean).join("\n");
  try { await navigator.clipboard.writeText(text); document.getElementById("exp-copy").textContent = "Copied ✓"; }
  catch (e) { download("permit-precheck-summary.txt", text, "text/plain"); }
}

// ================================================================ by-law dictionary: hover (or tap) a dotted word
let TERM_RE = null, TERM_RE_CAPS = null, TERM_MAP = new Map();
let GLOSS_USED = new Set();      // each dictionary word is underlined once per page, so pages don't fill up with dots
const escRe = (w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

function buildTerms() {
  const terms = (SETUP.glossary && SETUP.glossary.terms) || [];
  const words = [], caps = [];
  terms.forEach((t, i) => t.words.forEach(w => {
    (w.length <= 3 && w === w.toUpperCase() ? caps : words).push(w);      // HT, ST, FSI only match in capitals
    TERM_MAP.set(w.toLowerCase(), i);
  }));
  words.sort((a, b) => b.length - a.length);
  if (words.length) TERM_RE = new RegExp(`\\b(${words.map(escRe).join("|")})\\b`, "gi");
  if (caps.length) TERM_RE_CAPS = new RegExp(`\\b(${caps.map(escRe).join("|")})\\b`, "g");
}

// Wrap the first mention of each dictionary word in a text (already HTML-escaped). English only.
function glossify(html) {
  if (!TERM_RE || LANG !== "en" || !html) return html;
  const used = GLOSS_USED;
  const wrap = (m) => {
    const i = TERM_MAP.get(m.toLowerCase());
    if (i === undefined || used.has(i)) return m;
    used.add(i);
    return `<span class="term" tabindex="0" role="button" data-term="${i}">${m}</span>`;
  };
  // don't touch text inside tags that were already added
  return html.split(/(<[^>]+>)/).map(part => part.startsWith("<") ? part
    : part.replace(TERM_RE, wrap).replace(TERM_RE_CAPS || /$^/, wrap)).join("");
}

function showTerm(el) {
  const t = SETUP.glossary.terms[+el.dataset.term], tip = document.getElementById("term-tip");
  if (!t) return;
  tip.innerHTML = `<b>${esc(t.term)}</b><p>${esc(t.plain)}</p>
    ${t.official && isDesigner() ? `<p class="official">“${esc(t.official.length > 320 ? t.official.slice(0, 320) + "…" : t.official)}”</p>` : ""}
    <span class="muted small">${esc(t.source)} · <a href="#/dictionary">All terms</a></span>`;
  tip.hidden = false;
  const r = el.getBoundingClientRect(), w = Math.min(320, innerWidth - 24);
  tip.style.width = w + "px";
  tip.style.left = Math.max(12, Math.min(r.left, innerWidth - w - 12)) + "px";
  const below = r.bottom + 8, h = tip.offsetHeight;
  tip.style.top = (below + h > innerHeight - 8 ? Math.max(8, r.top - h - 8) : below) + "px";
  el.setAttribute("aria-describedby", "term-tip");
}
function hideTerm() { const tip = document.getElementById("term-tip"); if (tip) tip.hidden = true; }

function wireTerms() {
  let pinned = null;
  document.addEventListener("mouseover", e => { const el = e.target.closest(".term"); if (el) showTerm(el); });
  document.addEventListener("mouseout", e => { if (e.target.closest(".term") && !pinned && !e.relatedTarget?.closest?.("#term-tip")) hideTerm(); });
  document.addEventListener("focusin", e => { const el = e.target.closest(".term"); if (el) showTerm(el); });
  document.addEventListener("focusout", e => { if (e.target.closest(".term")) { pinned = null; hideTerm(); } });
  document.addEventListener("click", e => {
    const el = e.target.closest(".term");
    if (el) { e.preventDefault(); e.stopPropagation(); pinned = pinned === el ? null : el; pinned ? showTerm(el) : hideTerm(); return; }
    if (!e.target.closest("#term-tip")) { pinned = null; hideTerm(); }
  }, true);
  document.addEventListener("keydown", e => {
    if (e.key === "Escape") { pinned = null; hideTerm(); }
    if ((e.key === "Enter" || e.key === " ") && e.target.closest?.(".term")) { e.preventDefault(); showTerm(e.target.closest(".term")); }
  });
  addEventListener("scroll", () => { if (!pinned) hideTerm(); }, {passive: true});
}

function showDictionary() {
  const terms = (SETUP.glossary?.terms || []).slice().sort((a, b) => a.term.localeCompare(b.term));
  app.innerHTML = `<div class="card step-head"><p class="eyebrow">By-law dictionary</p><h2>Zoning words, in plain language</h2>
      <p class="muted">Definitions from Chapter 800 of Toronto's Zoning By-law 569-2013, each explained in everyday words.
        Throughout the tool, words with a dotted underline show these definitions when you hover over or tap them.</p>
      <label class="sr-only" for="dict-search">Search terms</label>
      <input type="text" id="dict-search" placeholder="Search, e.g. setback" autocomplete="off"></div>
    <div class="card"><dl class="dict" id="dict">${terms.map(t => `<div class="dict-item" data-search="${esc((t.term + " " + t.words.join(" ") + " " + t.plain).toLowerCase())}">
      <dt>${esc(t.term)}</dt><dd><p>${esc(t.plain)}</p>
      ${t.official ? `<details><summary>Official definition</summary><p class="official">${esc(t.official)}</p></details>` : ""}
      <span class="muted small">${esc(t.source)}</span></dd></div>`).join("")}</dl></div>
    <p class="muted small">Source: <a href="${esc(SETUP.glossary?.source || "")}" target="_blank" rel="noopener">Zoning By-law 569-2013, Chapter 800</a>
      (read ${esc(SETUP.glossary?.built_on || "")}). The plain-language versions are simplified: the official wording is what counts.</p>`;
  document.getElementById("dict-search").addEventListener("input", e => {
    const q = e.target.value.trim().toLowerCase();
    app.querySelectorAll(".dict-item").forEach(d => { d.hidden = q && !d.dataset.search.includes(q); });
  });
  animateIn(app, "page-enter");
  focusHeading();
}

// ================================================================ Toronto permit stats dashboard
let STATS_PICK = null;
function showStats() {
  const S = SETUP.stats;
  if (!S) { app.innerHTML = `<div class="card"><h2>Toronto permit stats</h2><p>No stats yet. Run <code>python3 tools/build_stats.py</code>.</p></div>`; return; }
  const groups = S.groups.slice().sort((a, b) => b.median_days - a.median_days);
  STATS_PICK = STATS_PICK || groups[0].project_key + "|" + groups[0].name;
  const slowest = groups[0], o = S.overall;
  app.innerHTML = `
    <div class="card step-head"><p class="eyebrow">Toronto permit stats</p><h2>How long do permits really take?</h2>
      <p class="muted">From the City of Toronto's own open data: ${o.permits.toLocaleString("en-CA")} low-rise residential permits issued since 2017.
        The law gives the City 10 business days to review a complete house application. Most take much longer from start to finish,
        often because the application wasn't complete or the design didn't meet zoning.</p></div>
    <div class="summary stat-tiles">
      <div class="tile"><b>${o.median_days}</b>days<span class="more">typical wait, all low-rise types</span></div>
      <div class="tile"><b>${o.within_14_days_pct}%</b>issued in 2 weeks<span class="more">about the 10-business-day target</span></div>
      <div class="tile"><b>${slowest.median_days}</b>days<span class="more">typical wait for a ${esc(slowest.name.toLowerCase())}</span></div>
      <div class="tile"><b>${slowest.over_90_days_pct}%</b>over 90 days<span class="more">${esc(slowest.name.toLowerCase())} permits</span></div>
    </div>
    <div class="card">
      <div class="spread"><h3 style="margin:0">Typical days from application to permit, by project</h3>
        <button type="button" class="link" id="stats-table-toggle">Show as a table</button></div>
      <p class="muted small" style="margin:4px 0 10px">Bar = median (half took less, half took more). Thin line = the middle half of permits (25th to 75th percentile).</p>
      <div id="stats-chart" class="chart">${statsBars(groups)}</div>
      <div id="stats-table" hidden>${statsTable(groups)}</div>
    </div>
    <div class="card">
      <div class="spread"><h3 style="margin:0">Is it getting faster? Median days by year</h3>
        <label class="small">Project <select id="stats-pick">${groups.map(g => `<option value="${esc(g.project_key + "|" + g.name)}" ${STATS_PICK === g.project_key + "|" + g.name ? "selected" : ""}>${esc(g.name)}</option>`).join("")}</select></label></div>
      <div id="stats-trend" class="chart">${statsTrend(groups.find(g => g.project_key + "|" + g.name === STATS_PICK))}</div>
    </div>
    <p class="muted small">Source: <a href="${esc(S.link)}" target="_blank" rel="noopener">${esc(S.source)}</a>, data up to ${esc(S.data_up_to || "")}.
      ${esc(S.measure)} Built with <code>tools/build_stats.py</code> on ${esc(S.built_on)}.</p>`;
  document.getElementById("stats-table-toggle").addEventListener("click", e => {
    const t = document.getElementById("stats-table"), c = document.getElementById("stats-chart");
    t.hidden = !t.hidden; c.hidden = !t.hidden; e.target.textContent = t.hidden ? "Show as a table" : "Show as a chart";
  });
  document.getElementById("stats-pick").addEventListener("change", e => {
    STATS_PICK = e.target.value;
    document.getElementById("stats-trend").innerHTML = statsTrend(groups.find(g => g.project_key + "|" + g.name === STATS_PICK));
    wireChartTips();
  });
  wireChartTips();
  animateIn(app, "page-enter");
  focusHeading();
}

// Horizontal bars: one series, one colour (accent), range as a thin muted line, a labelled 14-day reference line.
function statsBars(groups) {
  const W = 720, labelW = 210, right = 40, rowH = 34, top = 26;
  const max = Math.ceil(Math.max(...groups.map(g => g.p75_days)) / 30) * 30;
  const x = d => labelW + (W - labelW - right) * d / max;
  const H = top + groups.length * rowH + 28;
  const ticks = []; for (let d = 0; d <= max; d += 30) ticks.push(d);
  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Bar chart of typical days to permit by project type. Table view available.">
    <defs><linearGradient id="barGrad" x1="0" x2="1"><stop offset="0" stop-color="var(--accent)" stop-opacity=".75"/><stop offset="1" stop-color="var(--accent)"/></linearGradient></defs>
    ${ticks.map(d => `<line x1="${x(d)}" x2="${x(d)}" y1="${top - 6}" y2="${H - 26}" class="grid"/>
      <text x="${x(d)}" y="${H - 10}" class="axis" text-anchor="middle">${d}</text>`).join("")}
    <text x="${W - right}" y="${H - 10}" class="axis" text-anchor="end" dx="34">days</text>
    ${groups.map((g, i) => {
      const y = top + i * rowH, cy = y + rowH / 2;
      return `<g class="bar-row" tabindex="0" data-tip="${esc(`${g.name}: typical ${g.median_days} days · middle half ${g.p25_days}–${g.p75_days} days · ${g.permits.toLocaleString("en-CA")} permits · ${g.within_14_days_pct}% within 2 weeks · ${g.over_90_days_pct}% over 90 days`)}">
        <rect x="0" y="${y}" width="${W}" height="${rowH}" class="hit"/>
        <text x="${labelW - 10}" y="${cy + 4}" class="label" text-anchor="end">${esc(g.name)}</text>
        <path d="M${x(0)} ${cy - 9} H${x(g.median_days) - 4} a4 4 0 0 1 4 4 v10 a4 4 0 0 1 -4 4 H${x(0)} Z" class="bar"/>
        <line x1="${x(g.p25_days)}" x2="${x(g.p75_days)}" y1="${cy}" y2="${cy}" class="range"/>
        <line x1="${x(g.p25_days)}" x2="${x(g.p25_days)}" y1="${cy - 5}" y2="${cy + 5}" class="range"/>
        <line x1="${x(g.p75_days)}" x2="${x(g.p75_days)}" y1="${cy - 5}" y2="${cy + 5}" class="range"/>
        <text x="${x(g.p75_days) + 6}" y="${cy + 4}" class="value">${g.median_days}</text>
      </g>`;
    }).join("")}
    <line x1="${x(14)}" x2="${x(14)}" y1="${top - 14}" y2="${H - 26}" class="target"/>
    <text x="${x(14) + 4}" y="${top - 16}" class="target-label">10 business days (legal target)</text>
  </svg>`;
}

function statsTable(groups) {
  return `<div class="table-scroll"><table class="simple"><thead><tr><th>Project</th><th>Permits</th><th>Typical days</th><th>Middle half</th>
    <th>Within 2 weeks</th><th>Over 90 days</th></tr></thead><tbody>${groups.map(g => `<tr><td>${esc(g.name)}</td>
    <td>${g.permits.toLocaleString("en-CA")}</td><td><b>${g.median_days}</b></td><td>${g.p25_days}–${g.p75_days}</td>
    <td>${g.within_14_days_pct}%</td><td>${g.over_90_days_pct}%</td></tr>`).join("")}</tbody></table></div>`;
}

// Line: median days by year for one project type (2px line, 8px markers, recessive grid).
function statsTrend(g) {
  if (!g) return "";
  const years = Object.keys(g.by_year).sort();
  if (years.length < 2) return `<p class="muted">Not enough years of data for this project type.</p>`;
  const W = 720, H = 240, L = 46, R = 20, T = 18, B = 34;
  const vals = years.map(y => g.by_year[y].median_days);
  const max = Math.ceil(Math.max(...vals, 14) / 20) * 20;
  const x = i => L + (W - L - R) * i / (years.length - 1);
  const y = v => T + (H - T - B) * (1 - v / max);
  const ticks = []; for (let v = 0; v <= max; v += max / 4) ticks.push(Math.round(v));
  const path = vals.map((v, i) => `${i ? "L" : "M"}${x(i)} ${y(v)}`).join(" ");
  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Line chart of median days to permit by year for ${esc(g.name)}">
    ${ticks.map(v => `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" class="grid"/><text x="${L - 8}" y="${y(v) + 4}" class="axis" text-anchor="end">${v}</text>`).join("")}
    <line x1="${L}" x2="${W - R}" y1="${y(14)}" y2="${y(14)}" class="target"/>
    <text x="${L + 6}" y="${y(14) - 6}" class="target-label">10 business days (legal target)</text>
    <path d="${path}" class="line"/>
    ${vals.map((v, i) => `<g class="pt" tabindex="0" data-tip="${esc(`${years[i]}: typical ${v} days (${g.by_year[years[i]].permits} permits)`)}">
      <circle cx="${x(i)}" cy="${y(v)}" r="14" class="hit"/><circle cx="${x(i)}" cy="${y(v)}" r="4.5" class="dot"/>
      <text x="${x(i)}" y="${H - 12}" class="axis" text-anchor="middle">${years[i]}</text></g>`).join("")}
    <text x="${x(vals.length - 1)}" y="${y(vals[vals.length - 1]) - 12}" class="value" text-anchor="end">${vals[vals.length - 1]} days</text>
  </svg>`;
}

function wireChartTips() {
  const tip = document.getElementById("term-tip");
  app.querySelectorAll("[data-tip]").forEach(el => {
    const show = () => {
      tip.innerHTML = esc(el.dataset.tip); tip.hidden = false; tip.style.width = "auto";
      const r = el.getBoundingClientRect();
      tip.style.left = Math.max(12, Math.min(r.left + r.width / 2 - 140, innerWidth - 300)) + "px";
      tip.style.top = Math.max(8, r.top - tip.offsetHeight - 8) + "px";
    };
    el.addEventListener("mouseenter", show); el.addEventListener("focus", show);
    el.addEventListener("mouseleave", hideTerm); el.addEventListener("blur", hideTerm);
  });
}


// ================================================================ AI features (Build Plan steps 20-22)
// Every AI button sends a request to our own server, which checks the $5 budget first
// (checker/ai_client.py). Code on the server checks every AI answer, and nothing goes into
// the form until you tick it. The rules, not the AI, decide PASS or FAIL.
let AI_STATUS = null;      // from /api/ai-status: is the AI set up, and how much of the budget is left
let AI_RESULT = null;      // the last suggestions to review (from a description or drawings)
let AI_DONE = "";          // message after answers were added
const DRAWINGS_KEY = "permitDrawings", VIBES_KEY = "permitVibes", CHAT_KEY = "permitChat", YARD_KEY = "permitYardFaces";
const recallJson = (k) => { try { return JSON.parse(localStorage.getItem(k)); } catch (e) { return null; } };
const storeJson = (k, v) => { try { v === null ? localStorage.removeItem(k) : localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} window.projectChanged?.(); };

function aiOn() { return !!(AI_STATUS && AI_STATUS.enabled); }
function budgetLine() {
  if (!AI_STATUS) return "";
  return AI_STATUS.enabled ? `$${AI_STATUS.left_usd.toFixed(2)} of $${AI_STATUS.budget_usd.toFixed(2)} AI budget left` : AI_STATUS.message;
}
function noteCost(c) {      // after any AI request, update the budget shown everywhere
  if (!c) return;
  AI_STATUS = Object.assign(AI_STATUS || {}, {spent_usd: c.spent_usd, left_usd: c.left_usd, budget_usd: c.budget_usd, enabled: c.left_usd > 0.01});
  refreshAiBox();
  const cb = document.getElementById("chat-budget"); if (cb) cb.textContent = budgetLine();
}
function costText(c) { return c ? `This cost $${c.cost_usd.toFixed(4)}. Used so far: $${c.spent_usd.toFixed(2)} of $${c.budget_usd.toFixed(2)}.` : ""; }

// ---------------------------------------------------------------- step 1: description + drawings
function aiBox() {
  return `<section class="card ai-box" aria-labelledby="ai-title">
      <div class="ai-head"><span class="ai-tag">AI</span><h3 id="ai-title">Fill in the form for me</h3></div>
      <p class="muted small">The AI suggests answers and <b>you tick the ones that are right</b>. The rules, not the AI, decide pass or fail.</p>
      <div class="ai-two">
        <div class="ai-part">
          <h4>From your description</h4>
          <p class="muted small">Write what you're building in the box above, with sizes and distances
            (e.g. <i>“one-storey rear addition, 4 m deep, 0.8 m from the side lot line, lot is 10 m wide, zone RD”</i>).</p>
          <button type="button" class="primary" id="ai-read">Read my description</button>
        </div>
        <div class="ai-part">
          <h4>From your drawings</h4>
          <p class="muted small">Upload site plans, floor plans, elevations or a survey (PDF or photos, up to 5 files, 20 MB).
            The AI reads the numbers, checks the drawings against the City's checklist, and spots places they disagree.</p>
          <label class="file-pick"><input type="file" id="ai-files" multiple accept="application/pdf,image/png,image/jpeg,image/webp,image/gif">
            <span>Choose files</span></label>
          <span id="ai-file-names" class="muted small"></span>
          <button type="button" class="primary" id="ai-read-drawings" hidden>Read my drawings</button>
        </div>
      </div>
      <p id="ai-status" class="muted small" role="status"></p>
      <p class="muted small ai-privacy">What you send is read by Anthropic (the AI company). Leave out names and phone numbers. Files aren't saved.</p>
      <div id="ai-out" aria-live="polite"></div>
    </section>`;
}

function refreshAiBox() {
  const st = document.getElementById("ai-status");
  if (!st) return;
  ["ai-read", "ai-read-drawings"].forEach(id => { const b = document.getElementById(id); if (b) b.disabled = !aiOn(); });
  st.textContent = AI_STATUS ? (aiOn() ? `${budgetLine()} · a description costs about $0.001, drawings about $0.01` : AI_STATUS.message) : "";
}

function wireAiBox() {
  refreshAiBox();
  const out = document.getElementById("ai-out");
  if (AI_RESULT) out.innerHTML = aiReviewHtml(AI_RESULT);
  else if (AI_DONE) out.innerHTML = `<div class="ai-done">${icon("PASS")} ${esc(AI_DONE)}</div>`;
  document.getElementById("ai-read")?.addEventListener("click", readDescription);
  const files = document.getElementById("ai-files");
  files?.addEventListener("change", () => {
    const list = [...files.files];
    document.getElementById("ai-file-names").textContent = list.map(f => f.name).join(", ");
    document.getElementById("ai-read-drawings").hidden = !list.length;
  });
  document.getElementById("ai-read-drawings")?.addEventListener("click", readDrawings);
}

async function readDescription() {
  const btn = document.getElementById("ai-read"), out = document.getElementById("ai-out");
  const text = (ANSWERS.description || "").trim();
  if (text.length < 10) {
    out.innerHTML = `<div class="ai-note">Write a sentence or two in the description box first.</div>`;
    document.querySelector('[name="description"]')?.focus();
    return;
  }
  btn.disabled = true; btn.textContent = "Reading…"; AI_DONE = "";
  out.innerHTML = `<div class="ai-note">The AI is reading your description…</div>`;
  try {
    AI_RESULT = await api("/api/ai/read-plan", {description: text, current: ANSWERS});
    AI_RESULT.source = "text";
    noteCost(AI_RESULT.cost);
    out.innerHTML = aiReviewHtml(AI_RESULT);
  } catch (e) { out.innerHTML = `<div class="ai-note warn">${esc(e.message)}</div>`; }
  out.scrollIntoView({block: "start", behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth"});   // the answer appears below the buttons
  btn.textContent = "Read my description";
  refreshAiBox();
}

function fileToBase64(file) {
  return new Promise((ok, fail) => {
    const r = new FileReader();
    r.onload = () => ok(String(r.result).split(",")[1] || "");
    r.onerror = () => fail(new Error(`Couldn't open ${file.name}.`));
    r.readAsDataURL(file);
  });
}

async function readDrawings() {
  const btn = document.getElementById("ai-read-drawings"), out = document.getElementById("ai-out");
  const list = [...document.getElementById("ai-files").files];
  if (list.length > 5) { out.innerHTML = `<div class="ai-note warn">Please choose up to 5 files.</div>`; return; }
  const mb = list.reduce((s, f) => s + f.size, 0) / 1e6;
  if (mb > 20) { out.innerHTML = `<div class="ai-note warn">Together these files are ${mb.toFixed(0)} MB. Please keep it under 20 MB.</div>`; return; }
  btn.disabled = true; btn.textContent = "Reading…"; AI_DONE = "";
  out.innerHTML = `<div class="ai-note">The AI is reading your drawings. This can take up to a minute…</div>`;
  try {
    const files = await Promise.all(list.map(async f => ({name: f.name, type: f.type, data: await fileToBase64(f)})));
    AI_RESULT = await api("/api/ai/read-drawings", {files, answers: ANSWERS});
    AI_RESULT.source = "drawings";
    noteCost(AI_RESULT.cost);
    storeJson(DRAWINGS_KEY, {files: AI_RESULT.files, summary: AI_RESULT.summary, checklist: AI_RESULT.checklist,
                             conflicts: AI_RESULT.conflicts, when: new Date().toLocaleString()});
    out.innerHTML = aiReviewHtml(AI_RESULT);
  } catch (e) { out.innerHTML = `<div class="ai-note warn">${esc(e.message)}</div>`; }
  out.scrollIntoView({block: "start", behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth"});   // the answer appears below the buttons
  btn.textContent = "Read my drawings";
  refreshAiBox();
}

function aiValue(s) {
  if (s.type === "yesno") return s.value ? "Yes" : "No";
  if (s.value === "none") return "None shown on the map";
  return `${s.value}${s.unit ? " " + s.unit : ""}`;
}

function aiReviewHtml(res) {
  const fromDrawings = res.source === "drawings";
  const rows = res.suggestions.map((s, i) => {
    const changes = s.current !== undefined && s.current !== null && s.current !== "" && s.current !== s.value;
    const tick = fromDrawings ? false : s.quote_found;          // drawing numbers: you must look and tick yourself
    const from = fromDrawings ? `Found on: ${esc(s.where || "the drawings")}. Check it on your drawing before ticking.`
      : s.quote_found ? `From your words: “${esc(s.quote)}”`
      : `⚠ Couldn't find these words in your description: “${esc(s.quote)}”. Left unticked.`;
    return `<label class="ai-row${tick ? "" : " unsure"}">
        <input type="checkbox" data-ai="${i}" ${tick ? "checked" : ""}>
        <span class="ai-q">${esc(s.label)}</span><span class="ai-v">${esc(aiValue(s))}</span>
        <span class="ai-from">${from}${changes ? `<br>Replaces your answer: ${esc(aiValue(Object.assign({}, s, {value: s.current})))}` : ""}</span>
      </label>`;
  }).join("");
  let extra = "";
  if (fromDrawings) {
    extra += res.summary ? `<div class="ai-note"><b>What the drawings show (AI summary):</b> ${esc(res.summary)}</div>` : "";
    if (res.agrees?.length) extra += `<div class="ai-note">${icon("PASS")} The drawings match ${res.agrees.length} answer${res.agrees.length === 1 ? "" : "s"} already in your form: ${esc(res.agrees.join(", "))}.</div>`;
    extra += drawingsChecklistHtml(res);
  }
  if (res.unclear?.length) extra += `<div class="ai-note"><b>The AI wasn't sure about:</b><ul>${res.unclear.map(u => `<li>${esc(u)}</li>`).join("")}</ul></div>`;
  const cost = `<p class="muted small">${costText(res.cost)}</p>`;
  const note = res.note ? `<p class="muted small">${esc(res.note)}</p>` : "";
  if (!res.suggestions.length) return `<div class="ai-note">${fromDrawings && res.agrees?.length ? "No new numbers to fill in." : "The AI didn't find any numbers to fill in."}</div>${extra}${note}${cost}`;
  return `<div class="ai-review">
      <p><b>Check each suggestion.</b> ${fromDrawings ? "Tick the ones that match your drawings." : "Untick anything that's wrong."}
        Nothing is added until you press the button.</p>
      ${fromDrawings ? `<button type="button" class="link" id="ai-tick-all">Tick all</button>` : ""}
      ${rows}
      <div class="row ai-actions"><button type="button" class="primary" id="ai-apply">Add ticked answers</button>
        <button type="button" class="link" id="ai-cancel">Cancel</button></div>
      ${extra}${note}${cost}
    </div>`;
}

function drawingsChecklistHtml(d) {
  const mark = {shown: ["PASS", "Shown"], missing: ["FAIL", "Missing"], unclear: ["NEED MORE INFO", "Unclear"]};
  let html = "";
  if (d.conflicts?.length) html += `<div class="ai-note warn"><b>Things that don't match (${d.conflicts.length}):</b><ul>${
    d.conflicts.map(c => `<li>${esc(c.what)}${c.where ? ` <span class="muted">(${esc(c.where)})</span>` : ""}
      <span class="muted small">· found by ${c.by === "code" ? "the checker" : "the AI"}</span></li>`).join("")}</ul></div>`;
  if (d.checklist?.length) html += `<div class="ai-note"><b>City drawing checklist (AI's read, not a plans review):</b>
    <ul class="ai-check">${d.checklist.map(c => { const [s, word] = mark[c.status] || mark.unclear;
      return `<li class="st-${s.split(" ")[0]}">${icon(s)}<span><b>${esc(c.item)}</b>: ${word}. <span class="muted">${esc(c.note)}</span></span></li>`; }).join("")}</ul></div>`;
  return html;
}

document.addEventListener("click", (e) => {
  if (e.target.id === "ai-cancel") { AI_RESULT = null; document.getElementById("ai-out").innerHTML = ""; }
  if (e.target.id === "ai-tick-all") document.querySelectorAll("[data-ai]").forEach(b => { b.checked = true; });
  if (e.target.id === "ai-apply" && AI_RESULT) {
    const picked = [...document.querySelectorAll("[data-ai]:checked")].map(b => AI_RESULT.suggestions[+b.dataset.ai]);
    picked.forEach(s => { ANSWERS[s.key] = s.value; });
    save();
    AI_DONE = picked.length
      ? `Added ${picked.length} answer${picked.length === 1 ? "" : "s"}. You can check or change them on the next steps.`
      : "Nothing was added.";
    AI_RESULT = null;
    showStep(1);
  }
});

// ---------------------------------------------------------------- results page: drawings, vibes check, shadows
function drawingsCard() {
  const d = recallJson(DRAWINGS_KEY);
  if (!d) return "";
  return `<div class="card"><div class="spread"><h2 style="margin:0">Your drawings <span class="ai-tag">AI</span></h2>
      <button type="button" class="link" id="drawings-forget">Forget these drawings</button></div>
    <p class="muted small">Read on ${esc(d.when)}: ${esc((d.files || []).join(", "))}. AI suggestions, not a plans review.</p>
    ${d.summary ? `<p>${esc(d.summary)}</p>` : ""}${drawingsChecklistHtml(d)}</div>`;
}

function answersKey() { return JSON.stringify(Object.keys(ANSWERS).sort().map(k => [k, ANSWERS[k]])); }

function vibesCard(r) {
  const saved = recallJson(VIBES_KEY);
  const stale = saved && saved.key !== answersKey();
  return `<div class="card vibes"><h2>Vibes check <span class="ai-tag">AI</span></h2>
    <p class="muted">${esc(r.ai?.vibes_check?.text || "")}</p>
    <div class="row ai-actions"><button type="button" class="primary" id="vibes-run" ${aiOn() ? "" : "disabled"}>${saved ? "Run it again" : "Run vibes check"}</button>
      <span class="muted small" id="vibes-status">${aiOn() ? "About $0.002" : esc(AI_STATUS?.message || "")}</span></div>
    <div id="vibes-out">${saved ? (stale ? `<p class="ai-note">Your answers changed since this vibes check. Run it again to update it.</p>` : "") + vibesHtml(saved.result) : ""}</div></div>`;
}

function vibesHtml(v) {
  if (!v) return "";
  if (!v.comments.length) return `<p class="ai-note">The AI didn't have comments it could back up with a guideline.</p>`;
  const tone = {"fits": "PASS", "worth a look": "NEED MORE INFO", "concern": "FLAG"};
  return v.comments.map(c => `<div class="vibe ${(tone[c.tone] || "NEED MORE INFO").split(" ")[0]}">
      <div class="vibe-head">${icon(tone[c.tone] || "NEED MORE INFO")}<b>${esc(c.topic)}</b><span class="chip">${esc(c.tone)}</span></div>
      <p>${esc(c.comment)}</p>
      <blockquote>“${esc(c.quote)}”<footer><a href="${esc(c.link)}" target="_blank" rel="noopener">${esc(c.guideline)}</a>
        · ${c.kind === "quoted" ? "official wording" : "this tool's summary, not official wording"}</footer></blockquote>
    </div>`).join("") + `<p class="muted small">${esc(v.note)} ${v.dropped?.length ? `${v.dropped.length} AI comment(s) were removed because their quote didn't match a guideline.` : ""}</p>`;
}

async function runVibes() {
  const btn = document.getElementById("vibes-run"), out = document.getElementById("vibes-out"), st = document.getElementById("vibes-status");
  btn.disabled = true; st.textContent = "The AI is thinking…";
  try {
    const res = await api("/api/ai/vibes", {answers: ANSWERS, drawings_summary: recallJson(DRAWINGS_KEY)?.summary || ""});
    noteCost(res.cost);
    storeJson(VIBES_KEY, {key: answersKey(), result: res});
    out.innerHTML = vibesHtml(res);
    st.textContent = costText(res.cost);
    btn.textContent = "Run it again";
  } catch (e) { out.innerHTML = `<div class="ai-note warn">${esc(e.message)}</div>`; st.textContent = ""; }
  btn.disabled = !aiOn();
}

function shadowCard(r) {
  const s = r.shadow;
  if (!s) return "";
  if (!s.ready) return `<div class="card"><h2>Shadow preview</h2><p class="muted">${esc(s.message)}</p></div>`;
  const faces = getPref(YARD_KEY) || "N";
  const names = {N: "north", E: "east", S: "south", W: "west"};
  return `<div class="card shadow-card"><h2>Shadow preview <span class="chip">no AI</span></h2>
    <p class="muted small">How far shadows reach. Shown: ${esc(s.about || `a ${s.height_m} m tall building`)}. A rough sketch for talking with neighbours, not a City shadow study.</p>
    <label class="row small" style="gap:8px;align-items:center">Your back yard faces
      <select id="yard-faces">${Object.entries(names).map(([k, n]) => `<option value="${k}" ${k === faces ? "selected" : ""}>${n}</option>`).join("")}</select></label>
    <div id="shadow-svg">${shadowSvg(s, faces)}</div>
    <table class="simple"><thead><tr><th>When (sun time)</th><th>Sun height</th><th>Shadow length</th></tr></thead><tbody>${
      s.times.map(t => `<tr><td>${esc(t.label)}</td><td>${t.sun_height_deg}°</td><td><b>${t.length_m} m</b></td></tr>`).join("")}</tbody></table>
    <p class="muted small">${esc(s.note)} Sun time: noon is when the sun is highest (about 1:20 pm daylight time in Toronto).</p></div>`;
}

function hull(pts) {           // the outline around a set of points (for drawing a shadow shape)
  pts = pts.slice().sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const cross = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
  const lower = [], upper = [];
  for (const p of pts) { while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], p) <= 0) lower.pop(); lower.push(p); }
  for (const p of pts.reverse()) { while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], p) <= 0) upper.pop(); upper.push(p); }
  return lower.slice(0, -1).concat(upper.slice(0, -1));
}

function shadowSvg(s, faces) {
  // Drawing: "up" is toward the back of the lot. Turn the compass so the chosen direction is up.
  const turn = {N: 0, E: 90, S: 180, W: 270}[faces] * Math.PI / 180;
  const toScreen = (dx, dy) => { const L = Math.hypot(dx, dy), b = Math.atan2(dx, dy) - turn; return [L * Math.sin(b), -L * Math.cos(b)]; };
  const {w, d} = s.box;
  const rect = [[-w / 2, -d / 2], [w / 2, -d / 2], [w / 2, d / 2], [-w / 2, d / 2]];
  const shapes = s.times.map(t => { const [sx, sy] = toScreen(t.dx, t.dy); return {t, pts: hull(rect.concat(rect.map(([x, y]) => [x + sx, y + sy])))}; });
  const all = shapes.flatMap(x => x.pts).concat(rect);
  const pad = 3, minX = Math.min(...all.map(p => p[0])) - pad, maxX = Math.max(...all.map(p => p[0])) + pad;
  const minY = Math.min(...all.map(p => p[1])) - pad, maxY = Math.max(...all.map(p => p[1])) + pad;
  const W = 520, scale = Math.min(W / (maxX - minX), 340 / (maxY - minY)), H = (maxY - minY) * scale;
  const P = ([x, y]) => `${((x - minX) * scale).toFixed(1)},${((y - minY) * scale).toFixed(1)}`;
  const colours = ["var(--shadow-1)", "var(--shadow-2)", "var(--shadow-3)"];
  const [nx, ny] = toScreen(0, 1);
  const legend = s.times.map((t, i) => `<span class="lg"><i style="background:${t.main ? colours[i % 3] : "transparent"};border:${t.main ? "0" : "1.5px dashed var(--muted)"}"></i>${esc(t.label)}</span>`).join("");
  return `<svg viewBox="0 0 ${W} ${H.toFixed(0)}" role="img" aria-label="Shadow sketch: shadows reach up to ${Math.max(...s.times.map(t => t.length_m))} metres">
      ${shapes.map((x, i) => x.t.main ? `<polygon points="${x.pts.map(P).join(" ")}" fill="${colours[i % 3]}" />`
        : `<polygon points="${x.pts.map(P).join(" ")}" fill="none" stroke="var(--muted)" stroke-dasharray="5 4" />`).join("")}
      <polygon points="${rect.map(P).join(" ")}" fill="var(--accent)" />
      <g transform="translate(${W - 34},34)"><circle r="22" fill="var(--card)" stroke="var(--line)"/>
        <line x1="0" y1="0" x2="${(nx * 16).toFixed(1)}" y2="${(ny * 16).toFixed(1)}" stroke="var(--text)" stroke-width="2.5" stroke-linecap="round"/>
        <text x="${(nx * 30).toFixed(1)}" y="${(ny * 30 + 4).toFixed(1)}" text-anchor="middle" font-size="12" fill="var(--text)">N</text></g>
      <text x="8" y="16" font-size="12" fill="var(--muted)">↑ back of lot</text>
      <text x="8" y="${(H - 8).toFixed(0)}" font-size="12" fill="var(--muted)">↓ street</text>
    </svg><div class="legend small">${legend}</div>`;
}

function wireResultsAi() {
  document.getElementById("vibes-run")?.addEventListener("click", runVibes);
  document.getElementById("drawings-forget")?.addEventListener("click", () => { storeJson(DRAWINGS_KEY, null); drawResults(true); });
  document.getElementById("yard-faces")?.addEventListener("change", (e) => {
    setPref(YARD_KEY, e.target.value); window.projectChanged?.();
    document.getElementById("shadow-svg").innerHTML = shadowSvg(REPORT.shadow, e.target.value);
  });
}

// ---------------------------------------------------------------- chatbot: "Ask about my project"
let CHAT = recallJson(CHAT_KEY) || [];

function chatRender() {
  const box = document.getElementById("chat-msgs");
  if (!box) return;
  if (!CHAT.length) {
    box.innerHTML = `<div class="chat-hello"><p><b>Ask anything about your project.</b> I use your answers and results, and I run the real checker for “what if” questions.</p>
      <div class="chat-starters">${["Why did my project fail?", "What does established grade mean?", "What if my side setback was 1.2 m?", "Which forms do I still need?"]
        .map(q => `<button type="button" class="chip-btn" data-ask="${esc(q)}">${esc(q)}</button>`).join("")}</div></div>`;
  } else {
    box.innerHTML = CHAT.map((m, i) => m.role === "user" ? `<div class="msg me">${esc(m.content)}</div>`
      : `<div class="msg bot">${chatText(m.content)}${(m.what_ifs || []).map(w => `<div class="whatif">${icon("PASS")}<span><b>Checked by the real checker</b> with ${
          esc(Object.entries(w.changes).map(([k, v]) => `${field(k)?.label || k} = ${aiValue({type: field(k)?.type, value: v, unit: field(k)?.unit || ""})}`).join(", ") || "no changes")}:
          ${esc(w.overall)}${w.changed.length ? `<br>${w.changed.map(c => `${esc(c.rule_id)}: ${esc(c.before)} → <b>${esc(c.after)}</b>`).join(" · ")}` : ""}</span></div>`).join("")}
          ${(m.suggestions || []).map((s, j) => `<button type="button" class="chip-btn add" data-add="${i}:${j}" ${s.added ? "disabled" : ""}>${s.added ? "✓ Added" : "Add to form"}: ${esc(s.label)} = ${esc(aiValue(s))}</button>`).join("")}
        </div>`).join("");
  }
  box.scrollTop = box.scrollHeight;
}

function chatText(t) {        // plain text -> safe HTML with paragraphs and simple bullet lists
  return esc(t).split(/\n{2,}/).map(p => /^\s*[-•*] /m.test(p)
    ? `<ul>${p.split("\n").map(l => l.replace(/^\s*[-•*] /, "")).filter(Boolean).map(l => `<li>${l}</li>`).join("")}</ul>`
    : `<p>${p.replace(/\n/g, "<br>").replace(/\*\*(.+?)\*\*/g, "<b>$1</b>")}</p>`).join("");
}

function openChat() {
  let panel = document.getElementById("chat-panel");
  if (!panel) {
    panel = document.createElement("aside");
    panel.id = "chat-panel"; panel.className = "chat-panel no-print"; panel.setAttribute("aria-label", "Ask about my project");
    panel.innerHTML = `<div class="chat-top"><span class="ai-tag">AI</span><b>Ask about my project</b>
        <button type="button" class="link" id="chat-clear">Clear</button><button type="button" class="link" id="chat-close" aria-label="Close chat">✕</button></div>
      <div id="chat-msgs" class="chat-msgs" aria-live="polite"></div>
      <form id="chat-form" class="chat-form"><label class="sr-only" for="chat-in">Your question</label>
        <textarea id="chat-in" rows="2" maxlength="1500" placeholder="Ask a question…"></textarea>
        <button type="submit" class="primary" id="chat-send">Send</button></form>
      <p class="muted small chat-foot"><span id="chat-budget"></span><br>Answers explain the checker's results; they're not approvals. Sent to Anthropic: leave out names and phone numbers.</p>`;
    document.body.append(panel);
    panel.querySelector("#chat-close").addEventListener("click", closeChat);
    panel.querySelector("#chat-clear").addEventListener("click", () => { CHAT = []; storeJson(CHAT_KEY, CHAT); chatRender(); });
    panel.querySelector("#chat-form").addEventListener("submit", (e) => { e.preventDefault(); sendChat(); });
    panel.querySelector("#chat-in").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendChat(); } });
    panel.addEventListener("keydown", (e) => { if (e.key === "Escape") closeChat(); });
    panel.addEventListener("click", (e) => {
      const ask = e.target.closest("[data-ask]"); if (ask) { document.getElementById("chat-in").value = ask.dataset.ask; sendChat(); }
      const add = e.target.closest("[data-add]");
      if (add) {
        const [i, j] = add.dataset.add.split(":").map(Number), s = CHAT[i].suggestions[j];
        ANSWERS[s.key] = s.value; save(); s.added = true; storeJson(CHAT_KEY, CHAT); chatRender();
        if (location.hash.startsWith("#/check/5")) showResults(); else if (location.hash.startsWith("#/check/")) route();
      }
    });
  }
  panel.hidden = false;
  document.getElementById("chat-fab").setAttribute("aria-expanded", "true");
  document.getElementById("chat-budget").textContent = budgetLine();
  const input = document.getElementById("chat-in"), send = document.getElementById("chat-send");
  input.disabled = send.disabled = !aiOn();
  if (!aiOn()) input.placeholder = AI_STATUS?.message || "The AI isn't set up yet.";
  chatRender();
  input.focus();
}

function closeChat() {
  const p = document.getElementById("chat-panel"); if (p) p.hidden = true;
  const fab = document.getElementById("chat-fab"); fab.setAttribute("aria-expanded", "false"); fab.focus();
}

async function sendChat() {
  const input = document.getElementById("chat-in"), send = document.getElementById("chat-send");
  const q = input.value.trim();
  if (!q || send.disabled) return;
  CHAT.push({role: "user", content: q}); input.value = ""; chatRender();
  const box = document.getElementById("chat-msgs");
  box.insertAdjacentHTML("beforeend", `<div class="msg bot typing">Thinking…</div>`); box.scrollTop = box.scrollHeight;
  send.disabled = true;
  try {
    const res = await api("/api/ai/chat", {messages: CHAT.slice(-12).map(m => ({role: m.role, content: m.content})),
                                          answers: ANSWERS, drawings_summary: recallJson(DRAWINGS_KEY)?.summary || ""});
    CHAT.push({role: "assistant", content: res.reply, what_ifs: res.what_ifs, suggestions: res.suggestions});
    noteCost(res.cost);
  } catch (e) {
    CHAT.push({role: "assistant", content: "⚠ " + e.message, error: true});
  }
  CHAT = CHAT.slice(-30);
  storeJson(CHAT_KEY, CHAT.filter(m => !m.error));
  send.disabled = !aiOn();
  chatRender();
}

(function addChatButton() {
  const fab = document.createElement("button");
  fab.id = "chat-fab"; fab.type = "button"; fab.className = "chat-fab no-print";
  fab.setAttribute("aria-expanded", "false"); fab.setAttribute("aria-controls", "chat-panel");
  fab.innerHTML = `<span class="ai-tag">AI</span> Ask about my project`;
  fab.addEventListener("click", () => { const p = document.getElementById("chat-panel"); p && !p.hidden ? closeChat() : openChat(); });
  document.body.append(fab);
})();
