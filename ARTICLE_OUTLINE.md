# Article outline: Toronto Low-Rise Permit Checker

Jot notes for the article. Same kinds of sections as the fence article, but new content. Every number here comes from the build (see ARTICLE_NOTES.md for more detail).

---

## 1. Hook (a short story)
- Picture this: you want a garden suite for your parents. You hire someone to draw plans, you apply, and you wait.
- Months later, the application comes back because it's missing a form, or a setback is 0.3 m too small.
- Real numbers from the City's own open data (55,169 low-rise permits since 2017):
  - The law gives the City **10 business days** to review a complete house application.
  - A garden or laneway suite typically takes **69 days** from application to permit.
  - Only **4%** are issued within two weeks, and **39%** take over 90 days.
- The City says missing items are the **most common cause of delays**, and the zoning and tree forms are "frequently overlooked."
- Your point: a lot of that waiting is avoidable if people could check their plans before they apply.

## 2. Intro: from fences to whole homes
- Last build: a fence checker. One by-law (Chapter 447), 24 rules, no AI.
- This build is much bigger: a pre-check for almost any low-rise home project in Toronto.
  - **16 project types:** sheds, decks, additions, garden suites, laneway suites, basement apartments, multiplexes, new houses and more.
  - **174 rules:** Zoning By-law 569-2013, key Ontario Building Code rules, and other approvals (heritage, trees, TRCA).
- **And something new:** this is the first time I added real AI to a build.

## 3. What I replicated and why
- Remind readers of CivCheck and Symbium in 1 or 2 lines each (don't repeat the whole fence article).
- **Last time:** I took the *idea* of a pre-check from CivCheck and the *method* (rules turned into code) from Symbium. I skipped CivCheck's AI plan review because it cost money.
- **This time:** I actually tried CivCheck's AI part. The drawing reader reads uploaded plans, checks them against the City's submission checklist, and spots places where drawings disagree.
- I kept Symbium's idea as the backbone: the rules still live in a table and code decides PASS/FAIL.
- The printable report is modelled on the City's own **Zoning Applicable Law Certificate** pre-check.
- (Optional) If you add another company, double-check its facts first.

## 4. The scope
- **One city:** Toronto. **One kind of building:** low-rise homes.
- Residential zones R and RD first. RS, RT and RM are ready in the code but have no rules loaded yet.
- **What it doesn't do:**
  - site-specific exceptions (it warns instead)
  - commercial zones like CR (found in testing; see section 9)
  - approving anything
- **Why this scope:** low-rise homes are where homeowners apply without a professional team, and where mistakes cost the most time.

## 5. How it works (the user's steps)
- **Step 1: Pick your project.** Tap a project type. You can also let the AI fill in the form for you (section 7).
- **Step 2: About the property.** Type the address and the tool looks up the City's zoning map. That fills in the zone, height limits, heritage district, ravine/TRCA area, and whether the lot is grey (still under an old by-law).
- **Steps 3 and 4: Measurements.** You only get the questions that matter for your project type. Big Yes / No / Don't know buttons.
- **Step 5: Results.** Every rule shows:
  - PASS, FAIL, NEED MORE INFO or FLAG
  - the limit, your number, the rule ID and the by-law section
  - a confidence level
  - **Fix-it:** a FAIL tells you the smallest change that passes ("Shorten it by 0.8 m").
- **The report:** one click gives a printable report labelled "Draft pre-check for review. Not an approval."

## 6. All the other features (don't skip these)
Group them so it doesn't read like a list. One or two lines each.
- **Before you design:**
  - **What can I build?** The rules run backwards to show the biggest addition, garden suite, laneway suite or multiplex your lot allows. Then each design is run through the normal checker to prove it passes.
  - **Toronto permit stats** from the City's open data (the 69-day number).
- **While you design:**
  - **Compare designs:** 2 or 3 versions side by side (e.g. a 1.4 m deck needs a variance, a 1.1 m deck doesn't).
  - **Buildable-area diagram:** your lot drawn to scale.
  - **Shadow preview:** how far your building's shadow reaches on March 21, June 21 and December 21. Plain sun maths, no AI.
- **Before you apply:**
  - **Permit roadmap:** the drawings and forms to submit, tick-off checklist, inspection stages, timeline.
  - **Avoid getting sent back:** common rejection reasons, from the City's own pages.
  - **Cost and timeline estimate** from the City's 2026 fee schedule.
  - **Minor variance path:** what to do if you fail a rule.
- **Easy for everyone:**
  - plain-language **by-law dictionary** (47 terms, hover to see the meaning)
  - Simple words (grade 8 reading level)
  - French, Spanish and Chinese
  - Homeowner vs Designer mode
  - dark mode, bigger text, keyboard and screen-reader support
  - a "How to use" guide
- **My projects:** save several projects, each with an ID (like the fence checker). Download a backup.

## 7. The AI part (the new thing I tried, so make this a big section)
- **Why I avoided AI last time:** it costs money per use, and I didn't want AI deciding if something is legal.
- **What changed:** I found a way to use AI without letting it decide. My golden rule: **AI reads and explains, code decides.**
- **The 4 AI features** (using Claude Haiku, Anthropic's cheapest model):
  1. **Read my description:** write your project in plain words and the AI fills in the form. Each answer shows the exact words it came from, and code checks those words really are in what you wrote. You tick the ones to keep.
  2. **Read my drawings:** upload site plans or photos. The AI reads the numbers, checks the drawings against the City's checklist, and flags missing drawings or a missing signature. Code compares every number with your form itself. Drawing numbers start unticked, so you have to look.
  3. **Chatbot ("Ask about my project"):** explains your results. For "what if" questions, it runs the real checker instead of guessing. Example: "What if I move the suite to 1.5 m?" → two rules went FAIL → PASS, and it said the suite still fails on green space.
  4. **Vibes check:** opinions on whether the design fits the neighbourhood. Each one must quote Toronto's Official Plan word for word, and code throws out any quote that isn't real. Opinions never change a PASS or FAIL.
- **Keeping it cheap (the $5 challenge):**
  - I only wanted to spend $5. I bought $5 of credit with auto-reload off, so it can't charge more.
  - The app also has its own budget guard: before every request it works out the most that request could cost, and refuses if it would go over $5.
  - **Real costs:** a description read is about $0.001, a drawing read about $0.002. All my testing together cost about **1.4 cents**.
- **What I learned about AI:**
  - What an API key is, and why it must never be shared or put on GitHub.
  - The AI makes mistakes (examples in section 9), which is exactly why code checks it.
  - The tests use a pretend AI, so running them costs nothing.

## 8. The build process
- **Phase 1: plan before code.** Like last time, I started with a workbook, but much bigger:
  - Sources (every by-law and City page)
  - 16 project types
  - 174 rules, each with a limit, section, confidence level and link
  - **I checked every one of the 174 rules against the by-law and Building Code PDFs myself** before trusting it (like the fence checker, but 7 times as many rules)
  - 35 test cases
  - a 23-step build plan
  - "golden rules," e.g. missing info is never a PASS, grey properties stop all checks, and safety results always say "a qualified designer must confirm"
- **Phase 2: the brain.** Claude Code built it one step at a time from the build plan, running every test after each step.
- **Phase 3: making it a real tool.** Address lookup from City open data, the 5-step design, the guide, the report.
- **Phase 4: AI.** Added last, on purpose, once the rules worked without it.
- **Size:** about 8,000 lines of code (Python, JavaScript, HTML, CSS). Compare with the fence checker.
- Something honest about how it felt (like "I had no idea what I was doing" last time). What was easier the second time?

## 9. Testing and results
- **Automated tests:** 62 of 62 pass. These are all 35 workbook test cases plus 27 extra.
- **Real places:**
  - Toronto City Hall came back as a grey property, so the tool stopped all checks, as it should.
  - Riverdale Farm came back inside a heritage district.
- **Three made-up projects run on the real site:**
  - a rear addition (1 rule fails: building depth)
  - a garden suite read from an uploaded drawing (3 fail)
  - a deck in the Cabbagetown heritage district
- **The big find (your "0 passed" story from last time):** the deck's address (200 Carlton St) is in a **CR (commercial residential) zone**. The tool still gave it house-zone results with no warning. The code was "working," but the answer could mislead someone. Now it removes those results and says the zone is outside its scope. Only real testing caught it.
- **AI mistakes found by testing:**
  - The AI used the *addition's* size as the *whole house's* size. Fixed with clearer instructions.
  - The vibes check said the air conditioner was by the side lot line, but it was in the back yard. The AI was seeing "Where is it?" without knowing it was about the air conditioner.
  - The drawing reader repeated answers already in the form as if they were new.
- **Data trap:** the first permit stats made garden suites look super fast (24 days in 2026), because slow permits were still open and missing from the data. Adding the active-permits data fixed it.
- **Disagreements between the workbook and the rules** were flagged, not changed (e.g. a 15 m² shed matches two opposite rules).

## 10. From my laptop to a real link
- Last time: Pyodide + Netlify, so everything ran in the browser.
- This time is different, because the AI needs a secret key that can't go in the browser. It needs a real server that keeps the key hidden.
- Projects still save in each visitor's own browser, so nobody sees anyone else's.
- Limits so strangers can't spend all the $5:
  - 15 AI requests per visitor per day
  - $0.50 of AI spending per day for the whole site
  - the $5 credit with auto-reload off is still the real hard limit (the free host forgets its counts when it restarts)
- The key lives in the host's secret settings, never in the code on GitHub. Before publishing, I scanned every file for keys and personal info.
- Free hosting trade-off: the site sleeps when nobody uses it, so the first visit takes about a minute.
- **The link:** https://toronto-permit-checker.onrender.com (code: github.com/kavya12274/toronto-permit-checker)
- Testing found one more bug after it went live: the per-visitor limit wasn't counting, because the host passes visitors' addresses differently than on my laptop. Fixed and re-tested (and a faked address gets blocked).
- First live AI request cost $0.0008.
- How it felt when it went live: (your words)

## 11. Limitations and ethics
- **Not an approval.** Only the City can confirm zoning or issue a permit.
- **The AI can be wrong.** That's why it never decides, quotes are checked, and you confirm everything.
- **Privacy:**
  - What gets sent to the AI, and only when you press a button.
  - The page asks you to leave out names and phone numbers.
- **Over-reliance:** a confident-looking report might make people skip a professional. That's why safety results always say "a qualified designer must confirm."
- **Translations** were written without AI and haven't been checked by fluent speakers.

## 12. What's next
- Fill in the last Building Code rules (BC-06 to BC-11, still reminders).
- Add the RS, RT and RM zones (the code is ready).
- Past Committee of Adjustment decisions, to show how often similar variances get approved.
- Test with real homeowners and designers.
- Other cities (the rules live in a table, like the fence checker).

## 13. Conclusion
- Every answer comes from rules I verified against the by-law myself (all 174).
- **Main lesson:** the hardest part of adding AI wasn't making it work. It was deciding what it's **not** allowed to do.
- AI is great at reading messy things (descriptions, drawings) and explaining. Code is better at following the law exactly. Using both, with clear jobs, worked better than either alone.
- Tie back to the hook: it can't approve anything, but it can catch the mistake that would have sent your application back.

---

## Pictures to include
- The home page
- The AI "Fill in the form for me" box with suggestions and their quotes
- A results page with a FAIL and its fix-it
- The drawing reader's checklist and "things that don't match"
- The chatbot answering a "what if"
- The shadow preview
- "What can I build?"
- The printable report
- The cost line ("This cost $0.0014") to show how cheap AI is
