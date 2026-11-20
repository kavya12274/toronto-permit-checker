"""The engine: runs every check in the right order and builds one report.

    from checker.engine import run
    report = run({"project_type": "Deck / platform", "deck_height": 0.9})

Order:
  1. Stop checks (grey property)           -> approvals.stop_check
  2. Does it need a permit?                -> permit.check
  3. Rule groups for this project type     -> GROUPS below (from project_profiles.json)
  4. Other approvals                       -> approvals.check
  5. Extras: fix-its, variance path, diagram, cost, by-law tracker, AI placeholders

Code decides PASS/FAIL. Nothing here calls an AI (golden rule 2).
"""

from . import permit
from .core import Context, PASS, FAIL, NEED, FLAG, load_city

# Group name (used in project_profiles.json) -> function that runs those rules.
# Each module adds its own groups with register().
GROUPS = {}


def register(name):
    def wrap(fn):
        GROUPS[name] = fn
        return fn
    return wrap


# Import the rule modules so they register their groups. (Order doesn't matter.)
from . import zoning, suites, multiplex, building_code, approvals   # noqa: E402,F401
from . import extras                                               # noqa: E402


def profile_for(ctx):
    profiles = ctx.data.get("project_profiles", {})
    return profiles.get(ctx.project)


def run(inputs, city="toronto"):
    ctx = Context(inputs, city)
    report = {
        "city": city,
        "inputs": ctx.inputs,
        "project_type": ctx.project,
        "label": "Draft pre-check for review. Not an approval.",   # golden rule 7
        "stopped": False,
        "permit": None,
        "results": [],
        "notes": ctx.notes,
    }

    profile = profile_for(ctx)
    if not profile:
        report["permit"] = {"answer": permit.UNKNOWN, "reason": "Pick a project type first."}
        report["notes"].append("Pick a project type to start.")
        return finish(ctx, report)

    # 1. Stop checks (golden rule 5): grey property = no checks at all
    if approvals.stop_check(ctx):
        report["stopped"] = True
        report["permit"] = {"answer": permit.UNKNOWN,
                            "reason": "Checks stopped: this property is under an old by-law."}
        return finish(ctx, report)

    # 2. Permit
    report["permit"] = permit.check(ctx, profile.get("permit", ""))

    # 3. Rule groups
    for group in profile.get("groups", []):
        fn = GROUPS.get(group)
        if fn:
            fn(ctx)

    # 3b. Not a low-rise residential zone (e.g. CR): our zoning rules don't apply there, so remove those
    #     results and say so, instead of showing a PASS or FAIL that could be wrong
    from .zoning import outside_scope
    outside_scope(ctx)

    # 4. Approvals
    approvals.check(ctx, profile)
    return finish(ctx, report)


def finish(ctx, report):
    results = ctx.results
    report["results"] = results
    report["counts"] = {s: sum(1 for r in results if r["status"] == s) for s in (PASS, FAIL, NEED, FLAG)}
    report["overall"] = overall(report)
    extras.add_extras(ctx, report)      # fix-its, variance, diagram, costs, tracker, AI placeholders
    return report


def overall(report):
    """One-line summary at the top of the report, in plain words."""
    if report["stopped"]:
        return "STOP: contact Toronto Building before going further."
    c = report["counts"]
    if any(r["rule_id"] == "ZONE" and r["status"] == FLAG for r in report["results"]):
        return "Zoning can't be checked: this zone is outside the tool's low-rise residential rules. Check with Toronto Building."

    def rules(n):
        return f"{n} rule" if n == 1 else f"{n} rules"
    if c[FAIL]:
        verb = "doesn't" if c[FAIL] == 1 else "don't"
        return f"{rules(c[FAIL])} {verb} pass. Change the design or apply for a minor variance."
    if c[NEED]:
        return f"Nothing fails so far, but {rules(c[NEED])} still need an answer, so this isn't a pass yet."
    if c[FLAG]:
        return "Nothing fails. A few items need following up."
    return "Nothing fails in the rules checked."
