"""Step 3: Does the project need a building permit? (rules P-01 to P-12)

How to read a P- result:
  FLAG            = this rule TRIGGERS a permit
  PASS            = this rule does not trigger a permit (or the no-permit exemption is met)
  NEED MORE INFO  = we can't tell yet

The overall answer is one of:
  "Permit needed", "No building permit needed", "Need more info", "Check with the City"
"""

from .core import PASS, FLAG, NEED, fmt

NEEDED = "Permit needed"
NOT_NEEDED = "No building permit needed"
UNKNOWN = "Need more info"
CHECK_CITY = "Check with the City"


def check(ctx, kind):
    """kind comes from project_profiles.json (e.g. 'shed', 'deck', 'addition')."""
    before = len(ctx.results)
    decided = None            # NEEDED / NOT_NEEDED / CHECK_CITY / None (unknown)
    reason = ""

    if kind == "shed":
        decided, reason = _shed(ctx)
    elif kind == "accessory":
        decided, reason = _accessory(ctx)
    elif kind == "deck":
        decided, reason = _deck(ctx)
    elif kind in ("addition", "new_building", "new_house"):
        ctx.add("P-05", FLAG, message="This project adds floor area or a new structure, so it needs a permit.")
        decided, reason = NEEDED, "It adds floor area or a structure (P-05)."
        if kind == "new_house":
            ctx.add("P-09", FLAG, message="Replacing a house means demolishing the old one: a demolition permit is also needed.")
    elif kind == "secondary_suite":
        ctx.add("P-08", FLAG, message="Adding a secondary suite adds a dwelling unit (a change of use).")
        decided, reason = NEEDED, "Adding a unit is a change of use (P-08)."
        if ctx.yes("basement_work"):
            ctx.add("P-06", FLAG, message="Basement work for a second suite needs a permit.")
    elif kind == "change_of_use":
        ctx.add("P-08", FLAG, message="Going from one unit to several is a change of use, even with no construction.")
        decided, reason = NEEDED, "More units = change of use (P-08)."
    elif kind == "interior":
        decided, reason = _interior(ctx)
    elif kind == "demolition":
        ctx.add("P-09", FLAG, message="Demolishing all or part of a building needs a permit.")
        decided, reason = NEEDED, "Demolition needs a permit (P-09)."
    elif kind == "pool":
        decided = CHECK_CITY
        reason = ("Pools don't have a P- rule in the Rules Table. A pool enclosure (fence) permit is needed "
                  "under a separate City by-law, so check with the City. Zoning still applies.")
    elif kind == "driveway":
        decided = NOT_NEEDED
        reason = ("A driveway usually needs no building permit, but a new curb cut or front-yard parking pad "
                  "needs City approval (see AP-16). Zoning still applies.")
    elif kind == "solar":
        decided = NEEDED
        reason = "Solar collector systems need a building permit (Project Types tab, row 15)."

    # Extra triggers that can apply to ANY project if the user said yes.
    extra = _extra_triggers(ctx, skip_ids={r["rule_id"] for r in ctx.results[before:]})
    if extra and decided != NEEDED:
        decided, reason = NEEDED, extra

    # If nothing decided and there are open questions, say so.
    if decided is None:
        decided = UNKNOWN
        if not reason:
            reason = "Answer the permit questions marked NEED MORE INFO."

    return {"answer": decided, "reason": reason,
            "note": "Even when no permit is needed, the project must still meet zoning (rules below)."}


# ---------------------------------------------------------------- project kinds

def _shed(ctx):
    limit = ctx.limit("P-01")          # 15 m²
    if ctx.need("P-01", ["anc_area"], limit=limit):
        ctx.need("P-02", ["anc_area"], limit=ctx.limit("P-02"))
        return None, ""
    area = ctx.num("anc_area")
    if area >= limit:
        msg = f"Shed is {fmt(area)} m²; a permit is needed at {fmt(limit)} m² or more."
        if area == limit:
            msg += (" Note: at exactly 15 m², P-01 ('15 m² or more') and P-02 ('15 m² or less') overlap in the "
                    "Rules Table. We follow P-01. Check the City's page.")
        ctx.add("P-01", FLAG, value=area, limit=limit, message=msg)
        return NEEDED, f"The shed is {fmt(limit)} m² or more (P-01)."
    ctx.add("P-01", PASS, value=area, limit=limit, message=f"Shed is under {fmt(limit)} m².")

    # P-02: all five conditions must be true for "no permit"
    conditions = [("anc_storeys", lambda v: v == 1, "one storey"),
                  ("anc_attached", lambda v: v is False, "not attached"),
                  ("anc_storage_only", lambda v: v is True, "storage only"),
                  ("anc_plumbing", lambda v: v is False, "no plumbing")]
    missing = [k for k, _, _ in conditions if not ctx.has(k)]
    if missing:
        ctx.need("P-02", missing, limit=ctx.limit("P-02"),
                 why="A small shed needs no permit only if all five conditions are true.")
        return None, ""
    failed = [name for k, test, name in conditions if not test(ctx.get(k))]
    if failed:
        ctx.add("P-02", FLAG, value=area, limit=ctx.limit("P-02"),
                message="The no-permit exemption doesn't apply because it is not: " + ", ".join(failed) + ".")
        return NEEDED, "The small-shed exemption doesn't apply (P-02)."
    ctx.add("P-02", PASS, value=area, limit=ctx.limit("P-02"),
            message="All five no-permit conditions are met (under 15 m², one storey, detached, storage only, no plumbing).")
    return NOT_NEEDED, "Small storage shed that meets all five conditions (P-02)."


def _accessory(ctx):
    limit = ctx.limit("P-03")          # 10 m²
    if ctx.yes("anc_attached") or ctx.yes("anc_plumbing"):
        ctx.add("P-03", FLAG, value=ctx.num("anc_area"), limit=limit,
                message="Attached accessory buildings, or ones with plumbing, always need a permit.")
        return NEEDED, "Attached or has plumbing (P-03)."
    if ctx.need("P-03", ["anc_area"], limit=limit):
        return None, ""
    area = ctx.num("anc_area")
    if area > limit:
        ctx.add("P-03", FLAG, value=area, limit=limit,
                message=f"{fmt(area)} m² is over {fmt(limit)} m², so a permit is needed.")
        return NEEDED, f"Over {fmt(limit)} m² (P-03)."
    if ctx.missing("anc_attached", "anc_plumbing"):
        ctx.need("P-03", ["anc_attached", "anc_plumbing"], limit=limit)
        return None, ""
    ctx.add("P-03", PASS, value=area, limit=limit, message=f"{fmt(area)} m², detached, no plumbing.")
    return NOT_NEEDED, f"Small detached building, {fmt(limit)} m² or less, no plumbing (P-03)."


def _deck(ctx):
    limit = ctx.limit("P-04")          # 0.6 m
    if ctx.need("P-04", ["deck_height"], limit=limit):
        return None, ""
    h = ctx.num("deck_height")
    if h > limit:
        ctx.add("P-04", FLAG, value=h, limit=limit,
                message=f"Deck is {fmt(h)} m above ground; a permit is needed above {fmt(limit)} m (60 cm).")
        return NEEDED, f"Deck higher than {fmt(limit)} m (P-04)."
    if ctx.yes("deck_is_exit"):
        ctx.add("P-04", FLAG, value=h, limit=limit,
                message="Low deck, but it is part of a required exit, so the no-permit exemption doesn't apply.")
        return NEEDED, "Deck is part of a required exit (P-04 note)."
    if ctx.need("P-04", ["deck_is_exit"], limit=limit,
                why="Low decks need no permit only if they are not part of a required exit."):
        return None, ""
    ctx.add("P-04", PASS, value=h, limit=limit,
            message=f"Deck is {fmt(h)} m high (not over {fmt(limit)} m) and not part of a required exit.")
    return NOT_NEEDED, f"Deck not over {fmt(limit)} m and not an exit (P-04)."


def _interior(ctx):
    triggers = [("basement_work", "P-06"), ("structural_work", "P-07"), ("hvac_plumbing", "P-11")]
    any_yes = False
    for key, rid in triggers:
        if ctx.yes(key):
            ctx.add(rid, FLAG, message="You said yes to work that needs a permit.")
            any_yes = True
    if any_yes:
        return NEEDED, "Includes work that needs a permit (" + ", ".join(
            r["rule_id"] for r in ctx.results if r["status"] == FLAG and r["rule_id"].startswith("P-")) + ")."
    unknown = [k for k, _ in triggers if not ctx.has(k)]
    for key, rid in triggers:
        if not ctx.has(key):
            ctx.need(rid, [key])
        else:
            ctx.add(rid, PASS, message="Not part of this project.")
    if unknown:
        return None, ""
    if ctx.yes("minor_work_only"):
        ctx.add("P-12", PASS, message="Only minor work from the no-permit list. Zoning still applies.")
        return NOT_NEEDED, "Only work on the no-permit list (P-12)."
    if ctx.need("P-12", ["minor_work_only"]):
        return None, ""
    ctx.add("P-12", FLAG, message="The work is not only items from the no-permit list. Check with Toronto Building.")
    return None, "Some work isn't on either list; check with Toronto Building."


def _extra_triggers(ctx, skip_ids):
    """Triggers that apply to any project when the user answered yes."""
    reasons = []
    if ctx.yes("structural_work") and "P-07" not in skip_ids:
        ctx.add("P-07", FLAG, message="Structural changes, new/bigger openings or enclosing a deck/porch need a permit.")
        reasons.append("P-07")
    if ctx.yes("hvac_plumbing") and "P-11" not in skip_ids:
        ctx.add("P-11", FLAG, message="Heating/plumbing, chimney, wood stove, backwater valve or backflow work needs a permit.")
        reasons.append("P-11")
    if ctx.yes("basement_work") and "P-06" not in skip_ids:
        ctx.add("P-06", FLAG, message="This basement work needs a permit.")
        reasons.append("P-06")
    if ctx.yes("demolition") and "P-09" not in skip_ids:
        ctx.add("P-09", FLAG, message="Demolishing all or part of a building needs a permit.")
        reasons.append("P-09")
    eu, pu = ctx.num("existing_units"), ctx.num("proposed_units")
    if eu is not None and pu is not None and pu > eu and "P-08" not in skip_ids:
        ctx.add("P-08", FLAG, value=pu, message=f"Units go from {fmt(eu)} to {fmt(pu)}: a change of use.")
        reasons.append("P-08")
    h = ctx.num("retaining_wall_height")
    if h is not None and "P-10" not in skip_ids:
        limit = ctx.limit("P-10")
        if h > limit and ctx.yes("retaining_wall_public"):
            ctx.add("P-10", FLAG, value=h, limit=limit,
                    message=f"Retaining wall over {fmt(limit)} m next to public property or an entrance.")
            reasons.append("P-10")
        elif h > limit and not ctx.has("retaining_wall_public"):
            ctx.need("P-10", ["retaining_wall_public"], limit=limit)
        else:
            ctx.add("P-10", PASS, value=h, limit=limit, message="Retaining wall doesn't trigger a permit.")
    if reasons:
        return "Other work in the project needs a permit (" + ", ".join(reasons) + ")."
    return ""
