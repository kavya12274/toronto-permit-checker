"""Step 12: fix-it suggestions. For each FAIL, the smallest change that would make it pass.

The checker attaches "fix_data" to a FAIL when it knows the number that would pass:
  {"kind": "min", "key": "side_setback", "value": 0.8, "limit": 0.9}  -> needs to go UP by 0.1
  {"kind": "max", "key": "height", "value": 10.5, "limit": 10.0}      -> needs to come DOWN by 0.5
We turn that into plain words. The change is rounded UP (to the nearest cm, or
0.01) so following it really does pass, not fall just short.
A fix is a suggestion, not design advice: changing one thing can affect another rule,
so re-run the check after any change.
"""

import math

from .core import FAIL, fmt
from .fields import label

# Words for what kind of measurement a field is
DISTANCE_WORDS = ("setback", "to_house", "to_lot_line", "to_side_line", "to_front_line", "to_lane")


def _round_up(x, step=0.01):
    return math.ceil(round(x / step, 6)) * step


def suggestion(fd, unit):
    key, value, limit = fd["key"], fd.get("value"), fd.get("limit")
    name = label(key).lower()
    u = unit or ""
    pct = u.startswith("%")
    unit_txt = " percentage points" if pct else (" " + u if u else "")

    if fd["kind"] == "yesno":
        return f"Change the design so the answer to '{label(key)}' is different, or apply for a minor variance."

    gap = _round_up(abs(limit - value))
    gap_txt = f"{fmt(gap)}{unit_txt}"
    target = f"{fmt(value)} → {fmt(limit)}{'%' if pct else (' ' + u if u else '')}"

    if fd["kind"] == "min":
        if any(w in key for w in DISTANCE_WORDS):
            return f"Move the wall {gap_txt} in (further from the line) so the {name} goes {target}."
        if pct:
            return f"Increase the {name} by {gap_txt} ({target})."
        return f"Increase the {name} by {gap_txt} ({target})."
    # max
    if "height" in key:
        return f"Lower the height by {gap_txt} ({target})."
    if "length" in key or "depth" in key or "width" in key:
        return f"Shorten it by {gap_txt} ({target})."
    if "area" in key or "gfa" in key:
        return f"Make it {gap_txt} smaller ({target})."
    if "coverage" in key or "fsi" in key:
        return f"Reduce the {name} by {gap_txt} ({target}): a smaller footprint or floor area."
    return f"Reduce the {name} by {gap_txt} ({target})."


def add_to_report(ctx, report):
    fixes = []
    for r in report["results"]:
        if r["status"] != FAIL:
            continue
        fd = r.get("fix_data")
        if fd and (fd["kind"] == "yesno" or (fd.get("limit") is not None and fd.get("value") is not None)):
            text = suggestion(fd, r["unit"])
        else:
            text = "Change the design to meet this rule, or apply for a minor variance."
        text += " Then re-run the check: one change can affect other rules."
        r["fix"] = text
        fixes.append({"rule_id": r["rule_id"], "text": text})
    report["fixes"] = fixes
