"""Everything added to the report after the rules have run.

  step 11  pre-filled permit application fields + list of rules not checked
  step 12  fix-it suggestions                  (fixit.py)
  step 13  minor variance path                 (variance.py)
  step 15  buildable area diagram              (diagram.py)
  step 16  cost and timeline estimate          (costs.py)
  step 18  by-law version tracker              (tracker.py)
  step 22  shadow preview, plain maths        (shadow.py)
  20-21    AI status in the report             (ai_hooks.py); the AI itself runs only when asked
"""

import importlib
import importlib.util

from .core import FAIL, fmt


def add_extras(ctx, report):
    report["application"] = application_fields(ctx, report)
    report["not_checked"] = rules_not_checked(ctx, report)
    # Later steps plug in here:
    for name in ("fixit", "variance", "diagram", "costs", "roadmap", "warnings", "language", "tracker", "shadow", "ai_hooks"):
        if importlib.util.find_spec(f"checker.{name}") is None:
            continue                      # that build step isn't done yet
        importlib.import_module(f"checker.{name}").add_to_report(ctx, report)


# ---------------------------------------------------------------- step 11

PURPOSE = {
    "Rear addition (1 or 2 storey)": "Addition to an existing building",
    "Second-storey addition": "Addition to an existing building",
    "Front porch / front addition": "Addition to an existing building",
    "Deck / platform": "New construction (deck)",
    "Shed / accessory building": "New construction (accessory building)",
    "Detached garage": "New construction (accessory building)",
    "Pool": "Pool (enclosure permit is separate)",
    "Garden suite": "New construction (garden suite)",
    "Laneway suite": "New construction (laneway suite)",
    "Secondary suite (e.g. basement apartment)": "Alteration + change of use (additional unit)",
    "Multiplex conversion (house to 2-4 units)": "Change of use (additional units)",
    "New detached house / houseplex (replacement)": "New construction + demolition",
    "Interior alterations / basement finishing": "Alteration to an existing building",
    "Driveway / parking pad": "No building permit usually (City curb-cut approval)",
    "Solar panels": "Alteration (solar collector system)",
    "Demolition only": "Demolition",
}


def application_fields(ctx, report):
    """Fields from the provincial 'Application for a Permit to Construct or Demolish',
    pre-filled where we know the answer. Personal details are left blank on purpose:
    the applicant fills them in. Check them against the Feb 16, 2026 version of the form."""
    i = ctx.inputs
    project = ctx.project
    blank = "(fill in)"

    def v(key, unit=""):
        val = i.get(key)
        if val is None:
            return blank
        if val == "none":
            return "none"
        return f"{fmt(val)}{' ' + unit if unit else ''}"

    units_before, units_after = i.get("existing_units"), i.get("proposed_units")
    new_house = "New detached house" in project
    schedules = ["Schedule 1: Designer information"]
    if any(w in project for w in ("addition", "New detached house", "suite", "Multiplex")):
        schedules.append("Energy Efficiency Design Summary (SB-12)")
    schedules.append("Tree Declaration form" + (" (trees near the work: tree permit too)" if i.get("trees_near_work") else ""))
    if "addition" in project.lower() or new_house:
        schedules.append("Residential Infill Public Notice (if it applies)")
    if new_house or "Demolition" in project:
        schedules.append("Demolition permit application + checklist")

    approvals = [r["title"] for r in report["results"] if r["rule_id"].startswith("AP-") and r["status"] == "FLAG"
                 and r["rule_id"] not in ("AP-08", "AP-19")]

    return [
        {"part": "A. Project information", "field": "Project address", "value": i.get("address") or blank},
        {"part": "A. Project information", "field": "Lot / plan / legal description", "value": blank},
        {"part": "A. Project information", "field": "Lot frontage / depth / area",
         "value": f"{v('lot_frontage', 'm')} / {v('lot_depth', 'm')} / {v('lot_area', 'm²')}"},
        {"part": "A. Project information", "field": "Zoning", "value": i.get("zone_label") or i.get("zone") or blank},
        {"part": "A. Project information", "field": "Project value (estimated construction cost)", "value": blank},
        {"part": "B. Purpose of application", "field": "Type of work", "value": PURPOSE.get(project, blank)},
        {"part": "B. Purpose of application", "field": "Description of proposed work",
         "value": i.get("description") or project or blank},
        {"part": "B. Purpose of application", "field": "Current use / proposed use",
         "value": "Residential / Residential"},
        {"part": "B. Purpose of application", "field": "Dwelling units (existing → proposed)",
         "value": f"{fmt(units_before) if units_before is not None else blank} → "
                  f"{fmt(units_after) if units_after is not None else blank}"},
        {"part": "B. Purpose of application", "field": "Building type", "value": i.get("building_type") or blank},
        {"part": "B. Purpose of application", "field": "Storeys / height", "value": f"{v('storeys')} / {v('height', 'm')}"},
        {"part": "B. Purpose of application", "field": "New floor area", "value": v("gs_gfa", "m²") if "Garden" in project
            else (v("ls_gfa", "m²") if "Laneway" in project else blank)},
        {"part": "C–E. Applicant, owner, builder", "field": "Names and contact details",
         "value": "(fill in: not collected by this tool)"},
        {"part": "F. Tarion warranty", "field": "New home warranty enrolment",
         "value": "Likely needed (new house)" if new_house else "Not usually for this project type"},
        {"part": "G. Required schedules / forms", "field": "Attach", "value": "; ".join(schedules)},
        {"part": "H. Applicable law", "field": "Other approvals to get first",
         "value": "; ".join(approvals) if approvals else "None flagged (still check AP-19)"},
        {"part": "H. Applicable law", "field": "Zoning compliance",
         "value": "Does not comply: minor variance needed" if any(r["status"] == FAIL and r["group"] in ("Zoning", "Suites") for r in report["results"])
         else "No zoning fails found (Zoning Applicable Law Certificate / review still required)"},
    ]


def rules_not_checked(ctx, report):
    """Rules from the table that produced no result for this project (shown in the report's appendix)."""
    used = {r["rule_id"] for r in report["results"]}
    return [{"rule_id": r["id"], "rule": r["rule"], "section": r["section"]}
            for r in ctx.data["rules"] if r["id"] not in used]
