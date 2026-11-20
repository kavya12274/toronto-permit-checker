# Toronto Low-Rise Permit Checker (prototype)

A pre-check tool for low-rise residential projects in Toronto. You pick a project type and enter details about your property and project. It tells you:

1. whether you need a building permit,
2. how the project measures up against Toronto zoning (By-law 569-2013, zones R and RD), key Ontario Building Code rules and provincial rules,
3. which other approvals you may need,
4. how to fix each FAIL, and the minor variance path,

and it makes a printable draft report.

**Draft pre-check for review. Not an approval.** A Knowledge Society (TKS) Innovate prototype, not a published product.

You don't need to install anything. It uses only Python 3, which is already on your Mac.

---

## 1. Run the app

**Easiest:** double-click **`Start Permit Checker.command`**. Your browser opens at http://localhost:8010. To stop, close the Terminal window.

**Or in Terminal:**

```bash
cd "path/to/this/folder"
```

```bash
python3 app.py
```

Press **Control-C** in Terminal to stop.

How to use it (a **How to use** guide pops up the first time; reopen it from the top bar):
1. **Project:** tap your project type.
2. **Property:** type the address and press **Look up**. It fills in the zone label, HT/ST, lot coverage, grey-property status, heritage district, ravine and TRCA area from the City's and TRCA's open map data. Check what it filled in.
3. **Lot & house**, then 4. **Measurements:** only the questions that matter for your project. Every question is optional. "Don't know" means the rules that need it say **NEED MORE INFO** (never PASS).
5. **Results:** tap a summary tile (Doesn't meet / Need more info / Look into / Meets the rule) to show only those. On a NEED MORE INFO result, **Answer this question** jumps to the question. Then **Open printable report**, and press **Print / Save as PDF**.

**Also:**
- **What can I build?** (in the menu): enter your lot, and the rules run backwards to show the biggest addition, garden suite, laneway suite or multiplex allowed. Each one is double-checked by the normal checker.
- **Compare designs** (from the results): put two or three versions side by side. You see which passes, which needs a variance, and the rough permit fees.
- **Permit roadmap** (on the results and in the report): the drawings and forms to send in (tick them off as you go), the City's inspection stages, and a timeline from idea to final inspection.

- **Avoid getting sent back** (on the results): the reasons applications like yours get returned, from the City's own pages, plus how long permits like yours really take in Toronto.
- **Toronto stats** (in the menu): real wait times by project type from the City's open permit data.
- **By-law dictionary**: words with a dotted underline show a plain-language definition from Chapter 800 when you hover or tap. The full list is linked at the bottom of every page.

- **My projects** (in the menu): every project saves itself as you go, with an ID like PC-7KQ2MX (the fence checker's idea). Open, rename or delete them, or start a new one. Like the fence checker, only the answers (plus the AI notes) are saved, and results are worked out fresh each time. Projects are kept in your browser, not on the server, so on a public site nobody can see anyone else's. **Download a backup** saves them to a file, and **Restore** loads it on another computer. Three **example projects** (rear addition, garden suite from a drawing, heritage-district deck) come with the real AI results from the Nov 18 test run, so opening them costs nothing.

Your answers save automatically on this computer. **Settings** in the top bar has **Mode** (Homeowner: plain words and the essentials; Designer: every number, every section open, a full results table and exports to CSV/JSON), Language, Simple words, Bigger text and Colours (Auto / Light / Dark).

**Refreshing the City data** (optional, needs internet):
- Permit stats, about 220 MB download:

```bash
python3 tools/build_stats.py
```

- By-law dictionary, from Chapter 800:

```bash
python3 tools/build_glossary.py
``` The page also works in dark mode, on a phone, and with a keyboard only.

## 2. Re-import the spreadsheet after you update rules

The rules live in **data files**, not in the code (golden rule 1). After you change a rule, number or test in the workbook:

1. In Google Sheets: **File → Download → Microsoft Excel (.xlsx)** (this gets every tab at once).
2. In Terminal, from this folder, run:

```bash
python3 import_workbook.py ~/"Downloads/Toronto Low-Rise Permit Checker – Sources.xlsx"
```

If you leave out the file name, it uses the newest `Toronto Low-Rise Permit Checker*.xlsx` in Downloads.

3. Run the tests (next section) to see whether anything changed.

The importer rewrites `data/toronto/rules.json`, `project_types.json`, `test_cases.json`, `sources.json`, `build_plan.json`, `read_me.json` and `import_info.json`. It never touches the hand-written files (see "Files" below). It also tells you how many rules are ticked "Verified vs PDF".

**Which edits work with no code change:**
- Changing a number in the **Limit** column (for example RD-18's 0.9 m), the **Section**, the **Confidence** level, the rule text, the link or the notes.

**Which edits need a code change:**
- A number written inside the **Applies when** or **Notes** text (for example the frontage bands 6/12/15/18 m, or "3+ units: max 3 bedrooms"). These are in the code with a comment naming the rule. Search the `checker/` folder for the rule ID.
- A brand-new rule ID. Test **X-01c** fails and names it until a check is written for it, so you'll know.
- **RS / RT / RM:** add rules RS-01 to RS-33 numbered the same way as RD-01 to RD-33 (same meaning, that zone's numbers) and re-import. The RD checker runs them automatically. Until then, those zones say "not loaded yet".

**Another city:** make a workbook with the same tabs and run:

```bash
python3 import_workbook.py their_workbook.xlsx --city ottawa
```

That writes `data/ottawa/`. The city would also need its own `project_profiles.json`, `city.json`, `fees.json` and `translations.json` (copy Toronto's), plus checks for any rule numbering that differs.

## 3. Run the tests

```bash
python3 run_tests.py
```

This prints a pass/fail table for T-01 to T-35 (from your Test Cases tab) plus 20 extra tests I added (named X-…, or T-…-fix / -address / -diagram). It also writes `tests/results.csv` with "Actual result" and "Pass?" columns you can paste into the Test Cases tab.

Options:
- `python3 run_tests.py --step 6` runs only the tests for Build Plan steps 1 to 6.
- `python3 run_tests.py --live` runs the address tests against the real Toronto map services (needs internet). Without it, they use recorded answers so they always give the same result.

The workbook's test inputs are written as sentences. `tests/test_inputs.json` turns each one into exact form answers and expected results.

## 4. Files

| File / folder | What it is |
|---|---|
| `app.py` | The local web server. Shows the page and passes your answers to the checker. |
| `import_workbook.py` | Re-imports the workbook into `data/toronto/`. |
| `run_tests.py` | Runs the tests. |
| `checker/fields.py` | Every form question (the "contract" the AI plan reader will fill later). |
| `checker/engine.py` | Runs everything in order and builds the report. |
| `checker/permit.py` | Step 3: does it need a permit? (P-) |
| `checker/zoning.py` | Steps 4, 5, 19: RD, R and general rules (RD-, R-, G-), plus RS/RT/RM. |
| `checker/suites.py` | Step 6: garden, laneway and secondary suites, provincial overrides (GS-, LS-, SS-, ON-) |
| `checker/multiplex.py` | Step 7: houseplex rules (RD-29 to RD-32, G-38) |
| `checker/building_code.py` | Step 8: Building Code basics (BC-), always "needs human check" |
| `checker/approvals.py` | Step 10: other approvals and the grey-property STOP (AP-) |
| `checker/extras.py` | Step 11: pre-filled permit application fields, rules-not-checked list |
| `checker/fixit.py`, `variance.py` | Steps 12 and 13 |
| `checker/lookup.py` | Step 14: address lookup |
| `checker/diagram.py`, `costs.py`, `language.py`, `tracker.py` | Steps 15 to 18 |
| `checker/whatcan.py` | "What can I build?": the rules in reverse, then double-checked by the checker. |
| `checker/compare.py` | What-if comparison of 2 to 3 designs. |
| `checker/roadmap.py`, `data/toronto/roadmap.json` | Permit roadmap: checklist, inspections, timeline (from City of Toronto pages). |
| `checker/warnings.py`, `data/toronto/rejection_warnings.json` | Common rejection warnings (City sources) and the Toronto wait time for the project. |
| `tools/build_stats.py` → `data/toronto/permit_stats.json` | Toronto permit wait times from the City's open data (cleared + active permits). |
| `tools/build_glossary.py` → `data/toronto/glossary.json` | By-law dictionary from Chapter 800. |
| `checker/plan_reader.py` | **AI plan reader (step 20).** Description → suggested answers. Code checks every suggestion; you tick the ones to keep. |
| `checker/ai_client.py` | The only file that talks to the AI. Reads the key from `.env`, keeps spending under the budget, records every cost in `data/ai_spending.json`. |
| `checker/drawing_reader.py` | AI drawing reader: numbers, City checklist, conflicts (code double-checks). |
| `checker/chat.py` | The chatbot. Its tools run the real checker, the Rules Table and the dictionary. |
| `checker/vibes.py`, `data/toronto/design_guidelines.json` | Vibes check (step 21) and the guideline text it may quote. |
| `checker/shadow.py` | Shadow preview (step 22), plain maths. |
| `checker/ai_hooks.py` | Where the AI shows in the report. |
| `.env.example`, `requirements.txt`, `.gitignore` | AI setup: copy `.env.example` to `.env` and add your key. `.gitignore` keeps `.env` off GitHub. |
| `data/toronto/*.json` (imported) | Rules, project types, tests, sources, build plan. **Re-created by the importer.** |
| `data/toronto/project_profiles.json` | Hand-written: which questions and rule groups each project type uses. |
| `data/toronto/city.json` | Hand-written: by-law version dates and known amendments (step 18). |
| `data/toronto/fees.json` | Hand-written: 2026 permit fees and review times (step 16). Update every January. |
| `data/toronto/translations.json` | Hand-written: simple-English wording and FR / ES / 简体中文 translations (step 17). |
| `web/index.html`, `app.js` | The main page: home, the 5 steps and the results. |
| `web/guide.js` | The "How to use" guide that pops up the first time. |
| `web/common.js`, `style.css` | Shared display code and colours (light and dark mode). |
| `web/report.html` | The printable report. |
| `web/projects.js`, `examples.json` | My projects (save, open, backup) and the three example projects. |
| `tests/test_inputs.json` | Exact inputs and expected results for each test. |

## 5. The AI features (steps 20 to 22) and the $5 limit

On step 1, write what you're building (with sizes if you know them) and press **Read my description**.
The AI suggests answers. Each one shows the words it came from. You tick the ones that are right, and only
those go into the form. The rules then decide PASS or FAIL, exactly as before. The AI never decides.

Code checks every AI suggestion before you see it:
- it must be a real question in `checker/fields.py`
- numbers must be numbers, yes/no must be yes or no, choices must match the form exactly (otherwise it's dropped)
- the quoted words must really be in your description (otherwise it's shown with a ⚠ and left unticked)

**Set up (once):**
1. Install the AI library:
   ```bash
   pip3 install -r requirements.txt
   ```
2. Get an API key at console.anthropic.com → API keys.
3. In the project folder, copy `.env.example` to a new file called `.env` and paste the key after `ANTHROPIC_API_KEY=`.
4. Restart the app. The AI box on step 1 shows how much of the budget is left.

**Never paying more than $5, two layers:**
1. **On console.anthropic.com (the real guarantee):** buy only $5 of credit and leave **auto-reload OFF**.
   Anthropic can't charge more than the credit you bought.
2. **In the app:** `checker/ai_client.py` adds up the real cost of every request in `data/ai_spending.json`.
   Before each request it works out the most that request could cost, and refuses if it would go over
   `AI_BUDGET_USD` (5.00 in `.env`). It uses the cheap model, Claude Haiku 5.5: one read costs about $0.001,
   so $5 is roughly 5,000 reads.

The description is sent to Anthropic to be read, so the page asks people to leave out names and phone numbers.
The key stays on your computer: it's never sent to the web page, and `.gitignore` keeps `.env` off GitHub.

### The other AI features

| Feature | Where | What code checks | Rough cost |
|---|---|---|---|
| **Drawing reader** | Step 1, "From your drawings" | Values must be real questions with sensible values; only checklist items we asked about; code compares drawing numbers with your form and lists every difference. Numbers start **unticked**: you look at your drawing, then tick. | about $0.01 per set (Haiku) |
| **Chatbot** | "Ask about my project" button, bottom right | "What if" questions run the **real checker** (the reply shows the checker's own result). Rule IDs come from the results. "Approved"/"safe" get a reminder added. Offered answers are buttons you tap. | about $0.001–0.003 per question |
| **Vibes check** (step 21) | Results page | Each comment must quote a guideline that applies to the project, word for word from `data/toronto/design_guidelines.json`; others are dropped. Opinions only. | about $0.002 |
| **Shadow preview** (step 22) | Results page | Plain maths (Toronto's sun angles), no AI, free. | $0 |

Uploaded files aren't saved: they're sent to Anthropic for one read. Only the AI's short summary and checklist
are kept in your browser, so the chatbot and the printable report can use them ("Forget these drawings" removes them).
To use a stronger model just for drawings, set `AI_DRAWING_MODEL=claude-sonnet-5-5` in `.env` (about 20× the price).

**Tested with the real AI (November 18, 2026), Claude Haiku 5.5:** description read $0.0009, drawing read $0.0017,
chat question with a "what if" $0.0016, vibes check $0.0006. All four worked end to end. The automated tests use a
pretend AI, so running them never costs anything.
The notes at the top of `checker/ai_hooks.py` say where each one plugs in.

## 6. The public website (GitHub + Render)

The code is on GitHub, and Render (a free host) runs it as a public website. `render.yaml` tells Render how.

- **Your API key is never on GitHub.** `.gitignore` keeps `.env` out. On Render, the key is a secret setting
  you paste on Render's website (Environment → `ANTHROPIC_API_KEY`).
- **Limits so strangers can't use up your $5** (only on the public site, set in `render.yaml`):
  - 15 AI requests per visitor per day (`AI_VISITOR_DAILY`)
  - $0.50 of AI spending per day for the whole site (`AI_SITE_DAILY_USD`)
  - the app's own $4.90 guard (`AI_BUDGET_USD`)
  - The free host forgets these counts when it restarts, so the **$5 credit with auto-reload OFF** on
    console.anthropic.com stays the real hard limit.
- **Projects** are saved in each visitor's own browser, so nobody sees anyone else's.
- **Updating the site:** change the code, then in GitHub Desktop: Commit → Push. Render rebuilds by itself in a few minutes.
- The free plan sleeps after 15 minutes with no visitors, so the first visit after that takes about a minute to wake up.
- Not on GitHub (kept on your computer): `.env`, your AI spending record, your voice recording and the demo video.
