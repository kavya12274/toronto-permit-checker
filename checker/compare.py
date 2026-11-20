"""What-if comparison: two or three designs side by side.

Each design is a full set of form answers (usually your answers with a few numbers
changed). Each one runs through the normal checker, and we line up:
  permit needed?  which rules don't pass  needs a minor variance?
  open questions  rough permit fee  review time
Nothing new is decided here: it's engine.run() three times.
"""

from .engine import run
from .core import FAIL, NEED


def compare(designs, city="toronto"):
    out = []
    for i, d in enumerate(designs[:3]):
        report = run(d.get("inputs", {}), city)
        fails = [r for r in report["results"] if r["status"] == FAIL]
        zoning_fails = [r for r in fails if r["group"] in ("Zoning", "Suites")]
        safety_fails = [r for r in fails if r["group"] == "Building Code (safety)"]
        fee = None
        for line in (report.get("costs") or {}).get("lines", []):
            if line["item"].startswith(("Permit fee", "Application fee", "Demolition fee", "New unit fee")) and line["amount"].startswith("$"):
                fee = (fee or 0) + float(line["amount"].replace("$", "").replace(",", ""))
        review = next((l["amount"] for l in (report.get("costs") or {}).get("lines", []) if l["item"].startswith("City review")), "")
        out.append({
            "name": d.get("name") or f"Design {chr(65 + i)}",
            "stopped": report["stopped"],
            "permit": (report.get("permit") or {}).get("answer", ""),
            "fails": [{"rule_id": r["rule_id"], "title": r["title"], "message": r["message"], "fix": r.get("fix")} for r in fails],
            "needs_variance": bool(zoning_fails),
            "safety_fails": len(safety_fails),
            "need_info": sum(1 for r in report["results"] if r["status"] == NEED),
            "fee": round(fee, 2) if fee is not None else None,
            "fee_note": "" if fee is not None else "Add the floor area of the work to estimate the fee",
            "review": review,
            "overall": report["overall"],
        })
    # A simple verdict: fewest zoning fails, then fewest open questions, then lowest fee
    ranked = sorted(range(len(out)), key=lambda i: (out[i]["stopped"], len([f for f in out[i]["fails"]]),
                                                     out[i]["need_info"], out[i]["fee"] or 0))
    best = ranked[0] if out else None
    return {"designs": out, "best": best}
