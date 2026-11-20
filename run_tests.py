"""Run the Test Cases (T-01 to T-35) and print a pass/fail table.

How to run (in Terminal, from this folder):
    python3 run_tests.py            # all tests
    python3 run_tests.py --step 6   # only tests for Build Plan steps 1-6
    python3 run_tests.py --live     # also use the real Toronto map services for address tests

It also writes tests/results.csv with an 'Actual result' and 'Pass?' column
you can paste back into the Test Cases tab (Build Plan step 23).
"""

import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from checker.engine import run          # noqa: E402
from checker.core import load_city      # noqa: E402
from checker.core import fmt            # noqa: E402


def close(a, b):
    try:
        return abs(float(a) - float(b)) < 1e-6
    except (TypeError, ValueError):
        return False


def check_case(report, expect):
    """Return (passed, list of problems, short 'actual' text)."""
    problems = []
    by_rule = {}
    for r in report["results"]:
        by_rule.setdefault(r["rule_id"], []).append(r)
    actual = []

    if "permit" in expect:
        got = (report.get("permit") or {}).get("answer")
        actual.append(f"Permit: {got}")
        if got != expect["permit"]:
            problems.append(f"permit answer was '{got}', expected '{expect['permit']}'")

    if expect.get("stopped"):
        actual.append("STOPPED" if report["stopped"] else "not stopped")
        if not report["stopped"]:
            problems.append("checks were not stopped")

    for e in expect.get("results", []):
        found = by_rule.get(e["rule"], [])
        if not found:
            problems.append(f"{e['rule']} gave no result")
            actual.append(f"{e['rule']}: (none)")
            continue
        match = None
        for r in found:
            ok = r["status"] == e["status"]
            if ok and "limit" in e:
                ok = close(r["limit"], e["limit"])
            if ok and "confidence" in e:
                ok = r["confidence"] == e["confidence"]
            if ok and "message_contains" in e:
                ok = e["message_contains"].lower() in r["message"].lower()
            if ok:
                match = r
                break
        r = match or found[0]
        lim = f" (limit {fmt(r['limit'])})" if r.get("limit") is not None else ""
        actual.append(f"{e['rule']}: {r['status']}{lim}")
        if not match:
            problems.append(f"{e['rule']}: got {r['status']}{lim}, conf {r['confidence']}; expected {e}")

    for e in expect.get("not_results", []):
        if any(r["status"] == e["status"] for r in by_rule.get(e["rule"], [])):
            problems.append(f"{e['rule']} should not be {e['status']}")

    if "not_rules_prefix" in expect:
        wrong = sorted(r for r in by_rule if r.startswith(expect["not_rules_prefix"]))
        if wrong:
            problems.append("used rules from another zone: " + ", ".join(wrong))

    if "only_rules" in expect:
        extra = sorted(set(by_rule) - set(expect["only_rules"]))
        if extra:
            problems.append("other checks ran even though it should stop: " + ", ".join(extra))

    if expect.get("zoning_still_checked"):
        zoning = [r for r in report["results"] if r["group"] == "Zoning"]
        actual.append(f"{len(zoning)} zoning results")
        if not zoning:
            problems.append("no zoning results (zoning must still be checked)")

    if expect.get("all_bc_human_check"):
        bad = [r["rule_id"] for r in report["results"]
               if r["rule_id"].startswith("BC-") and r["confidence"] != "Needs human check"]
        if bad:
            problems.append("BC rules not marked 'Needs human check': " + ", ".join(bad))

    if "fix_for" in expect:
        fixes = [f for f in report.get("fixes", []) if f["rule_id"] == expect["fix_for"]]
        text = fixes[0]["text"] if fixes else "(no fix)"
        actual.append(f"Fix: {text}")
        if not fixes or expect["fix_contains"] not in text:
            problems.append(f"fix-it text was '{text}'")

    if "variance_tests" in expect:
        v = report.get("variance") or {}
        n = len(v.get("four_tests", []))
        actual.append(f"Variance path with {n} tests")
        if n != expect["variance_tests"]:
            problems.append(f"variance path had {n} tests")

    if expect.get("every_result_complete"):
        levels = {"High", "Verify", "Needs human check"}
        bad = [r["rule_id"] for r in report["results"]
               if r["confidence"] not in levels or not r["section"] or not r["rule_id"]
               or r["status"] not in ("PASS", "FAIL", "NEED MORE INFO", "FLAG")]
        actual.append(f"{len(report['results'])} results checked")
        if bad:
            problems.append("results missing confidence/section/status: " + ", ".join(bad))

    if "diagram" in expect:
        e = (report.get("diagram") or {}).get("envelope") or {}
        actual.append(f"Diagram: {e.get('build_width')} m wide x {e.get('build_depth')} m deep")
        for k, v in expect["diagram"].items():
            if not close(e.get(k), v):
                problems.append(f"diagram {k} was {e.get(k)}, expected {v}")
        if "<svg" not in (report.get("diagram") or {}).get("svg", ""):
            problems.append("no diagram drawn")

    if "cost_contains" in expect:
        text = " ".join(f"{l['item']} {l['amount']}" for l in (report.get("costs") or {}).get("lines", []))
        actual.append(f"Costs: {text[:80]}")
        if expect["cost_contains"] not in text:
            problems.append(f"cost lines don't mention '{expect['cost_contains']}'")

    if "tracker_contains" in expect:
        text = (report.get("tracker") or {}).get("summary", "")
        actual.append(f"Tracker: {text[:70]}")
        if expect["tracker_contains"] not in text:
            problems.append(f"tracker summary was '{text}'")

    if expect.get("plain_grade_max") is not None:
        grades = [r.get("plain_grade", 99) for r in report["results"] if r.get("plain")]
        worst = max(grades) if grades else None
        actual.append(f"Plain-language worst grade {worst}")
        if worst is None or worst > expect["plain_grade_max"]:
            problems.append(f"plain-language grade {worst} is above {expect['plain_grade_max']}")

    if "roadmap" in expect:
        rm = report.get("roadmap") or {}
        items = [d["item"] for d in rm.get("checklist", {}).get("drawings", []) + rm.get("checklist", {}).get("forms", [])]
        insp = [i["item"] for i in rm.get("inspections", [])]
        steps = [t["title"] for t in rm.get("timeline", [])]
        actual.append(f"Roadmap: {len(items)} items, {len(insp)} inspections, {len(steps)} steps")
        for want in expect["roadmap"].get("items", []):
            if want not in items:
                problems.append(f"checklist is missing '{want}'")
        for want in expect["roadmap"].get("inspections", []):
            if want not in insp:
                problems.append(f"inspections missing '{want}'")
        for want in expect["roadmap"].get("steps", []):
            if want not in steps:
                problems.append(f"timeline missing '{want}'")
        if expect["roadmap"].get("nothing_to_submit") and not rm.get("checklist", {}).get("none"):
            problems.append("expected 'nothing to submit'")

    if "warnings_include" in expect or "no_warnings" in expect:
        titles = [w["title"] for w in report.get("warnings", [])]
        actual.append(f"{len(titles)} warnings")
        for want in expect.get("warnings_include", []):
            if want not in titles:
                problems.append(f"missing warning '{want}'")
        if expect.get("no_warnings") and titles:
            problems.append("expected no rejection warnings (no permit needed)")
        for w in report.get("warnings", []):
            if not w.get("source_name"):
                problems.append(f"warning '{w['title']}' has no source")
    if expect.get("wait_days"):
        wait = report.get("wait") or {}
        actual.append(f"wait {wait.get('median_days')} days")
        if not wait.get("median_days"):
            problems.append("no Toronto wait time shown for this project type")

    if expect.get("data_files"):
        data = load_city("toronto")
        stats, gloss = data.get("permit_stats") or {}, data.get("glossary") or {}
        groups = stats.get("groups", [])
        actual.append(f"{len(groups)} stats groups, {len(gloss.get('terms', []))} dictionary terms")
        if len(groups) < 10:
            problems.append("permit stats has fewer than 10 project types (re-run tools/build_stats.py)")
        for g in groups:
            if not (0 <= g["p25_days"] <= g["median_days"] <= g["p75_days"]) or g["permits"] < 100:
                problems.append(f"stats look wrong for {g['name']}")
        terms = gloss.get("terms", [])
        if len(terms) < 40:
            problems.append("dictionary has fewer than 40 terms (re-run tools/build_glossary.py)")
        for t in terms:
            if not t.get("plain") or not t.get("source"):
                problems.append(f"dictionary term {t.get('term')} has no plain wording or source")
            if "Chapter 800" in t.get("source", "") and not t.get("official"):
                problems.append(f"{t['term']}: says Chapter 800 but has no official wording")

    if expect.get("coverage"):
        missing = rules_without_code()
        total = len(load_city("toronto")["rules"])
        actual.append(f"{total - len(missing)} of {total} rules have code that checks them")
        if missing:
            problems.append("rules in the sheet with no check written yet: " + ", ".join(missing))

    if expect.get("report_complete"):
        if report.get("label") != "Draft pre-check for review. Not an approval.":
            problems.append("report label is wrong")
        if len(report.get("application", [])) < 10:
            problems.append("pre-filled application fields missing")
        if not report.get("ai", {}).get("vibes_check", {}).get("text"):
            problems.append("vibes check section missing")
        if any(not r["rule_id"] or not r["section"] for r in report["results"]):
            problems.append("a result is missing its rule ID or section")
        actual.append(f"label OK, {len(report.get('application', []))} application fields, vibes check section")

    return (not problems), problems, "; ".join(actual)


def fake_fetch(layers):
    """Pretend map services for offline tests: 'layers' says which layers contain the point."""
    from checker import lookup

    def fetch(url, params):
        if url == lookup.GEOCODER:
            return {"result": {"bestResult": [{"featureClass": "Address", "latitude": 43.66, "longitude": -79.37,
                                               "key_Desc": params["searchString"], "matchType": "Exact"}]}}
        for name, layer_url in lookup.SERVICES.items():
            if url == layer_url + "/query":
                return {"features": [{"attributes": a} for a in layers.get(name, [])]}
        raise RuntimeError("unexpected url " + url)
    return fetch


def inputs_for(case, live):
    """Inputs for a test case; if the case has an address lookup, run it first (like the app does)."""
    inputs = dict(case.get("inputs", {}))
    if "lookup" in case:
        from checker import lookup
        if live and "live_address" in case:
            res = lookup.lookup_address(case["live_address"])
        else:
            res = lookup.lookup_address(case["lookup"]["address"], fetch=fake_fetch(case["lookup"]["layers"]))
        inputs.update(res["values"])
    return inputs


def plug_in_zone(spec):
    """Pretend the Rules Table has rules for a new zone (step 19 test).
    spec = {"zone": "RS", "copy_from": "RD", "limits": {"18": 1.2}} copies RD-01..33 as RS-01..33."""
    if not spec:
        return []
    data = load_city("toronto")
    added = []
    for r in list(data["rules"]):
        if r["id"].startswith(spec["copy_from"] + "-"):
            n = r["id"].split("-")[1]
            new = dict(r, id=f"{spec['zone']}-{n}", section=r["section"].replace("10.20", "10.40"))
            if n in spec.get("limits", {}):
                new["limit"] = spec["limits"][n]
            data["rules"].append(new)
            data["rules_by_id"][new["id"]] = new
            added.append(new["id"])
    return added


def override_limits(new):
    """Change rule limits in memory (as if you edited the spreadsheet and re-imported).
    Returns the old values so they can be put back."""
    rules = load_city("toronto")["rules_by_id"]
    old = {}
    for rid, value in new.items():
        old[rid] = rules[rid]["limit"]
        rules[rid]["limit"] = value
    return old


def unplug(ids):
    data = load_city("toronto")
    data["rules"] = [r for r in data["rules"] if r["id"] not in ids]
    for i in ids:
        data["rules_by_id"].pop(i, None)


def rules_without_code():
    """Rule IDs in rules.json that no checker file mentions (so they would never be checked).
    RS/RT/RM rules count as covered if the same-numbered RD rule is (they reuse the RD checker)."""
    import glob
    import re
    code = "".join(open(f, encoding="utf-8").read() for f in glob.glob(os.path.join(HERE, "checker", "*.py")))
    seen = set(re.findall(r'"((?:P|RD|R|G|SS|GS|LS|ON|BC|AP)-\d\d)"', code))
    seen |= {f"RD-{n}" for n in re.findall(r'f"\{p\}-(\d\d)"', code)}
    seen |= {f"RD-{n}" for n in range(17, 24)}          # side setback bands (side_rule_for_frontage)
    missing = []
    for r in load_city("toronto")["rules"]:
        rid = r["id"]
        prefix, num = rid.split("-")[0], rid.split("-")[-1]
        if rid in seen or (prefix in ("RS", "RT", "RM") and f"RD-{num}" in seen):
            continue
        missing.append(rid)
    return missing


def run_feature(case):
    """Tests for the calculator and comparison, which aren't single checks."""
    problems, actual = [], []
    if "whatcan" in case:
        from checker.whatcan import calculate
        out = calculate(case["whatcan"])
        if case.get("expect_stop"):
            actual.append("stopped" if out.get("stop") else "not stopped")
            if not out.get("stop"):
                problems.append("expected the calculator to stop")
            return problems, "; ".join(actual)
        kinds = {o["kind"]: o for o in out["options"]}
        actual.append("options: " + ", ".join(kinds))
        for k in case.get("expect_kinds", []):
            if k not in kinds:
                problems.append(f"no '{k}' option")
        for o in out["options"]:
            if o.get("check") and not o["check"]["passed"]:
                problems.append(f"biggest {o['kind']} design fails the checker: {o['check']['fails']}")
        for k, text in case.get("expect_headline", {}).items():
            if k in kinds and text not in kinds[k]["headline"]:
                problems.append(f"{k} headline was '{kinds[k]['headline']}'")
    if "compare" in case:
        from checker.compare import compare
        out = compare(case["compare"])
        d = out["designs"]
        actual.append(" vs ".join(f"{x['name']}: {len(x['fails'])} fails, variance {x['needs_variance']}, fee {x['fee']}" for x in d))
        for i, want in enumerate(case.get("expect_variance", [])):
            if d[i]["needs_variance"] != want:
                problems.append(f"{d[i]['name']}: needs_variance was {d[i]['needs_variance']}")
        if "expect_best" in case and out["best"] != case["expect_best"]:
            problems.append(f"best was design {out['best']}")
        if case.get("expect_fee_order") and not (d[0]["fee"] < d[1]["fee"]):
            problems.append("the bigger design should cost more in fees")
    if "plan_reader" in case:
        problems += plan_reader_test(case["plan_reader"], actual)
    for kind in ("drawing_reader", "chat", "vibes", "shadow"):
        if kind in case:
            problems += ai_feature_test(kind, case[kind], actual)
    return problems, "; ".join(actual)


class FakeAI:
    """A pretend AI for the tests: returns fixed answers, so tests never use the internet or money.
    `answer` is one reply (a dict, sent back as JSON text), or a list of replies for several rounds.
    A reply like {"tool_uses": [...]} pretends the AI asked to use our tools."""
    def __init__(self, answer):
        self.replies = answer if isinstance(answer, list) else [answer]
        self.calls, self.requests = 0, []
        self.messages = self

    def create(self, **kwargs):
        from types import SimpleNamespace as NS
        reply = self.replies[min(self.calls, len(self.replies) - 1)]
        self.calls += 1
        self.requests.append(kwargs)
        usage = NS(input_tokens=6000, output_tokens=400)
        if isinstance(reply, dict) and "tool_uses" in reply:
            blocks = [NS(type="tool_use", id=f"t{i}", name=t["name"], input=t["input"]) for i, t in enumerate(reply["tool_uses"])]
            return NS(stop_reason="tool_use", usage=usage, content=blocks)
        text = reply["text"] if isinstance(reply, dict) and "text" in reply else json.dumps(reply)
        return NS(stop_reason="end_turn", usage=usage, content=[NS(type="text", text=text)])


def ai_feature_test(kind, spec, actual):
    """Drawing reader, chatbot, vibes check (pretend AI) and the shadow preview (plain maths)."""
    import tempfile
    from checker import ai_client
    problems = []
    if kind == "shadow":
        s = run(spec["inputs"]).get("shadow")
        if spec.get("expect_none"):
            actual.append(f"shadow: {s}")
            return [] if s is None else ["expected no shadow preview for this project"]
        lengths = {t["label"]: t["length_m"] for t in (s or {}).get("times", [])}
        actual.append(f"shadow lengths {lengths}")
        for label, want in spec["expect_lengths"].items():
            if abs(lengths.get(label, -99) - want) > 0.15:
                problems.append(f"{label}: shadow {lengths.get(label)} m, expected about {want} m")
        return problems

    saved_ledger = ai_client.LEDGER
    ai_client.LEDGER = os.path.join(tempfile.mkdtemp(), "ai_spending.json")      # never touch the real spending record
    try:
        fake = FakeAI(spec.get("ai_answer", {}))
        try:
            if kind == "drawing_reader":
                from checker.drawing_reader import read_drawings
                out = read_drawings(spec["files"], spec.get("answers", {}), client=fake)
            elif kind == "chat":
                from checker.chat import chat
                out = chat([{"role": "user", "content": spec["question"]}], spec["answers"], client=fake)
            else:
                from checker.vibes import vibes_check
                out = vibes_check(spec["answers"], client=fake)
        except ai_client.AIError as e:
            actual.append(f"stopped before sending: {str(e)[:60]}")
            if not spec.get("expect_error"):
                problems.append(f"unexpected stop: {e}")
            if fake.calls:
                problems.append("a request was sent even though it should have been stopped")
            return problems
        if spec.get("expect_error"):
            return ["expected this to be stopped before sending"]
        rounds = fake.calls
        if abs(ai_client.spent() - rounds * ai_client.cost_of(ai_client.DEFAULT_MODEL, 6000, 400)) > 1e-9:
            problems.append("the cost of every AI round wasn't recorded")

        if kind == "drawing_reader":
            keys = [s["key"] for s in out["suggestions"]]
            dropped = [d["key"] for d in out["dropped"]]
            code_conflicts = [c["what"] for c in out["conflicts"] if c["by"] == "code"]
            status = {c["item"]: c["status"] for c in out["checklist"]}
            actual.append(f"suggested {keys}, dropped {dropped}, code found {len(code_conflicts)} conflict(s), "
                          f"checklist {len(status)} items ({status.get('Site plan')} site plan)")
            if keys != spec["expect_keys"]:
                problems.append(f"suggestions were {keys}")
            if dropped != spec["expect_dropped"]:
                problems.append(f"dropped was {dropped}")
            if "expect_agrees" in spec and len(out.get("agrees", [])) != spec["expect_agrees"]:
                problems.append(f"matches with the form: {out.get('agrees')}")
            if not any(spec["expect_code_conflict"] in c for c in code_conflicts):
                problems.append("code didn't spot the form/drawing difference")
            if "Bogus item" in status:
                problems.append("a checklist item we didn't ask about got through")
            for item, want in spec["expect_checklist"].items():
                if status.get(item) != want:
                    problems.append(f"checklist {item}: {status.get(item)}")
            doc = [b for b in fake.requests[0]["messages"][0]["content"] if b.get("type") == "document"]
            if doc and any(k.startswith("_") for k in doc[0]):
                problems.append("our private '_pages' note was sent to the API")

        if kind == "chat":
            w = out["what_ifs"][0] if out["what_ifs"] else {}
            changed = {c["rule_id"]: (c["before"], c["after"]) for c in w.get("changed", [])}
            actual.append(f"{rounds} AI rounds, tools {out['tools_used']}, checker said {changed}, "
                          f"{len(out['suggestions'])} answer button(s)")
            for rule, (b, a) in spec["expect_changed"].items():
                if changed.get(rule) != (b, a):
                    problems.append(f"{rule}: what-if gave {changed.get(rule)}, expected {b} -> {a}")
            if len(out["suggestions"]) != spec["expect_suggestions"]:
                problems.append(f"{len(out['suggestions'])} answer buttons")
            if spec.get("expect_reminder") and "not an approval" not in out["reply"]:
                problems.append("the 'not an approval' reminder wasn't added")
            if "RD-18" not in fake.requests[0]["system"]:
                problems.append("the AI wasn't given the project's results")

        if kind == "vibes":
            got = [(c["guideline_id"], c["tone"]) for c in out["comments"]]
            actual.append(f"kept {got}, dropped {len(out['dropped'])}")
            if [g for g, _ in got] != spec["expect_kept"]:
                problems.append(f"kept {got}")
            if len(out["dropped"]) != spec["expect_dropped"]:
                problems.append(f"dropped {len(out['dropped'])}")
            if spec.get("expect_reminder") and not any("not an approval" in c["comment"] for c in out["comments"]):
                problems.append("the 'not an approval' reminder wasn't added")
    finally:
        ai_client.LEDGER = saved_ledger
    return problems


def plan_reader_test(spec, actual):
    """AI plan reader: code checks the AI's suggestions, confirmed answers go to the normal checker,
    and the budget guard stops requests before going over the limit."""
    import tempfile
    from checker import ai_client
    from checker.plan_reader import read_plan
    problems = []
    saved_ledger = ai_client.LEDGER
    ai_client.LEDGER = os.path.join(tempfile.mkdtemp(), "ai_spending.json")      # never touch the real spending record
    try:
        if spec.get("start_spent") is not None:
            with open(ai_client.LEDGER, "w") as f:
                json.dump({"total_usd": spec["start_spent"], "requests": []}, f)
        fake = FakeAI(spec["ai_answer"])
        try:
            out = read_plan(spec["description"], client=fake)
        except ai_client.AIError as e:
            actual.append(f"stopped before sending: {str(e)[:50]}...")
            if not spec.get("expect_blocked"):
                problems.append(f"unexpected stop: {e}")
            if fake.calls:
                problems.append("the request was sent even though it was blocked")
            return problems
        if spec.get("expect_blocked"):
            return problems + ["expected the budget guard to stop the request"]
        ticked = {s["key"]: s["value"] for s in out["suggestions"] if s["quote_found"]}
        unticked = [s["key"] for s in out["suggestions"] if not s["quote_found"]]
        dropped = [d["key"] for d in out["dropped"]]
        actual.append(f"ticked {sorted(ticked)}, unticked {unticked}, dropped {dropped}, cost ${out['cost']['cost_usd']}")
        for k, v in spec.get("expect_ticked", {}).items():
            if ticked.get(k) != v:
                problems.append(f"{k}: expected {v}, got {ticked.get(k)}")
        if sorted(unticked) != sorted(spec.get("expect_unticked", [])):
            problems.append(f"unticked was {unticked}")
        if sorted(dropped) != sorted(spec.get("expect_dropped", [])):
            problems.append(f"dropped was {dropped}")
        expected_cost = ai_client.cost_of(ai_client.DEFAULT_MODEL, 6000, 400)
        if abs(ai_client.spent() - (spec.get("start_spent") or 0) - expected_cost) > 1e-9:
            problems.append("the cost wasn't added to the spending record")
        if spec.get("expect_results"):                    # the user confirms the ticked answers, then the rules decide
            report = run(ticked)
            ok, more, text = check_case(report, {"results": spec["expect_results"]})
            actual.append(text)
            problems += more
    finally:
        ai_client.LEDGER = saved_ledger
    return problems


def special_cases(kind):
    if kind == "data_files":
        return [{"inputs": {}, "expect": {"data_files": True}}]
    if kind == "coverage":
        return [{"inputs": {}, "expect": {"coverage": True}}]
    """Builder-added tests that loop over every project type."""
    if kind == "all_project_types":
        types = [t["Project type"] for t in load_city("toronto")["project_types"]]
        sample = {"zone": "RD", "lot_frontage": 10, "lot_depth": 30, "building_type": "Detached house",
                  "side_setback": 0.5, "height": 11, "anc_area": 20, "deck_height": 1.0,
                  "gs_height": 5, "gs_to_house": 5, "lane_frontage": 5, "ls_length": 12,
                  "ss_floor_pct": 60, "proposed_units": 3, "existing_units": 1, "has_bedroom": True,
                  "egress_sill": 1200, "driveway_width": 8, "solar_above_height": 2}
        return [{"inputs": dict(sample, project_type=t), "expect": {"every_result_complete": True}} for t in types]
    if kind == "new_zones":
        # Every project type in RS, RT and RM with no rules loaded: must ask, never crash or guess.
        types = [t["Project type"] for t in load_city("toronto")["project_types"]]
        cases = []
        for z in ("RS", "RT", "RM"):
            for t in types:
                inp = dict(special_cases("all_project_types")[0]["inputs"], project_type=t, zone=z)
                exp = {"every_result_complete": True}
                if t == "Rear addition (1 or 2 storey)":
                    exp["results"] = [{"rule": "ZONE", "status": "NEED MORE INFO", "message_contains": f"Zone {z} is not loaded yet"}]
                    exp["not_rules_prefix"] = "RD-"
                cases.append({"inputs": inp, "expect": exp})
        return cases
    if kind == "all_project_types_plain":
        return [dict(c, expect={"plain_grade_max": 8}) for c in special_cases("all_project_types")]
    return []


def main():
    step = None
    live = "--live" in sys.argv          # use the real map services for address-lookup tests
    if "--step" in sys.argv:
        step = int(sys.argv[sys.argv.index("--step") + 1])

    with open(os.path.join(HERE, "tests", "test_inputs.json"), encoding="utf-8") as f:
        tests = json.load(f)
    tests.pop("_about", None)
    workbook = {t["Test ID"]: t for t in load_city("toronto")["test_cases"]}

    def sort_key(tid):
        base = tests[tid].get("test_id", tid)
        return (tests[tid]["step"], base, tid)

    rows, failures = [], 0
    for tid in sorted(tests, key=sort_key):
        t = tests[tid]
        if step is not None and t["step"] > step:
            continue
        base_id = t.get("test_id", tid)
        wb = workbook.get(base_id, {})
        all_ok, all_problems, actual_texts = True, [], []
        cases = t.get("cases", []) + special_cases(t.get("special", ""))
        for case in cases:
            if any(k in case for k in ("whatcan", "compare", "plan_reader", "drawing_reader", "chat", "vibes", "shadow")):
                problems, actual = run_feature(case)
                all_ok &= not problems
                all_problems += problems
                actual_texts.append(actual)
                continue
            added = plug_in_zone(case.get("plugin_zone"))
            saved = override_limits(case.get("override_limits", {}))
            report = run(inputs_for(case, live))
            override_limits(saved)
            unplug(added)
            ok, problems, actual = check_case(report, case["expect"])
            all_ok &= ok
            all_problems += problems
            actual_texts.append(actual)
        failures += 0 if all_ok else 1
        rows.append({"id": tid, "step": t["step"], "scenario": wb.get("Scenario", "") or t.get("scenario", ""),
                     "expected": wb.get("Expected result", ""), "actual": " | ".join(actual_texts),
                     "pass": all_ok, "problems": all_problems})

    # Print the table
    print(f"\n{'Test':<13} {'Step':<5} {'Result':<7} Scenario")
    print("-" * 70)
    for r in rows:
        print(f"{r['id']:<13} {r['step']:<5} {'PASS' if r['pass'] else 'FAIL':<7} {r['scenario']}")
        if not r["pass"]:
            for p in r["problems"]:
                print(f"{'':<27}-> {p}")
    print("-" * 70)
    print(f"{len(rows) - failures} of {len(rows)} tests passed.\n")

    # Save results for the workbook
    out = os.path.join(HERE, "tests", "results.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Test ID", "Build step", "Scenario", "Expected result", "Actual result", "Pass?"])
        for r in rows:
            w.writerow([r["id"], r["step"], r["scenario"], r["expected"], r["actual"], 1 if r["pass"] else 0])
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
