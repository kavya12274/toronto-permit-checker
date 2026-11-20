"""Step 6: garden suites (GS-), laneway suites (LS-), secondary suites (SS-)
and provincial overrides (ON-).

Garden and laneway suites are in Chapter 150 of By-law 569-2013.
Provincial overrides come from the Planning Act s. 35.1 and O. Reg. 299/19.
The ON- rules are marked 'Verify' in the Rules Table, so they are shown as
FLAGs for you to confirm. They never silently change a city result.
"""

from .engine import register
from .core import PASS, FAIL, NEED, FLAG, fmt
from .zoning import required_house_side_setback


# ---------------------------------------------------------------- garden suite

@register("garden")
def garden_suite(ctx):
    one_suite_building(ctx)

    # GS-02 rear yard soft landscaping across the full lot width
    fr = ctx.num("lot_frontage")
    if fr is None:
        ctx.need("GS-02", ["lot_frontage"], why="Rear landscaping % depends on frontage.")
    else:
        lim = ctx.limit("GS-02") if fr > 6.0 else 25        # 25% if frontage <= 6 m (rule text)
        ctx.check_min("GS-02", "rear_soft_full_width_pct", lim)

    # GS-03 rear setback (+ GS-04 extra 1.5 m for high rear windows)
    base = ctx.limit("GS-03")                               # 1.5 m
    if not ctx.need("GS-03", ["lot_depth", "gs_rear_setback"], limit=base,
                    why="Rear setback depends on lot depth (lots deeper than 45 m need more)."):
        depth, h = ctx.num("lot_depth"), ctx.num("gs_height")
        req, why = base, f"Lot depth {fmt(depth)} m (45 m or less): {fmt(base)} m."
        if depth > 45:
            if h is None:
                ctx.need("GS-03", ["gs_height"], limit=base, why="Lots deeper than 45 m: greater of 1.5 m or half the suite height.")
                req = None
            else:
                req = max(base, h / 2)
                why = f"Lot deeper than 45 m: greater of {fmt(base)} m or half the height ({fmt(h / 2)} m) = {fmt(req)} m."
        if req is not None:
            rid = "GS-03"
            if ctx.yes("gs_rear_windows_high"):
                req += ctx.limit("GS-04")
                why += f" Plus {fmt(ctx.limit('GS-04'))} m for rear windows above 4.0 m (GS-04)."
                rid = "GS-04"
            ctx.check_min(rid, "gs_rear_setback", req, unit="m",
                          message=f"{why} Yours: {fmt(ctx.num('gs_rear_setback'))} m.")

    # GS-05 / GS-06 side setback = greater of X or 10% of frontage, max 3.0 m
    if not ctx.need("GS-05", ["lot_frontage", "gs_side_openings", "gs_side_setback"],
                    why="Side setback depends on frontage and whether the wall has windows or doors."):
        rid = "GS-05" if ctx.yes("gs_side_openings") else "GS-06"
        base = ctx.limit(rid)                                # 1.5 m or 0.6 m
        tenth = 0.10 * fr
        req = min(max(base, tenth), 3.0)                     # "max 3.0 m" (rule text)
        ctx.check_min(rid, "gs_side_setback", req,
                      message=f"Needs the greater of {fmt(base)} m or 10% of {fmt(fr)} m ({fmt(tenth)} m), capped at 3.0 m "
                              f"= {fmt(req)} m. Yours: {fmt(ctx.num('gs_side_setback'))} m.")

    # GS-07 corner lot
    if ctx.yes("corner_lot"):
        if ctx.get("parking_access") == "From the flanking (side) street":
            ctx.check_min("GS-07", "gs_side_setback", 6.0,
                          message=f"Corner lot with parking from the side street: 6.0 m. Yours: {fmt(ctx.num('gs_side_setback'))} m.")
        else:
            house = ctx.num("street_side_setback")
            if house is None:
                ctx.need("GS-07", ["street_side_setback"], why="Corner lot: greater of the house's side setback or 1.5 m.")
            else:
                req = max(house, ctx.limit("GS-07"))
                ctx.check_min("GS-07", "gs_side_setback", req)

    # GS-08 through lot
    if ctx.yes("through_lot"):
        ctx.add("GS-08", FLAG, limit=ctx.limit("GS-08"),
                message="Through lot: if parking comes from the rear street, the rear setback is the greater of the "
                        "neighbour's front setback or 6.0 m. Check this on your drawings.")

    # GS-09 / GS-10 separation and GS-11 / GS-12 height
    separation_and_height(ctx, "gs", ("GS-09", "GS-10"), ("GS-11", "GS-12"))

    ctx.check_max("GS-13", "gs_storeys", ctx.limit("GS-13"))
    roof_items(ctx, "GS-14", {"Skylight": 0.3, "Antenna or flagpole": 1.0,
                              "Rooftop equipment (e.g. heat pump)": "limit", "Solar panels": 1.2})

    # GS-15 / GS-16 floor area by storeys
    if not ctx.need("GS-16", ["gs_storeys", "gs_gfa"], why="Floor area limit depends on storeys (60 m² for one storey, 120 m² for two)."):
        rid = "GS-16" if ctx.num("gs_storeys") <= 1 else "GS-15"
        ctx.check_max(rid, "gs_gfa", ctx.limit(rid))

    smaller_than_house(ctx, "GS-17", "gs_gfa")

    # GS-18 lot coverage: all buildings max 45% (other option: suite excluded, ancillary max 20%)
    if ctx.has("all_buildings_coverage"):
        ctx.check_max("GS-18", "all_buildings_coverage", ctx.limit("GS-18"),
                      message=f"All buildings together max {fmt(ctx.limit('GS-18'))}% of the lot (or: suite not counted and all "
                              f"ancillary buildings max 20%). Also check the Lot Coverage Overlay. "
                              f"Yours: {fmt(ctx.num('all_buildings_coverage'))}%.")
    else:
        ctx.need("GS-18", ["all_buildings_coverage"], limit=ctx.limit("GS-18"))

    deck_ratio(ctx, "GS-19", "gs_deck_area", "gs_gfa")
    ctx.check_min("GS-20", "bike_spaces", ctx.limit("GS-20"))

    # GS-21 fire access (OBC) - always needs a human
    ctx.add("GS-21", FLAG, message="A garden suite needs a firefighter access route from the street. The exact path width "
                                   "and distance are in the Building Code (not yet extracted). A qualified designer must confirm.")


def one_suite_building(ctx):
    """GS-01: only one ancillary building with a garden OR laneway suite per lot."""
    if ctx.need("GS-01", ["other_suite_building"], limit=ctx.limit("GS-01")):
        return
    if ctx.yes("other_suite_building"):
        ctx.add("GS-01", FAIL, value=2, limit=ctx.limit("GS-01"), unit="building",
                message="The lot already has a garden or laneway suite. Only one suite building is allowed per lot (not both).")
    else:
        ctx.add("GS-01", PASS, value=1, limit=ctx.limit("GS-01"), unit="building",
                message="This would be the only suite building on the lot.")


def separation_and_height(ctx, prefix, sep_ids, height_ids):
    """Separation from the house (4.0 m / 7.5 m) and height (4.0 m / 6.3 m).
    Works for garden suites (gs_) and laneway suites (ls_)."""
    h_key, d_key = f"{prefix}_height", f"{prefix}_to_house"
    h, dist = ctx.num(h_key), ctx.num(d_key)
    low_id, high_id = sep_ids

    # Separation: depends on height
    if h is None:
        ctx.need(low_id, [h_key], why="Separation from the house depends on the suite height.")
    else:
        if h <= 4.0:
            rid, req = low_id, ctx.limit(low_id)                       # 4.0 m
        else:
            rid = high_id
            req = ctx.limit(high_id) if high_id != low_id else 7.5      # LS-06 note: 7.5 m if taller than 4.0 m
        ok = ctx.check_min(rid, d_key, req, unit="m",
                           message=f"Suite is {fmt(h)} m tall, so it must be at least {fmt(req)} m from the house. "
                                   f"Yours: {fmt(dist)} m.")
        # ON-02: the province may cap the required separation at 4 m for ARU projects.
        if ok is False and req > 4.0 and dist is not None and dist >= ctx.limit("ON-02") - 1e-9:
            ctx.add("ON-02", FLAG, value=dist, limit=ctx.limit("ON-02"),
                    message=f"Provincial override to VERIFY: O. Reg. 299/19 may stop a city from requiring more than "
                            f"{fmt(ctx.limit('ON-02'))} m between buildings on a lot with 3 or fewer units. Your "
                            f"{fmt(dist)} m might be allowed. Read the e-Laws text before relying on this.")

    # Height: depends on distance to the house
    near_id, far_id = height_ids
    if dist is None:
        ctx.need(near_id, [d_key], why="Height limit depends on distance to the house.")
    else:
        if dist < 7.5:
            rid, lim = near_id, (ctx.limit(near_id) if near_id != far_id else 4.0)   # 4.0 m within 7.5 m
        else:
            rid, lim = far_id, ctx.limit(far_id)                                      # 6.3 m
        ctx.check_max(rid, h_key, lim, unit="m",
                      message=f"Suite is {fmt(dist)} m from the house, so max height is {fmt(lim)} m. Yours: {fmt(h)} m.")


def roof_items(ctx, rid, allowances):
    """GS-14 / LS-11: things on the roof may go a little above the suite's height limit.
    allowances: item -> metres allowed ('limit' = the Limit column of the rule).
    The smaller allowances (skylight 0.3 m etc.) come from the rule text."""
    item = ctx.get("suite_roof_item")
    if item is None:
        ctx.need(rid, ["suite_roof_item"], why="Some rooftop items may go above the height limit.")
        return
    if item == "Nothing":
        ctx.add(rid, PASS, message="Nothing on the roof goes above the height limit.")
        return
    if item not in allowances:
        ctx.add(rid, FAIL, message=f"{item} is not one of the rooftop items allowed above the height limit for this suite.")
        return
    lim = ctx.limit(rid) if allowances[item] == "limit" else allowances[item]
    ctx.check_max(rid, "suite_roof_above", lim, unit="m",
                  message=f"{item}: may go up to {fmt(lim)} m above the height limit. Yours: {fmt(ctx.num('suite_roof_above'))} m.")
    if item.startswith("Rooftop equipment"):
        ctx.notes.append(f"{rid}: rooftop equipment must also cover no more than 30% of the roof and sit back from the walls.")


def smaller_than_house(ctx, rid, key):
    if ctx.need(rid, [key, "house_gfa"], why="The suite must be smaller than the house."):
        return
    v, house = ctx.num(key), ctx.num("house_gfa")
    if v < house:
        ctx.add(rid, PASS, value=v, limit=house, unit="m²", message=f"Suite {fmt(v)} m² is smaller than the house ({fmt(house)} m²).")
    else:
        ctx.add(rid, FAIL, value=v, limit=house, unit="m²",
                message=f"Suite {fmt(v)} m² must be smaller than the house ({fmt(house)} m²).",
                fix_data={"kind": "max", "key": key, "value": v, "limit": house - 0.1})


def deck_ratio(ctx, rid, deck_key, gfa_key):
    if not ctx.has(deck_key):
        return                                             # only if the suite has a deck
    if ctx.need(rid, [gfa_key]):
        return
    lim = 0.10 * ctx.num(gfa_key)
    v = ctx.num(deck_key)
    ok = v < lim
    ctx.add(rid, PASS if ok else FAIL, value=v, limit=round(lim, 2), unit="m²",
            message=f"Deck must be under 10% of the suite floor area ({fmt(lim)} m²). Yours: {fmt(v)} m².",
            fix_data=None if ok else {"kind": "max", "key": deck_key, "value": v, "limit": round(lim - 0.1, 2)})


# ---------------------------------------------------------------- laneway suite

@register("laneway")
def laneway_suite(ctx):
    # LS-01: lot must touch a lane for at least 3.5 m
    lim = ctx.limit("LS-01")
    if ctx.need("LS-01", ["lane_frontage"], limit=lim):
        return
    if ctx.num("lane_frontage") < lim - 1e-9:
        ctx.add("LS-01", FAIL, value=ctx.num("lane_frontage"), limit=lim,
                message=f"The lot touches the lane for {fmt(ctx.num('lane_frontage'))} m; a laneway suite needs at least "
                        f"{fmt(lim)} m. A laneway suite is not allowed here. Try the garden suite rules instead "
                        "(choose 'Garden suite' as the project type).")
        return
    ctx.add("LS-01", PASS, value=ctx.num("lane_frontage"), limit=lim, message="Enough lane frontage for a laneway suite.")

    one_suite_building(ctx)

    fr = ctx.num("lot_frontage")
    if fr is None:
        ctx.need("LS-02", ["lot_frontage"], why="Landscaping % depends on frontage.")
    else:
        lim = ctx.limit("LS-02") if fr > 6.0 else 60        # 60% if frontage <= 6 m (rule text)
        ctx.check_min("LS-02", "ls_between_soft_pct", lim)
    ctx.check_min("LS-03", "ls_lane_side_soft_pct", ctx.limit("LS-03"))
    ctx.check_min("LS-04", "ls_rear_setback", ctx.limit("LS-04"),
                  message=f"Minimum {fmt(ctx.limit('LS-04'))} m (0.0 m allowed if the rear line doesn't touch a street/lane "
                          f"and the wall has no openings). Yours: {fmt(ctx.num('ls_rear_setback'))} m.")
    ctx.check_min("LS-05", "ls_side_setback", ctx.limit("LS-05"),
                  message=f"Minimum {fmt(ctx.limit('LS-05'))} m (0.0 m if no openings and not next to a street/lane). "
                          f"Yours: {fmt(ctx.num('ls_side_setback'))} m.")
    separation_and_height(ctx, "ls", ("LS-06", "LS-06"), ("LS-09", "LS-09"))
    ctx.check_max("LS-07", "ls_length", ctx.limit("LS-07"))
    ctx.check_max("LS-08", "ls_width", ctx.limit("LS-08"))
    ctx.check_max("LS-10", "ls_storeys", ctx.limit("LS-10"))
    roof_items(ctx, "LS-11", {"Skylight": 0.3, "Rooftop equipment (e.g. heat pump)": "limit"})
    smaller_than_house(ctx, "LS-12", "ls_gfa")
    deck_ratio(ctx, "LS-13", "ls_deck_area", "ls_gfa")
    ctx.check_max("LS-14", "ancillary_coverage_all", ctx.limit("LS-14"))
    ctx.check_min("LS-15", "bike_spaces", ctx.limit("LS-15"))


# ---------------------------------------------------------------- secondary suite

@register("secondary")
def secondary_suite(ctx):
    # SS-01 building type
    if not ctx.need("SS-01", ["building_type"]):
        bt = ctx.get("building_type")
        if bt in ("Detached house", "Semi-detached house", "Townhouse"):
            ctx.add("SS-01", PASS, message=f"A secondary suite is allowed in a {bt.lower()}.")
        else:
            ctx.add("SS-01", FAIL, message=f"Secondary suites are allowed in detached, semi-detached and townhouses, not a {bt.lower()}.")

    # SS-02 one suite per dwelling unit (default: the one you're adding)
    if ctx.has("ss_count"):
        ctx.check_max("SS-02", "ss_count", ctx.limit("SS-02"))

    # SS-04 exception: whole basement of a one-storey detached house
    one_storey_detached = ctx.num("house_storeys") == 1 and ctx.get("building_type") == "Detached house"
    if one_storey_detached and ctx.yes("ss_whole_basement"):
        ctx.add("SS-04", PASS, message="One-storey detached house: the suite may take the whole basement (exception to the 45% limit).")
    else:
        # SS-03 max 45% of the interior floor area
        if ctx.yes("ss_whole_basement") and not ctx.has("ss_floor_pct"):
            ctx.need("SS-03", ["ss_floor_pct", "house_storeys"], limit=ctx.limit("SS-03"),
                     why="A whole-basement suite is only exempt in a one-storey detached house.")
        else:
            ctx.check_max("SS-03", "ss_floor_pct", ctx.limit("SS-03"))

    # SS-05 parking on the front-yard driveway is allowed (information)
    ctx.add("SS-05", PASS, message="Good to know: parking for the secondary suite may be on the front-yard driveway.")


# ---------------------------------------------------------------- provincial overrides

@register("provincial")
def provincial(ctx):
    """ON-01 and ON-03 (ON-02 is checked alongside the separation rules)."""
    # ON-01: up to 3 units as-of-right with a detached, semi or rowhouse
    pu = ctx.num("proposed_units")
    if pu is None:
        ctx.need("ON-01", ["proposed_units"], limit=ctx.limit("ON-01"),
                 why="The province allows up to 3 units as of right on urban residential lots.")
    elif pu <= ctx.limit("ON-01"):
        ctx.add("ON-01", PASS, value=pu, limit=ctx.limit("ON-01"),
                message=f"{fmt(pu)} unit(s): within the 3 units the province allows as of right (city zoning can't block them). "
                        "Marked 'Verify' in the Rules Table.")
    else:
        ctx.add("ON-01", FLAG, value=pu, limit=ctx.limit("ON-01"),
                message=f"{fmt(pu)} units is more than the 3 the province guarantees. City rules (like the 'u' value) decide the rest.")

    # ON-03: coverage of at least 45% must be allowed for ARU projects
    cov = ctx.get("coverage_overlay")
    if isinstance(cov, (int, float)) and cov < ctx.limit("ON-03") and (pu is None or pu <= 3):
        ctx.add("ON-03", FLAG, value=cov, limit=ctx.limit("ON-03"),
                message=f"Provincial override to VERIFY: your Lot Coverage Overlay is {fmt(cov)}%, but for additional "
                        f"residential units the province may require at least {fmt(ctx.limit('ON-03'))}% to be allowed. "
                        "Read the e-Laws text before relying on this.")
