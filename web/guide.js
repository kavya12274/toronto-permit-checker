// The "How to use" guide. It pops up by itself the first time someone opens the app.
// "How to use" in the top bar opens it again. Skip, ✕ Close or the Esc key closes it.
// "▶ Play as video" moves through the slides by itself. Animations stop if the
// computer is set to reduce motion.

// Bump the version when the guide changes, so everyone sees the new version once.
const GUIDE_KEY = "permitGuideSeen_v3";
const SLIDE_MS = 8000;

const GUIDE = [
  {title: "Check your home project in about 10 minutes",
   body: `<p>This tool checks a home project in Toronto (an addition, deck, garden suite, basement apartment and more)
            against the zoning by-law, key Building Code rules and other approvals.</p>
          <p><b>Two ways to start:</b></p>
          <ul><li><b>Check a project</b>: you have an idea or drawings, and want to know if they pass.</li>
              <li><b>What can I build?</b>: no design yet. See the biggest thing your lot allows.</li></ul>
          <p><b>Have these ready if you can:</b> the address, your measurements, and a survey of the lot.</p>
          <p class="muted small">It's a draft pre-check, not an approval. Your answers stay on this computer
            (only the address is sent to the City's map, if you use Look up).</p>`},
  {title: "No design yet? Try “What can I build?”",
   body: `<div class="mock" aria-hidden="true"><div class="m-card"><b>What your lot allows</b>
            <div class="m-row PASS appear1">Biggest addition: 8.2 m wide × 17 m deep, 10 m tall</div>
            <div class="m-row PASS appear2">Biggest garden suite: 2 storeys, up to 42 m²</div>
            <div class="m-row PASS appear3">Most homes: up to 4 units</div></div></div>
          <p>Enter your lot (Look up fills most of it). We run the rules <b>backwards</b> to show the biggest addition, garden suite,
             laneway suite or multiplex allowed, and double-check each one with the normal checker.</p>
          <p class="muted small">Tap <b>Check this design</b> to see its full results, or <b>Start from it and adjust</b>.</p>`},
  {title: "Step 1: Pick your project",
   body: `<div class="mock" aria-hidden="true"><div class="m-card"><b>What are you building?</b><div style="margin-top:8px">
            <span class="m-btn">Rear addition</span><span class="m-btn pick">Garden suite</span>
            <span class="m-btn">Deck</span><span class="m-btn">Secondary suite</span></div></div></div>
          <p>Tap the type of project. The tool then only asks the questions that matter for it.</p>
          <p><b>Shortcut:</b> describe your project, or upload your drawings, and the AI suggests answers. You tick the ones
             that are right. The rules, not the AI, decide pass or fail.</p>`},
  {title: "Step 2: Tell us about the property",
   body: `<div class="mock" aria-hidden="true"><div class="m-card"><b>Address</b>
            <div class="m-input"><span class="typed">123 Example St</span></div><span class="m-btn primary pulse">Look up</span></div></div>
          <p>Type the address and press <b>Look up</b>. We read the City's zoning map and fill in the zone, height and
             coverage values, and whether it's in a heritage district, a ravine area or TRCA's area.</p>
          <p class="muted small">Check what it fills in. If Look up can't find something, you can type it in yourself.</p>`},
  {title: "Steps 3 and 4: Lot, house and measurements",
   body: `<div class="mock" aria-hidden="true"><div class="m-card"><b>Space to the <span class="term">back lot line</span></b>
            <div class="m-input"><span class="typed">7.5 m</span></div>
            <b>Does it have dormers?</b><div><span class="m-btn">Yes</span><span class="m-btn">No</span><span class="m-btn pick">Don't know</span></div></div></div>
          <p>Fill in what you know. <b>Don't know? Leave it.</b> Rules that need it will say NEED MORE INFO, never PASS.</p>
          <p>Words with a <span class="term">dotted underline</span> are zoning terms: <b>hover or tap</b> one to see what it means.</p>
          <p class="muted small">Extra questions are folded away under “More questions” and “Optional” sections.</p>`},
  {title: "Step 5: Read your results",
   body: `<div class="mock" aria-hidden="true"><div class="m-card">
            <div class="m-row FAIL appear1">✕ FAIL: side setback, RD-18, s. 10.20.40.70(3)(B)</div>
            <div class="m-row NEED appear2">? NEED MORE INFO: rear setback (lot depth missing)</div>
            <div class="m-row FLAG appear3">! FLAG: tree permit may be needed</div></div></div>
          <ul><li><b>PASS</b>: meets the rule. <b>FAIL</b>: doesn't.</li>
              <li><b>NEED MORE INFO</b>: tap “Answer this question” to jump straight to it.</li>
              <li><b>FLAG</b>: something to look into, like another approval.</li></ul>
          <p class="muted small">Tap a summary tile to show only fails, open questions and so on. Each result shows the rule,
            the by-law section and how sure we are. Building Code results always need a qualified designer to confirm.</p>`},
  {title: "Avoid getting sent back",
   body: `<div class="mock" aria-hidden="true"><div class="m-card">
            <div class="m-row NEED appear1">69 days: typical wait for a garden suite permit in Toronto</div>
            <div class="m-row FLAG appear2">Often missed: the Tree Declaration form</div>
            <div class="m-row FLAG appear3">Often missed: a current survey for the site plan</div></div></div>
          <p>Below your results: the reasons applications like yours get returned, from the City's own advice, with what to do
             about each one. You also see how long permits like yours really take in Toronto.</p>
          <p class="muted small">Want the full picture? <b>Toronto stats</b> in the menu shows real wait times for every project
            type, from the City's open data.</p>`},
  {title: "Fix it, or compare designs",
   body: `<div class="mock" aria-hidden="true"><div class="m-card"><div class="m-row flip"></div>
            <span class="m-btn">One storey ✓</span><span class="m-btn">Two storeys: needs a variance</span></div></div>
          <p>Each FAIL shows the <b>smallest change</b> that would pass, and the minor variance path if you'd rather ask for an exception.</p>
          <p>Not sure which version is best? <b>Compare designs</b> puts two or three side by side: which passes, which needs a
             variance, and the rough permit fees.</p>`},
  {title: "Your permit roadmap, then print it",
   body: `<div class="mock" aria-hidden="true"><div class="m-card">
            <div class="m-row PASS appear1">☑ Site plan (current survey)</div>
            <div class="m-row appear2" style="background:var(--grey-bg)">☐ Tree Declaration form</div>
            <div class="m-row appear3" style="background:var(--grey-bg)">Inspections: footings → framing → insulation → final</div>
            <span class="m-btn primary">Open printable report</span></div></div>
          <p>The roadmap shows what happens after the check: a <b>timeline</b> from idea to final inspection, the <b>drawings and
             forms</b> to send in (tick them off as you go), and the <b>inspections</b> the City will do.</p>
          <p>Press <b>Open printable report</b>, then <b>Print / Save as PDF</b> to take it to a designer.</p>`},
  {title: "AI helpers (they never decide pass or fail)",
   body: `<div class="mock" aria-hidden="true"><div class="m-card">
            <div class="m-row PASS appear1">Upload drawings: numbers read, City checklist, mismatches found</div>
            <div class="m-row NEED appear2">“What if my setback was 1.2 m?” → checked by the real checker</div>
            <div class="m-row FLAG appear3">Vibes check: fits the street? Each comment quotes the Official Plan</div></div></div>
          <ul><li><b>From your drawings</b> (step 1): upload PDFs or photos. The AI reads the numbers, checks the drawings against the
                City's checklist and lists anything that doesn't match. You tick each number after looking at your drawing.</li>
              <li><b>Ask about my project</b> (button at the bottom right): questions about your results. For “what if”, it runs the real checker.</li>
              <li><b>Vibes check</b> (results page): opinions on how the design fits the neighbourhood, each quoting a guideline.</li>
              <li><b>Shadow preview</b> (results page): how far the shadow reaches. Plain maths, no AI.</li></ul>
          <p class="muted small">AI features need an API key (see the README). What you send is read by Anthropic, so leave out names and phone numbers.</p>`},
  {title: "Make it work for you",
   body: `<div class="mock" aria-hidden="true"><div class="m-card"><b>Settings</b><div style="margin-top:8px">
            <span class="m-btn pick">Homeowner</span><span class="m-btn">Designer</span></div>
            <div style="margin-top:6px"><span class="m-btn">Language</span><span class="m-btn">Simple words</span>
            <span class="m-btn">Bigger text</span><span class="m-btn">Light / Dark</span></div></div></div>
          <ul><li><b>Homeowner</b> mode: plain words and just the essentials.</li>
              <li><b>Designer</b> mode: every number and by-law section in one table, every question open, and exports (CSV, JSON).</li>
              <li>Also in <b>Settings</b>: language, simple words, bigger text, and light or dark colours.</li></ul>
          <p class="muted small">Your answers save automatically. The <b>By-law dictionary</b> and <b>Toronto stats</b> are linked at
            the bottom of every page. Reopen this guide any time with <b>How to use</b>.</p>`},
];

let guide = null;   // {dialog, index, playing, timer}

function guideSeen() { try { return localStorage.getItem(GUIDE_KEY) === "yes"; } catch (e) { return false; } }
function markGuideSeen() { try { localStorage.setItem(GUIDE_KEY, "yes"); } catch (e) {} }

function openGuide() {
  if (guide) guide.dialog.remove();
  const dialog = document.createElement("dialog");
  dialog.className = "guide";
  dialog.setAttribute("aria-labelledby", "guide-title");
  dialog.style.setProperty("--slide-ms", SLIDE_MS + "ms");
  dialog.addEventListener("close", () => {
    clearTimeout(guide.timer);
    markGuideSeen();
    dialog.remove();
    guide = null;
    if (typeof focusHeading === "function") focusHeading();
  });
  document.body.append(dialog);
  guide = {dialog, index: 0, playing: false, timer: null};
  showSlide(0);
  dialog.showModal();
}

function showSlide(index) {
  const {dialog} = guide;
  const last = GUIDE.length - 1;
  guide.index = index;
  clearTimeout(guide.timer);
  if (guide.playing && index < last) guide.timer = setTimeout(() => showSlide(index + 1), SLIDE_MS);
  if (index === last) guide.playing = false;
  const slide = GUIDE[index];

  dialog.innerHTML = `
    <div class="g-head">
      <span class="muted small">How to use · ${index + 1} of ${GUIDE.length}</span>
      <div class="row">
        <button class="link" data-act="play">${guide.playing ? "❚❚ Pause" : "▶ Play as video"}</button>
        <button class="link" data-act="close" aria-label="Close the guide">✕ Close</button>
      </div>
    </div>
    <div class="bar" aria-hidden="true"><span class="${guide.playing ? "run" : ""}"></span></div>
    <div class="g-body"><h2 id="guide-title">${slide.title}</h2>${slide.body}</div>
    <div class="g-foot">
      ${index === last ? "<span></span>" : `<button class="link" data-act="close">Skip the guide</button>`}
      <div class="dots" aria-hidden="true">${GUIDE.map((_, i) => `<span class="${i === index ? "on" : ""}"></span>`).join("")}</div>
      <div class="row">
        ${index > 0 ? `<button data-act="back">← Back</button>` : ""}
        <button class="primary" data-act="next">${index === last ? "Start checking" : "Next →"}</button>
      </div>
    </div>`;

  dialog.querySelectorAll("[data-act]").forEach(b => b.addEventListener("click", () => {
    const act = b.dataset.act;
    if (act === "close") dialog.close();
    if (act === "back") showSlide(index - 1);
    if (act === "next") {
      if (index === last) { dialog.close(); if (!location.hash.startsWith("#/check")) location.hash = "#/check/1"; }
      else showSlide(index + 1);
    }
    if (act === "play") { guide.playing = !guide.playing; showSlide(guide.playing && index === last ? 0 : index); }
  }));
  dialog.querySelector('[data-act="next"]').focus();
}
