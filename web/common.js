// Shared helpers for the main page (index.html) and the report (report.html).
// Nothing here decides PASS/FAIL: it only DISPLAYS what the Python checker sent back.

// ---------- words on the page (translation-ready) ----------
// English is the base. Other languages come from data/toronto/translations.json ("ui").
// A word with no translation falls back to English.
const EN = {
  title: "Permit Pre-Check", subtitle: "Toronto · low-rise homes · Zoning By-law 569-2013",
  draft: "Draft pre-check for review. Not an approval.",
  nav_home: "Home", nav_check: "Check a project", nav_build: "What can I build?", nav_stats: "Toronto stats", mode: "Mode", mode_home: "Homeowner", mode_designer: "Designer", nav_guide: "How to use", language: "Language",
  simple: "Simple words", bigtext: "Bigger text", settings: "Settings", theme: "Colours", theme_auto: "Auto", theme_light: "Light", theme_dark: "Dark",
  step1: "Project", step2: "Property", step3: "Lot & house", step4: "Measurements", step5: "Results",
  next: "Next →", back: "← Back", see_results: "See results", check: "Check my project",
  permit_q: "Does it need a building permit?", overall: "Summary",
  PASS: "PASS", FAIL: "FAIL", "NEED MORE INFO": "NEED MORE INFO", FLAG: "FLAG",
  tile_FAIL: "Don't pass", tile_NEED: "Need an answer", tile_FLAG: "To follow up", tile_PASS: "Pass",
  tile_more_FAIL: "Change the plan or ask for a variance", tile_more_NEED: "Answer a question to check these",
  tile_more_FLAG: "Other approvals and reminders", tile_more_PASS: "Rules your project meets",
  limit: "Limit", yours: "Yours", rule: "Rule", section: "By-law section", confidence: "Confidence",
  High: "High", Verify: "Verify", "Needs human check": "Needs human check",
  fix: "Fix it", answer_this: "Answer this question →", details: "Full details (English)",
  open_report: "Open printable report", change: "Change answers", start_over: "New project",
  show_all: "Show everything", passed_n: "rules your project meets (tap to open)",
  grp_permit: "Does it need a permit?", grp_zoning: "Zoning", grp_suites: "Suites",
  grp_prov: "Provincial rules", grp_code: "Building Code (safety)", grp_ap: "Other approvals", stop: "STOP",
};
let LANG = "en";
let TRANSLATIONS = {};

function t(key) {
  const tr = TRANSLATIONS[LANG];
  if (tr && tr.ui && tr.ui[key]) return tr.ui[key];
  return EN[key] || key;
}

const GROUP_ORDER = ["Does it need a permit?", "Zoning", "Suites", "Provincial rules", "Building Code (safety)", "Other approvals"];
const GROUP_KEY = {"Does it need a permit?": "grp_permit", "Zoning": "grp_zoning", "Suites": "grp_suites",
                   "Provincial rules": "grp_prov", "Building Code (safety)": "grp_code", "Other approvals": "grp_ap"};
const STATUS_CLASS = {"PASS": "PASS", "FAIL": "FAIL", "NEED MORE INFO": "NEED", "FLAG": "FLAG"};
const STATUS_ICON = {"PASS": "✓", "FAIL": "✕", "NEED MORE INFO": "?", "FLAG": "!"};

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
}

function fmtNum(v, unit) {
  if (v === null || v === undefined || v === "") return "—";
  let s = typeof v === "number" ? String(Math.round(v * 1000) / 1000) : String(v);
  if (unit) s += unit.startsWith("%") ? unit : " " + unit;
  return s;
}

function chip(status) {
  return `<span class="chip ${STATUS_CLASS[status] || ""}">${esc(t(status))}</span>`;
}
const badge = chip;   // older name, still used by the report

function icon(status) {
  return `<span class="icon" aria-hidden="true"><span>${STATUS_ICON[status] || "•"}</span></span>`;
}

function confHtml(c) {
  const cls = c === "Needs human check" ? "conf-human" : (c === "Verify" ? "conf-verify" : "");
  return `<span class="${cls}">${esc(t(c))}</span>`;
}
const confLabel = confHtml;

// The main sentence for a result: translated, or simple words, or the full English message.
function mainSentence(r, simple) {
  if (LANG !== "en" && r.translated && r.translated[LANG]) return r.translated[LANG];
  if (simple && r.plain) return r.plain;
  return r.message;
}

// Dictionary tooltips on the main page (the report page has no glossify, so text stays plain there)
const gl = (html) => (typeof glossify === "function" ? glossify(html) : html);

// One result as a card (used on the main page).
// With Simple words on: the plain sentence comes first and big, and the rule details fold away.
function resultCard(r, opts = {}) {
  const sentence = mainSentence(r, opts.simple);
  const rule = r.link ? `<a href="${esc(r.link)}" target="_blank" rel="noopener">${esc(r.rule_id)}</a>` : esc(r.rule_id);
  const asks = (r.status === "NEED MORE INFO" && r.asks && r.asks.length && opts.onAnswer)
    ? `<div class="row" style="margin-top:6px"><button class="link" data-answer="${esc(r.asks[0])}">${esc(t("answer_this"))}</button></div>` : "";
  const facts = `<dl>
      ${r.limit !== null && r.limit !== undefined ? `<dt>${esc(t("limit"))}</dt><dd>${esc(fmtNum(r.limit, r.unit))}</dd>` : ""}
      ${r.value !== null && r.value !== undefined ? `<dt>${esc(t("yours"))}</dt><dd>${esc(fmtNum(r.value, r.unit))}</dd>` : ""}
      <dt>${esc(t("rule"))}</dt><dd>${rule} · ${esc(r.section)}</dd>
      <dt>${esc(t("confidence"))}</dt><dd>${confHtml(r.confidence)}</dd>
    </dl>`;
  const fix = r.fix ? `<div class="fix"><b>${esc(t("fix"))}:</b> ${esc(r.fix)}</div>` : "";
  if (opts.simple && LANG === "en") {
    return `<article class="item ${STATUS_CLASS[r.status]} simple">
      ${icon(r.status)}
      <div class="item-head"><p class="say big-say">${gl(esc(sentence))}</p>${chip(r.status)}</div>
      ${fix}${asks}
      <details><summary>Show rule details</summary><p class="small" style="margin:6px 0 0"><b>${esc(r.title)}</b></p>
        ${sentence !== r.message ? `<p class="small" style="margin:4px 0 0">${esc(r.message)}</p>` : ""}${facts}</details>
    </article>`;
  }
  const showDetails = sentence !== r.message;
  return `<article class="item ${STATUS_CLASS[r.status]}">
    ${icon(r.status)}
    <div class="item-head"><h4>${gl(esc(r.title))}</h4>${chip(r.status)}</div>
    <p class="say">${gl(esc(sentence))}</p>
    ${showDetails ? `<details><summary>${esc(t("details"))}</summary>${esc(r.message)}</details>` : ""}
    ${facts}${fix}${asks}
  </article>`;
}

// ---------- table versions (used by the printable report) ----------
function resultsTable(results) {
  const rows = results.map(r => `
    <tr>
      <td>${chip(r.status)}</td>
      <td><b>${r.link ? `<a href="${esc(r.link)}" target="_blank" rel="noopener">${esc(r.rule_id)}</a>` : esc(r.rule_id)}</b>
          <div class="muted small">${esc(r.category || "")}</div></td>
      <td>${esc(fmtNum(r.limit, r.unit))}</td>
      <td>${esc(fmtNum(r.value, r.unit))}</td>
      <td>${esc(r.section)}</td>
      <td>${confHtml(r.confidence)}</td>
      <td>${esc(r.message)}${r.fix ? `<div class="fix"><b>${esc(t("fix"))}:</b> ${esc(r.fix)}</div>` : ""}</td>
    </tr>`).join("");
  return `<table class="simple"><thead><tr><th>Result</th><th>Rule</th><th>Limit</th><th>Yours</th>
    <th>By-law section</th><th>Confidence</th><th>What it means</th></tr></thead><tbody>${rows}</tbody></table>`;
}

function groupedResults(report) {
  let html = "";
  for (const g of GROUP_ORDER) {
    const rs = report.results.filter(r => r.group === g);
    if (!rs.length) continue;
    html += `<h3 class="group-title">${esc(t(GROUP_KEY[g]))}</h3>` + resultsTable(rs);
    if (g === "Building Code (safety)") {
      html += `<p class="safety-note"><b>Safety results never mean "safe" or "approved". A qualified designer must confirm.</b></p>`;
    }
  }
  return html;
}

function countsHtml(c) {
  return `<div class="row">${["FAIL", "NEED MORE INFO", "FLAG", "PASS"].map(s => `<span>${chip(s)} ${c[s] || 0}</span>`).join("")}</div>`;
}
