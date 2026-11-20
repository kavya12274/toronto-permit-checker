"""Step 13: the minor variance path (AP-08, Planning Act s. 45(1)).

If any zoning rule FAILs, the report explains the Committee of Adjustment route
and the four tests the Committee must find are ALL met.
The text is general information, not legal advice.
Later (Build Plan note): add past Committee of Adjustment decisions from Toronto
Open Data, e.g. "similar side-setback variances on your street".
"""

from .core import FAIL, fmt

FOUR_TESTS = [
    {"test": "Is it minor?",
     "question": "Is the change small in size and impact on neighbours (not just in numbers)?"},
    {"test": "Is it desirable?",
     "question": "Is it appropriate for the development or use of the land, building or structure?"},
    {"test": "Does it keep the intent of the zoning by-law?",
     "question": "Does it still respect what the rule is for (e.g. a side setback gives light, access and space between houses)?"},
    {"test": "Does it keep the intent of the Official Plan?",
     "question": "Does it fit the Official Plan, e.g. the Neighbourhoods policies on fitting in with the existing physical character?"},
]

STEPS = [
    "Try the fix-it suggestions first: if the design can meet the rule, no variance is needed.",
    "Get a Zoning Applicable Law Certificate or zoning review from Toronto Building listing the exact variances needed.",
    "Talk to your neighbours early: they get notice and can comment or appear at the hearing.",
    "Apply to the Committee of Adjustment for your district, with drawings and the list of variances (O. Reg. 200/96 says what an application needs).",
    "City staff (Planning, Urban Forestry, etc.) may comment. The Committee holds a public hearing and decides.",
    "After the decision there is a 20-day appeal period to the Ontario Land Tribunal (the Planning Act limits who may "
    "appeal: verify the current rules). Then apply for (or continue) the building permit.",
]


def add_to_report(ctx, report):
    fails = [r for r in report["results"] if r["status"] == FAIL and r["group"] in ("Zoning", "Suites")]
    if not fails:
        report["variance"] = None
        return
    items = []
    for r in fails:
        if r["limit"] is not None and r["value"] is not None:
            items.append(f"{r['rule_id']} ({r['section']}): {fmt(r['value'])} instead of {fmt(r['limit'])} {r['unit']}".strip())
        else:
            items.append(f"{r['rule_id']} ({r['section']})")
    report["variance"] = {
        "title": "Minor variance path",
        "rule_id": "AP-08",
        "intro": (f"{len(fails)} zoning rule(s) fail: " + "; ".join(items) + ". If you can't change the design, you can "
                  "ask the Committee of Adjustment for a minor variance. The Committee can only approve it if ALL four "
                  "tests in the Planning Act s. 45(1) are met."),
        "variances_needed": items,
        "four_tests": FOUR_TESTS,
        "steps": STEPS,
        "source": "Planning Act s. 45(1); O. Reg. 200/96. General information, not legal advice. Building Code (safety) "
                  "fails can't be fixed by a minor variance.",
    }
