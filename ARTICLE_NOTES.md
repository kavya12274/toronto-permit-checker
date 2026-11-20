# Article notes: Toronto Low-Rise Permit Checker

Facts for the article, as of November 19, 2026. All Build Plan steps (1 to 22) are built. The AI parts (step 20 plan and drawing reader, chatbot, step 21 vibes check) were added November 18 and tested with a pretend AI in the automated tests, and once each with the real AI (all four worked; together they cost under half a cent). Step 22 (shadow preview) uses plain maths, no AI.

## What I built

A prototype web app that runs on a laptop. It pre-checks a low-rise residential project in Toronto (16 project types, from sheds and decks to garden suites and multiplexes) and produces a draft report:

- **Permit answer:** "Permit needed", "No building permit needed", "Need more info" or "Check with the City", with the rule that decided it (P-01 to P-12).
- **Rule-by-rule results:** zoning (By-law 569-2013, zones RD and R), suites and provincial overrides, multiplexes, Ontario Building Code basics. Each result is PASS / FAIL / NEED MORE INFO / FLAG and shows the limit, the user's value, the rule ID, the by-law section and a confidence level.
- **Other approvals checklist:** heritage, TRCA, ravine, trees, ESA, tenants, demolition and more (AP-01 to AP-19).
- **Fix-it suggestions:** for each FAIL, the smallest change that would pass, e.g. "Move the wall 0.1 m in".
- **Minor variance path:** the Committee of Adjustment steps and the four tests in Planning Act s. 45(1).
- **Address lookup:** zone label, height/storey overlay, lot coverage overlay, grey (old by-law) status, heritage district, ravine and TRCA area, from City of Toronto and TRCA open map services.
- **Buildable-area diagram:** the lot drawn to scale with the area where the house may go shaded.
- **Cost and timeline estimate:** from the City's 2026 permit fee schedule and the legal review timelines.
- **Simple words and translation:** grade-8-or-lower sentences, plus French, Spanish and Simplified Chinese, without AI.
- **By-law version tracker** on every report.
- **"What can I build?" calculator:** you enter the lot and the same rules run backwards to show the biggest house or addition, garden suite, laneway suite and multiplex allowed. Then each biggest design is run through the normal checker to prove it passes. On the first try, this caught that a 10 m lot is under the 12 m minimum for a brand-new house, though fine for an addition, and the tool now says so.
- **What-if comparison:** two or three designs side by side. For example, a 1-storey garden suite passes with about $1,722 in fees, while a 2-storey one needs a minor variance and costs about $2,557.
- **Permit roadmap:** the drawings and forms to submit (from the City's Small Residential Additions guide and Chapter 363 s. 363-3.5), the City's 11 inspection stages for houses, and a timeline from idea to closed permit that adds a variance or other approvals when the results call for them.
- **Toronto permit stats (evidence for the problem):** from the City's own open data on 55,169 low-rise permits issued since 2017 (cleared and active permits combined, data to Nov 13, 2026).
  - The law gives the City 10 business days to review a complete house application, but from application to permit a garden or laneway suite typically takes **69 days**. Only **4%** are issued within two weeks, and **39%** take over 90 days.
  - New houses typically take 55 days and additions 37.
  - Garden and laneway suites are getting faster: about 100 days in 2019, 64 in 2025.
  - The measure counts calendar days, including time applicants spend fixing incomplete applications. That's exactly the problem this tool targets.
- **Common rejection warnings:** the City says missing submission items are the most common cause of permit delays, and that the zoning and tree declaration forms are "frequently overlooked" (BuildSafeTO). Each project gets those warnings plus its own: zoning fails, other approvals first, and missing measurements. Each warning shows its source.
- **By-law dictionary:** 47 terms, 41 with the official Chapter 800 definition, all explained in plain words. Shown as hover/tap tooltips across the tool, plus a searchable page.
- **AI plan reader (step 20):** describe the project in plain words and Claude Haiku 5.5 suggests form answers, each with the exact words it came from. Code checks every suggestion (real question, sensible value, quote really in the text) and the user ticks the ones to keep. The rules still decide PASS/FAIL. One read costs about $0.001, and a budget guard stops requests before $5 is spent.
- **AI drawing reader:** upload PDFs or photos of drawings. The AI reads dimensions, checks the drawings against the City's submission checklist for the project, and lists mismatches between sheets. Code drops impossible values and compares every drawing number with the form itself. Drawing numbers start unticked: the user looks, then ticks.
- **Chatbot ("Ask about my project"):** explains the results in plain words. For "what if" questions it calls the real checker as a tool, and the reply shows the checker's own result, so the AI never decides PASS/FAIL.
- **Vibes check:** 3 to 6 opinions on how the design fits the neighbourhood. Each must quote Official Plan policy 4.1.5 or 4.1.9 (checked word for word by code) or a clearly labelled summary of City guidance.
- **Shadow preview:** how long the building's shadow is at 9 am, noon and 3 pm on March 21 (the date Toronto's shadow studies use), plus June and December noon. Standard sun-angle maths for Toronto's latitude, no AI.
- **Two modes:** Homeowner (plain words, essentials, folded sections) and Designer (every number and section reference in one table, all questions open, CSV/JSON export).
- **Easy to use:**
  - a home page, a 5-step walkthrough with a progress bar, and a "How to use" guide that pops up the first time
  - big Yes / No / Don't know buttons
  - "Answer this question" links from missing-info results
  - summary tiles that filter the results
  - soft colours, dark mode, a Bigger text switch, and keyboard and screen-reader support
- **Printable report** modelled on the City's Zoning Applicable Law Certificate pre-check, with pre-filled permit application fields, the vibes check, shadow preview and drawing check if you ran them. It is labelled "Draft pre-check for review. Not an approval."

## How it works

- **The spreadsheet is the source of truth.** A planning workbook holds 174 rules, each with an ID, a limit, a section, a confidence level and a link. A small import script turns it into JSON data files. The app reads the rules from those files, not from the code. A test proves it: changing RD-18's limit in the data changes the result with no code change.
- **Code decides, not AI.** Each rule group is a small Python function that compares the user's number with the limit from the data. The app runs only on the user's computer (a local web page). Nothing needs installing for the checker itself. The AI is used only when the user presses an AI button: to read a description or drawings into suggested answers, to explain results (the chatbot runs the real checker for what-ifs), and to give vibes-check opinions.
- **Missing information is never a pass.** A blank answer is NEED MORE INFO and the result names the missing question. Overlay values (HT, ST, lot coverage, f/a/d/u) are asked for, read from the zone label, or looked up.
- **Never guess.** A grey property (still under an old by-law) stops all checks and tells the user to contact Toronto Building. A site-specific exception (x###) on the zone label shows a warning. A zone with no rules loaded (RS/RT/RM) asks for rules instead of borrowing RD's.
- **Safety stays human.** Every Building Code result is marked "Needs human check" and says "A qualified designer must confirm." The tool never says "safe" or "approved".
- **AI on top, not inside.** The form is defined in one list of questions, so the AI readers can only fill in those same answers, which the user confirms. Code checks every AI output (real question, sensible value, quote really in the source) before the user sees it.

## Build process

- I wrote the planning workbook first: sources, 16 project types, 174 rules, 35 test cases and a 23-step build plan.
- Claude Code built the app step by step following the Build Plan. After each step it ran all the tests so far and fixed failures before moving on.
- Tech: Python 3 standard library only (web server, spreadsheet reading, web requests), plain HTML/JavaScript for the page, and SVG for the diagram.
- Rough size: about 8,000 lines of Python, JavaScript, HTML and CSS (including comments), plus the data files. The AI features use Anthropic's Python library and Claude Haiku 5.5.

## Testing and results

- **62 of 62 automated tests pass:** all 35 test cases from the workbook (T-01 to T-35) plus 27 extra tests added during the build:
  - rules really come from the data
  - every one of the 174 rules has code that checks it (this caught 3 missing rules: G-01, GS-14 and LS-11)
  - rules that need unusual answers really run
  - every result in all 16 project types has a status, section and confidence
  - the report has the draft label and citations
  - the fix-it for T-05
  - T-28/29/30 from an address alone
  - the diagram matches T-06 (12.0 m buildable width)
  - the fee for a sample addition
  - the reading level is grade 8 or lower
  - the by-law version date
  - RS/RT/RM behave safely
  - plugging in RS rules works
  - the AI plan reader, using a pretend AI so tests cost nothing: bad values are dropped, made-up quotes are left unticked, and the T-05 description ends in the expected RD-18 FAIL
  - the budget guard: with $4.9999 of $5 spent, the next AI request is never sent
  - the drawing reader (pretend AI): bad values dropped, form/drawing differences found by code, wrong file types stopped before sending
  - the chatbot (pretend AI): "what if 0.9 m" runs the real checker and RD-18 goes FAIL → PASS; "approved" gets a reminder
  - the vibes check (pretend AI): made-up quotes and guidelines that don't apply are dropped
  - the shadow preview: a 5 m garden suite casts about 4.8 m at noon on March 21 and 11.8 m on December 21
- **Real AI check (Nov 18):** one real run of each AI feature on Claude Haiku 5.5. The description reader filled 7 answers correctly; the drawing reader read every dimension off a test site plan, found the 0.8 vs 0.9 m mismatch and flagged the missing drawings and signature; the chatbot ran the real checker for "what if 0.9 m" (RD-18 FAIL → PASS) and said it isn't a pass yet; the vibes check gave 5 comments, all with exact Official Plan quotes. Mistake found: the AI used the addition's size for whole-house questions, so a hint was added to the instructions (drawing numbers already start unticked).
- **Three-project site test (Nov 18):** a rear addition, a garden suite (from an uploaded drawing) and a heritage-district deck, run through every feature on the real site for about half a cent of AI. It found one real gap: a deck at an address in a CR (commercial residential) zone got house-zone results with no warning. Now zoning results are removed for zones outside the tool's scope and one clear flag says why (golden rule: never guess). Smaller fixes: the vibes check mixed up which item was in the back yard (the AI now sees each answer's field name), the drawing reader repeated form answers as "new" (code now drops values not read from a named drawing and counts matches instead), and the shadow preview now says it shows the whole house's height. The three projects are saved as examples on the new **My projects** page.
- **Live check:** the address tests also pass against the real City and TRCA services (`run_tests.py --live`).
  - Riverdale Farm (201 Winchester St) came back as inside the Cabbagetown North heritage district.
  - Toronto City Hall (100 Queen St W) came back as a grey property under the old City of Toronto By-law 438-86, so the tool stopped, as it should.

**Places where the tests and rules disagreed (flagged, not changed):**
1. **P-01 vs P-02.** P-01 says a shed of 15 m² *or more* needs a permit. P-02 says 15 m² *or less* needs none, so exactly 15 m² hits both. The tool follows P-01 and says so on the result.
2. **T-13 vs ON-02.** T-13 expects a FAIL for a 5 m tall garden suite 6 m from the house (needs 7.5 m under GS-10). ON-02 says the province may cap that distance at 4 m. The tool shows the expected FAIL plus a "Verify" FLAG. The provincial text should be read before trusting either.
3. **T-12 "PASS for FSI".** The FSI limit doesn't apply to a house with a secondary suite. The tool shows PASS with "doesn't apply" in the message, because the golden rules only allow four statuses. A separate "Not applicable" status might be clearer.
4. **T-19 and T-21** had to assume the lot has enough lane frontage (6 m). Otherwise LS-01 stops the laneway checks first.
5. **T-32** tests two different rules (RD-16 and GS-03) from two project types, so it runs as two cases.

## What went wrong (and how it was fixed)

- **A data trap in the open data.** The first stats used only "cleared" (closed) permits. Recent years looked much faster (garden suites: 24 days in 2026) because slow permits from those years are still open and not in that file. Adding the City's "active permits" dataset fixed most of this (2026 is now 46 days and still marked as a partial year). This is a good example of checking data before trusting it.
- **Simple words didn't do anything on most pages.** It only changed the results. It now changes question labels, page intros and result cards everywhere.

- **3 rules were missing.** A coverage check found 3 of the 174 rules had no code checking them: G-01 (how height is measured), and GS-14 and LS-11 (rooftop items on suites). They were added, and a test now fails if any rule in the sheet has no check.
- **A hidden crash.** Running all 16 project types through about 1,600 answer combinations found one crash: a "fix-it" for a yes/no rule (like a shed in the front yard). Fixed. One rule (RD-24) was applied but showed under the wrong rule ID. Also fixed.

- **Numbers hidden in sentences.** Many limits are in the Limit column, but some are only in "Applies when" or "Notes" (frontage bands, "3+ units: max 3 bedrooms", "max 355 mm"). Those had to go in the code, so changing them in the spreadsheet won't change the app. Fix for later: add columns for them.
- **Too many NEED MORE INFO results.** Being strict about missing information means a half-filled form shows dozens of NEED MORE INFO lines. That's honest, but it's a lot. The results page has a filter (show only FAILs, etc.) and the form shows only the relevant sections.
- **Security certificates.** Python on the Mac couldn't verify the City's website certificate (a common python.org install problem). The lookup now falls back to the Mac's built-in `curl`, which uses the Mac's certificates. Security checking is never turned off.
- **Wrong TRCA layer.** The City's map layer named "Toronto and Region Conservation Authority" only shows land TRCA owns, not the regulated area. The lookup uses TRCA's own Regulation Limit service instead.
- **Flaky server.** The City's heritage layer timed out once during testing. The lookup now retries once. If a layer still fails, it leaves that question blank and tells the user to answer by hand.
- **Reading level.** The first simple-English sentences scored up to grade 8.2 ("an electrical (ESA) permit"). Shorter words brought them under grade 8.

## Limitations and ethics

**Not an approval.** Every page and report says "Draft pre-check for review. Not an approval." Only the City can confirm zoning compliance or issue a permit.

**Verification:**
- All 174 rules were checked by hand against the by-law and Building Code PDFs, and are ticked "Verified vs PDF" in the workbook (ticked Nov 20, 2026). The report no longer shows the "unverified" warning.
- The Building Code rules BC-06 to BC-11 haven't been extracted from the Code. They show only as reminders.

**Rules the tool doesn't check yet:**
- Site-specific exceptions (Chapter 900).
- The neighbour-average front setback rule.
- Exact percentage-of-wall rules (main wall 70%, dormers).
- R-zone houseplex unit and bedroom rules (not in the Rules Table yet).

**Data and lookup:**
- The diagram assumes a rectangular lot.
- Address lookup can't find designated (Part IV) heritage properties, trees, the helicopter flightpath or lot size. TRCA's map is approximate.
- Pre-filled application fields follow the general structure of the provincial form. They need checking against the February 2026 version.

**Estimates and translations:**
- Fees are a rough estimate. Development charges and other fees aren't included, and fees change every January.
- The translations were written without an AI service and haven't been checked by fluent speakers. Rule details stay in English.

**Ethics:**
- **Privacy:** the tool runs on your own computer. Address lookup sends the typed address to the City of Toronto's map search, and only the map point to the other services. The AI plan reader sends only the description, and only when the user presses the button; the page asks people to leave out names and phone numbers. The tool doesn't collect names or contact details. The application form fields for those stay blank.
- **Over-reliance:** a confident-looking report could make people skip professional advice. That's why missing info is never PASS, safety results always need a qualified designer, every result shows its confidence, and "Verify" rules are flagged.
- **Fairness and access:** permit rules are hard to read, and professional pre-checks cost money. Simple words and translation try to widen access. The fix-it and variance sections show options, not just "no".
- **AI:** code still decides PASS/FAIL. AI only suggests form answers the user confirms, explains results, and writes vibes-check comments that must quote the City's own guidelines. A $5 budget guard and $5 of prepaid credit (auto-reload off) cap the cost.

## What's next

1. Extract BC-06 to BC-11. Read O. Reg. 299/19 to settle ON-02 and ON-03.
2. Add columns for the secondary numbers (frontage bands, bedroom limits) so all numbers live in the spreadsheet.
3. Add RS, RT and RM rules (the code is ready for them).
4. Put it online with limits so visitors can't use up the AI budget.
5. Add past Committee of Adjustment decisions from Toronto Open Data to the variance path.
6. Have fluent speakers review the translations, and test the tool with real homeowners.
