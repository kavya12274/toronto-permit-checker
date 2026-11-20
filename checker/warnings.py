"""Common rejection warnings, and how long permits like this take in Toronto.

1. Warnings: "Applications like yours often get sent back for..."
   Built from the City of Toronto's own pages (data/toronto/rejection_warnings.json),
   plus warnings from this project's results (fails, other approvals, missing numbers).
   Each warning says where it comes from. The City doesn't publish a ranked list of
   rejection reasons, so we don't invent percentages.

2. Wait times: the median days from application to permit issued for this type of
   project, from the City's open permit data (data/toronto/permit_stats.json,
   built by tools/build_stats.py).
"""

from .core import FAIL, FLAG, NEED
from .roadmap import tags_for

# Project type -> the group name in permit_stats.json
STATS_KEY = {
    "Rear addition (1 or 2 storey)": "rear", "Second-storey addition": "rear", "Front porch / front addition": "porch",
    "Deck / platform": "deck", "Shed / accessory building": "shed", "Detached garage": "garage", "Pool": "pool",
    "Garden suite": "garden", "Laneway suite": "garden", "Secondary suite (e.g. basement apartment)": "secondary",
    "Interior alterations / basement finishing": "interior", "New detached house / houseplex (replacement)": "newhouse",
}


def add_to_report(ctx, report):
    data = ctx.data.get("rejection_warnings")
    answer = (report.get("permit") or {}).get("answer", "")
    report["warnings"] = []
    if data and not report["stopped"] and answer not in ("No building permit needed",) \
            and ctx.project not in ("Driveway / parking pad", "Pool"):
        tags = tags_for(ctx)
        results = report["results"]
        if any(r["status"] == FAIL and r["group"] in ("Zoning", "Suites") for r in results):
            tags.add("fails")
        if any(r["status"] == FLAG and r["rule_id"] in ("AP-03", "AP-04", "AP-05", "AP-06", "AP-07", "AP-10") for r in results):
            tags.add("approvals")
        if sum(1 for r in results if r["status"] == NEED and r["group"] == "Zoning") >= 3:
            tags.add("missing")
        sources = data["sources"]
        picked = [dict(w) for w in data["warnings"] if w["when"] in tags]
        picked.sort(key=lambda w: w["rank"])
        for w in picked:
            src = sources.get(w["source"])
            w["source_name"] = src["name"] if src else "Based on this project's check"
            w["source_link"] = src["link"] if src else ""
        report["warnings"] = picked

    stats = ctx.data.get("permit_stats")
    key = STATS_KEY.get(ctx.project)
    group = next((g for g in (stats or {}).get("groups", []) if g["project_key"] == key), None) if key else None
    report["wait"] = None
    if group:
        report["wait"] = {"name": group["name"], "median_days": group["median_days"], "p25_days": group["p25_days"],
                          "p75_days": group["p75_days"], "permits": group["permits"],
                          "within_14_days_pct": group["within_14_days_pct"], "over_90_days_pct": group["over_90_days_pct"],
                          "source": stats["source"], "link": stats["link"], "data_up_to": stats.get("data_up_to")}
