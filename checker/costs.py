"""Step 16: rough cost and timeline estimate.

Fee numbers live in data/toronto/fees.json (from the City's 2026 fee schedule).
Formula from the City's page: permit fee = Service Index ($/m²) x floor area of the work,
with a minimum fee. Plus a non-refundable application fee, and a fee per new unit.
This is a ROUGH estimate: the City calculates the real fee when you apply.
Not included: development charges, tree permit fees, Committee of Adjustment fees,
design and construction costs.
"""

from .core import fmt


def money(x):
    return f"${x:,.2f}"


def add_to_report(ctx, report):
    fees = ctx.data.get("fees")
    if not fees or report["stopped"]:
        report["costs"] = None
        return
    project = ctx.project
    p = (report.get("permit") or {}).get("answer", "")
    si, app, flat = fees["service_index_per_m2"], fees["application_fee"], fees["flat"]
    lines = []

    if p == "No building permit needed":
        report["costs"] = {"lines": [{"item": "Building permit", "amount": "$0", "note": "No building permit needed (zoning still applies)."}],
                           "disclaimer": disclaimer(fees)}
        return

    area_key = {"Garden suite": "gs_gfa", "Laneway suite": "ls_gfa", "Shed / accessory building": "anc_area",
                "Detached garage": "anc_area"}.get(project, "work_area")
    area = ctx.num(area_key)

    # Application fee
    if any(w in project for w in ("Shed", "garage", "Deck", "porch")):
        app_fee = app["accessory"]
    elif "suite" in project and ("Garden" in project or "Laneway" in project):
        app_fee = app["garden_or_laneway_suite"]
    else:
        app_fee = app["house"]
    lines.append({"item": "Application fee (non-refundable)", "amount": money(app_fee), "note": f"Fees effective {fees['effective']}."})

    # Permit fee
    if "Deck" in project or "porch" in project.lower():
        lines.append({"item": "Permit fee (deck/porch, flat)", "amount": money(flat["deck_porch_carport"]), "note": ""})
    elif project in ("Shed / accessory building", "Detached garage"):
        lines.append({"item": "Permit fee (garage/accessory, flat)", "amount": money(flat["garage_or_accessory"]), "note": ""})
    elif "Demolition" in project:
        if area is None:
            lines.append({"item": "Demolition fee", "amount": "Need area", "note": f"${si['demolition']}/m² of building demolished. Enter the floor area of the work."})
        else:
            lines.append({"item": "Demolition fee", "amount": money(max(area * si["demolition"], fees["minimum_fee"])),
                          "note": f"{fmt(area)} m² × ${si['demolition']}/m² (minimum {money(fees['minimum_fee'])})."})
    else:
        rate_key = "interior_alterations_group_c" if "Interior" in project else (
            "residential_alterations" if any(w in project for w in ("Secondary", "Multiplex", "Solar")) else "new_residential")
        rate = si[rate_key]
        if area is None:
            lines.append({"item": "Permit fee", "amount": "Need area",
                          "note": f"${rate}/m² × floor area of the work. Enter the floor area to estimate it."})
        else:
            fee = max(area * rate, fees["minimum_fee"])
            lines.append({"item": "Permit fee", "amount": money(fee),
                          "note": f"{fmt(area)} m² × ${rate}/m² (minimum {money(fees['minimum_fee'])})."})

    # New units
    eu, pu = ctx.num("existing_units"), ctx.num("proposed_units")
    new_units = (pu - eu) if (eu is not None and pu is not None and pu > eu) else (1 if any(
        w in project for w in ("Garden suite", "Laneway suite", "Secondary")) else 0)
    if new_units:
        lines.append({"item": f"New unit fee × {new_units}", "amount": money(new_units * fees["per_new_unit"]), "note": ""})

    # Timeline
    t = fees["timelines"]
    lines.append({"item": "City review time (complete application)", "amount": f"up to {t['house_business_days']} business days",
                  "note": "Legal maximum for house-type projects once the application is complete. Incomplete applications take longer."})
    fails = report["counts"].get("FAIL", 0)
    if fails:
        lines.append({"item": "Minor variance (if you don't change the design)", "amount": "months", "note": t["committee_of_adjustment"]})
    if ctx.yes("trca"):
        lines.append({"item": "TRCA permit", "amount": "varies", "note": t["trca_permit"]})
    if ctx.yes("in_hcd") or ctx.yes("heritage_designated"):
        lines.append({"item": "Heritage permit", "amount": "varies", "note": t["heritage_permit"]})
    report["costs"] = {"lines": lines, "disclaimer": disclaimer(fees)}


def disclaimer(fees):
    return (f"Rough estimate only, from {fees['source']} (effective {fees['effective']}; confidence: {fees['confidence']}). "
            "The City calculates the real fee. Not included: development charges, tree permits, Committee of Adjustment "
            "fees, design and construction costs. Fees change every January 1.")
