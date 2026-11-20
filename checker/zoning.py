"""Steps 4, 5 and 19: zoning checks under By-law 569-2013.

  - RD zone (RD- rules)                       step 4
  - General rules for all zones (G- rules)    step 4
  - R zone (R- rules)                         step 5
  - RS, RT, RM (same structure as RD)         step 19

LIMITS come from the Rules Table (ctx.limit("RD-18") etc.).
Some numbers only appear inside the "Applies when" or "Notes" text of a rule
(for example the frontage bands 6/12/15/18 m). Those are written below with a
comment naming the rule, so you can find them if the by-law changes.

HOW RS / RT / RM WORK (step 19)
The RD checker is written once with a "prefix". If you add rules RS-01 ... RS-33
to the Rules Table, numbered the SAME way as RD-01 ... RD-33, the RD checker
runs them for an RS property automatically. Until then the tool says those
zones have no rules loaded yet (NEED MORE INFO), and never guesses.
"""

from .engine import register
from .core import PASS, FAIL, NEED, FLAG, fmt

RD_LIKE = ("RD", "RS", "RT", "RM")    # zones that follow the RD numbering


# ---------------------------------------------------------------- shared helpers

def zone_ready(ctx):
    """Return the rule prefix to use ('RD', 'R', 'RS'...), or None after recording why not."""
    zone = ctx.zone
    if not zone:
        ctx.notes.append("Zone not given: zoning rules can't be checked until you pick the zone (or type the zone label).")
        _system_need(ctx, "Pick the zone (for example RD or R) so the zoning rules can be checked.")
        return None
    if zone == "R":
        return "R"
    if zone in RD_LIKE:
        if f"{zone}-02" in ctx.rules:
            return zone
        _system_need(ctx, f"Zone {zone} is not loaded yet: the Rules Table has no {zone}- rules. "
                          f"Add {zone}-01 to {zone}-33 (numbered like the RD rules) and re-import. "
                          "Until then, check with Toronto Building.")
        return None
    _system_need(ctx, f"Zone '{zone}' is outside this tool's scope (low-rise residential R and RD zones). "
                      "Check with Toronto Building.")
    return None


RESIDENTIAL = ("R",) + RD_LIKE         # the low-rise residential zones (Chapter 10) this tool's rules are written for


def outside_scope(ctx):
    """After all rules ran: if the zone isn't a low-rise residential zone (e.g. CR, CL, OS), the zoning rules
    we have don't apply there. Remove their results and say so plainly, instead of showing PASS/FAIL that
    could be wrong. Building Code results and other approvals (heritage, trees...) stay: they apply in any zone.
    Returns True if it happened."""
    zone = ctx.zone
    if not zone or zone in RESIDENTIAL:
        return False
    label = (ctx.get("zone_label") or "").strip()
    letters = label.split(" ")[0].split("(")[0] if label else zone
    ctx.results[:] = [r for r in ctx.results if r.get("group") not in ("Zoning", "Suites")]
    ctx.results.insert(0, {
        "rule_id": "ZONE", "status": FLAG, "title": "Zone outside this tool's scope",
        "category": "Zone",
        "message": (f"This property's zone ({letters}) isn't a low-rise residential zone, so the zoning rules in this tool "
                    "don't apply and no zoning results are shown. Other zones (like CR, commercial residential) have "
                    "their own rules in By-law 569-2013. Check with Toronto Building or a designer. "
                    "Building Code and other approval results below still apply."),
        "plain": (f"Your zone ({letters}) isn't a home zone this tool covers, so zoning isn't checked. "
                  "Ask Toronto Building which rules apply."),
        "limit": None, "value": letters, "unit": "", "section": "569-2013 Ch. 10 (residential zones)",
        "source": "Zoning 569-2013", "confidence": "High", "verified_vs_pdf": False,
        "link": "https://www.toronto.ca/zoning/", "group": "Zoning", "fix": None, "fix_data": None, "safety": False})
    ctx.notes.append(f"Zone {letters} is outside this tool's scope: zoning results were removed.")
    return True


def _system_need(ctx, message):
    """A NEED MORE INFO line that isn't tied to one rule (e.g. zone missing)."""
    if any(r["rule_id"] == "ZONE" for r in ctx.results):
        return
    ctx.results.append({"rule_id": "ZONE", "status": NEED, "title": "Zone needed for zoning checks",
                        "category": "Zone", "message": message, "limit": None, "value": None, "unit": "",
                        "section": "569-2013 Ch. 10", "source": "Zoning 569-2013", "confidence": "High",
                        "verified_vs_pdf": False, "link": "https://www.toronto.ca/zoning/",
                        "group": "Zoning", "fix": None, "fix_data": None, "safety": False})


def max_height(ctx, p):
    """Max building height (RD-02/RD-03 or R-02). Returns (limit, rule_id) or (None, rule_id)."""
    rid = f"{p}-02"
    default = ctx.limit(rid)                 # 10.0 m when there's no HT value
    ht = ctx.get("ht")
    if ht is None:
        return None, rid
    limit = default if ht == "none" else ht
    if ctx.is_houseplex():
        # RD-03 / R-02: houseplex = greater of HT value or 10.0 m
        hp_rule = f"{p}-03" if p in RD_LIKE else rid
        hp_default = ctx.limit(hp_rule) if p in RD_LIKE else default
        limit = max(limit, hp_default)
        rid = hp_rule
    return limit, rid


def side_rule_for_frontage(p, frontage):
    """RD-17 to RD-23: which side setback rule applies for this frontage.
    Frontage bands come from the 'Applies when' column of RD-17..RD-23."""
    bands = [(6, 17), (12, 18), (15, 19), (18, 20), (24, 21), (30, 22)]
    for upper, n in bands:
        if frontage < upper:
            return f"{p}-{n}"
    return f"{p}-23"


def required_house_side_setback(ctx):
    """The house's minimum side setback for this zone (used by G-22, G-29, GS-07). None if unknown."""
    zone = ctx.zone
    if zone == "R":
        if ctx.no("side_wall_openings"):
            return ctx.limit("R-11")
        return ctx.limit("R-10")
    if zone in RD_LIKE and ctx.num("lot_frontage") is not None:
        rid = side_rule_for_frontage(zone, ctx.num("lot_frontage"))
        return ctx.limit(rid)          # None if that zone's rules aren't loaded yet
    return None


def height_method(ctx):
    """G-01 is a measuring rule, not a limit: remind the user how height is measured."""
    if ctx.has("height"):
        ctx.add("G-01", FLAG, message="Check how you measured the height: from established grade (defined in Chapter 800) "
                                      "to the highest point of the building. A different starting point changes the result.")


def yes_no_rule(ctx, rule_id, key, bad_if, message_bad, message_ok, why=""):
    """For 'Prohibited if' / 'Yes/No' rules: FAIL when answer == bad_if."""
    if ctx.need(rule_id, [key], why=why):
        return
    if ctx.get(key) == bad_if:
        ctx.add(rule_id, FAIL, message=message_bad, fix_data={"kind": "yesno", "key": key})
    else:
        ctx.add(rule_id, PASS, message=message_ok)


def ask_if(ctx, rule_id, flag_key, why):
    """For rules that only apply if a feature exists. Returns True if we should check it."""
    if not ctx.has(flag_key):
        ctx.need(rule_id, [flag_key], why=why)
        return False
    return ctx.yes(flag_key)


# ---------------------------------------------------------------- main building: RD-like zones

@register("zone_main")
def zone_main(ctx):
    p = zone_ready(ctx)
    if p is None:
        return
    if p == "R":
        r_zone_main(ctx)
    else:
        rd_main(ctx, p)


def rd_main(ctx, p):
    houseplex = ctx.is_houseplex()

    # RD-01 permitted building types
    rid = f"{p}-01"
    if not ctx.need(rid, ["building_type"]):
        bt = ctx.get("building_type")
        if bt in ("Detached house", "Detached houseplex"):
            ctx.add(rid, PASS, message=f"{bt} is permitted.")
        elif bt in ("Townhouse", "Apartment building") and ctx.yes("major_street"):
            ctx.add(rid, PASS, message=f"{bt} is permitted on a lot on a major street.")
        elif bt in ("Townhouse", "Apartment building") and not ctx.has("major_street"):
            ctx.need(rid, ["major_street"], why=f"A {bt.lower()} is only permitted on a major street.")
        else:
            ctx.add(rid, FAIL, message=f"{bt} is not permitted in this zone.")

    # RD-02 / RD-03 height
    limit, hrid = max_height(ctx, p)
    if limit is None:
        ctx.need(hrid, ["ht"], why="The height limit depends on the Height Overlay (HT) value.")
    else:
        why = "No HT value, so 10.0 m applies." if ctx.get("ht") == "none" else f"HT value {fmt(ctx.get('ht'))} m."
        if houseplex:
            why += " Houseplex: greater of HT or 10.0 m."
        ctx.check_max(hrid, "height", limit, message=f"Maximum height {fmt(limit)} m ({why}) Yours: {fmt(ctx.num('height'))} m.")
    height_method(ctx)

    # RD-04 / RD-05 main wall height
    if limit is not None and not ctx.need(f"{p}-04", ["roof_type"], why="Main wall limit depends on the roof type."):
        flat = ctx.get("roof_type").startswith("Flat")
        rid = f"{p}-05" if flat else f"{p}-04"
        base = ctx.limit(rid)                          # 7.0 m (pitched) or 7.2 m (flat)
        mw_limit = max(base, limit - 2.5)              # "higher of base or (max height - 2.5 m)"
        ctx.check_max(rid, "main_wall_height", mw_limit,
                      message=f"Main wall max = higher of {fmt(base)} m or (max height {fmt(limit)} − 2.5) = {fmt(mw_limit)} m. "
                              f"Yours: {fmt(ctx.num('main_wall_height'))} m. Must be met for at least 70% of the side wall width.")
    elif limit is None:
        ctx.need(f"{p}-04", ["ht"], why="Main wall limit depends on the max height (HT value).")

    # RD-06 entrance height
    ctx.check_max(f"{p}-06", "entrance_height", ctx.limit(f"{p}-06"))

    # RD-07 dormers
    if ask_if(ctx, f"{p}-07", "has_dormers", "Dormer rule applies only if there are dormers."):
        ctx.check_max(f"{p}-07", "dormer_width_pct", ctx.limit(f"{p}-07"))

    # RD-08 storeys (not for houseplex)
    rid = f"{p}-08"
    if not houseplex:
        st = ctx.get("st")
        if st is None:
            ctx.need(rid, ["st"], why="Storey limit depends on the ST value on the Height Overlay Map.")
        elif st == "none":
            ctx.add(rid, PASS, message="No ST value on the map, so no storey limit.", value=ctx.num("storeys"))
        else:
            ctx.check_max(rid, "storeys", st)

    # RD-09 / RD-10 / RD-11 building length
    rd_length(ctx, p, houseplex)

    # RD-12 building depth (frontage <= 18.0 m)
    rid = f"{p}-12"
    fr = ctx.num("lot_frontage")
    if fr is None:
        ctx.need(rid, ["lot_frontage"], why="Depth rule applies when frontage is 18.0 m or less.")
    elif fr <= 18.0:
        ctx.check_max(rid, "building_depth", ctx.limit(rid))

    # RD-13 FSI
    rd_fsi(ctx, p, houseplex)

    # RD-14 lot coverage
    rid = f"{p}-14"
    cov = ctx.get("coverage_overlay")
    if cov is None:
        ctx.need(rid, ["coverage_overlay"], why="Lot coverage limit comes from the Lot Coverage Overlay map.")
    elif cov == "none":
        ctx.add(rid, PASS, value=ctx.num("lot_coverage"), message="No Lot Coverage Overlay value, so no coverage limit.")
    else:
        lim = cov
        note = f"Overlay value {fmt(cov)}%."
        if (houseplex or ctx.yes("has_secondary_suite")) and cov < ctx.limit(rid):
            lim = ctx.limit(rid)                     # 45%
            note += f" Houseplex/secondary suite: raised to {fmt(lim)}%."
        ctx.check_max(rid, "lot_coverage", lim, message=f"Maximum lot coverage {fmt(lim)}% ({note}) Yours: {fmt(ctx.num('lot_coverage'))}%.")

    # RD-15 front setback
    _front(ctx, f"{p}-15")

    # RD-16 rear setback: greater of 7.5 m or 25% of lot depth
    rid = f"{p}-16"
    base = ctx.limit(rid)
    if not ctx.need(rid, ["lot_depth", "rear_setback"], limit=None,
                    why=f"Rear setback = greater of {fmt(base)} m or 25% of lot depth."):
        depth = ctx.num("lot_depth")
        req = max(base, 0.25 * depth)
        ctx.check_min(rid, "rear_setback", req,
                      message=f"Needs the greater of {fmt(base)} m or 25% of {fmt(depth)} m = {fmt(req)} m. "
                              f"Yours: {fmt(ctx.num('rear_setback'))} m.")

    # RD-17 to RD-24 side setbacks
    rd_side(ctx, p)

    # RD-25 deep side setback on wide lots
    rid = f"{p}-25"
    if fr is not None and fr > 18.0:
        if not ctx.need(rid, ["building_length"], why="On lots wider than 18 m, parts deeper than 17 m need 7.5 m side setbacks."):
            if ctx.num("building_length") > 17.0:
                ctx.add(rid, FLAG, value=ctx.num("building_length"), limit=ctx.limit(rid),
                        message="Part of the building is deeper than 17.0 m from the front wall. That part needs "
                                f"{fmt(ctx.limit(rid))} m side setbacks. Check your drawings.")
            else:
                ctx.add(rid, PASS, value=ctx.num("building_length"), limit=ctx.limit(rid),
                        message="Building is no deeper than 17.0 m, so the 7.5 m rule isn't triggered.")

    # RD-26 corner lot street side
    rid = f"{p}-26"
    if ctx.yes("corner_lot") and fr is not None and fr >= 12.0:
        if not ctx.need(rid, ["neighbour_fronts_flank"]):
            if ctx.yes("neighbour_fronts_flank"):
                ctx.check_min(rid, "street_side_setback", ctx.limit(rid))
    elif not ctx.has("corner_lot"):
        ctx.need(rid, ["corner_lot"], why="Corner lots have a street-side setback rule.")

    # RD-33 one residential building per lot
    rid = f"{p}-33"
    if ctx.has("residential_buildings"):
        ctx.check_max(rid, "residential_buildings", ctx.limit(rid))


def _front(ctx, rid):
    """Front setback minimum. The neighbour-average rule (10.5.40.70(1)) may change it."""
    lim = ctx.limit(rid)
    ok = ctx.check_min(rid, "front_setback", lim,
                       message=f"Minimum {fmt(lim)} m unless the neighbour-average rule 10.5.40.70(1) applies "
                               f"(not yet built into this tool). Yours: {fmt(ctx.num('front_setback'))} m.")
    return ok


def rd_length(ctx, p, houseplex):
    rid9, rid10, rid11 = f"{p}-09", f"{p}-10", f"{p}-11"
    fr = ctx.num("lot_frontage")
    if fr is None:
        ctx.need(rid9, ["lot_frontage"], why="The length rule applies when frontage is 18.0 m or less.")
        return
    if fr > 18.0:
        return                                          # RD-25 handles wide lots
    limit = ctx.limit(rid9)                             # 17.0 m
    used = rid9
    msg_extra = ""
    depth = ctx.num("lot_depth")
    # RD-11: houseplex on deep lots -> 19.0 m
    if houseplex and depth is not None:
        deep = (depth >= 36 and fr < 10) or (depth >= 40 and fr >= 10)
        if deep:
            limit, used = ctx.limit(rid11), rid11
            msg_extra = " Houseplex on a deep lot: 19.0 m."
    # RD-10: one-storey extension may add 2.0 m (detached house, frontage > 12.0 to 18.0 m)
    if used == rid9 and 12.0 < fr <= 18.0 and ctx.get("building_type") == "Detached house":
        if ctx.yes("rd10_extension"):
            limit = limit + ctx.limit(rid10)
            msg_extra = f" Includes the {fmt(ctx.limit(rid10))} m one-storey extension allowance (RD-10)."
        elif not ctx.has("rd10_extension") and ctx.num("building_length") and ctx.num("building_length") > limit:
            ctx.need(rid10, ["rd10_extension"], why="A one-storey rear extension may add 2.0 m of length.")
    elif used == rid9 and fr <= 12.0:
        msg_extra = " (The 2.0 m extension in RD-10 is only for frontages over 12 m.)"
    ctx.check_max(used, "building_length", limit,
                  message=f"Maximum length {fmt(limit)} m.{msg_extra} Yours: {fmt(ctx.num('building_length'))} m.")


def rd_fsi(ctx, p, houseplex):
    rid = f"{p}-13"
    if houseplex or ctx.yes("has_secondary_suite"):
        ctx.add(rid, PASS, value=ctx.num("fsi"),
                message="The FSI limit doesn't apply to a houseplex or a house with a secondary suite.")
        return
    d = ctx.get("d")
    if d is None:
        ctx.need(rid, ["d"], why="FSI limit is the 'd' value on the zone label.")
        return
    if d == "none":
        ctx.add(rid, PASS, value=ctx.num("fsi"), message="No 'd' value on the zone label, so no FSI limit.")
        return
    if not ctx.has("has_secondary_suite") and not ctx.has("building_type"):
        ctx.need(rid, ["has_secondary_suite"], limit=d, why="The FSI limit doesn't apply if there's a secondary suite.")
        return
    ctx.check_max(rid, "fsi", d, unit="")


def rd_side(ctx, p):
    fr = ctx.num("lot_frontage")
    if fr is None:
        ctx.need(f"{p}-18", ["lot_frontage"], why="The side setback depends on lot frontage.")
        return
    rid = side_rule_for_frontage(p, fr)
    req = ctx.limit(rid)
    if ctx.need(rid, ["side_setback"], limit=req):
        return
    a = ctx.num("side_setback")
    b = ctx.num("side_setback_other")
    small, big = (min(a, b), max(a, b)) if b is not None else (a, None)
    if small >= req - 1e-9:
        ctx.add(rid, PASS, value=small, limit=req,
                message=f"Frontage {fmt(fr)} m needs {fmt(req)} m side setbacks. Yours: {fmt(small)} m.")
        return
    # RD-24: frontage 12.0 to < 18.0 m -> one side may be 0.3 m less if the other is 0.3 m more
    adj = ctx.limit(f"{p}-24")
    if 12.0 <= fr < 18.0 and small >= req - adj - 1e-9:
        if big is None:
            ctx.need(rid, ["side_setback_other"], limit=req,
                     why=f"One side may be up to {fmt(adj)} m less if the other side is that much more (RD-24).")
            return
        shortfall = req - small
        if big >= req + shortfall - 1e-9:
            ctx.add(f"{p}-24", PASS, value=small, limit=round(req - adj, 2), unit="m",
                    message=f"{fmt(small)} m is under the usual {fmt(req)} m ({rid}), but one side may be up to "
                            f"{fmt(adj)} m less because the other side is {fmt(big)} m (at least {fmt(req + shortfall)} m).")
            return
    ctx.add(rid, FAIL, value=small, limit=req,
            message=f"Frontage {fmt(fr)} m needs {fmt(req)} m side setbacks. Yours: {fmt(small)} m.",
            fix_data={"kind": "min", "key": "side_setback", "value": small, "limit": req})


@register("zone_lot")
def zone_lot(ctx):
    """Lot frontage and area (new house / new lot)."""
    p = zone_ready(ctx)
    if p is None:
        return
    if p == "R":
        f = ctx.get("f")
        lim = ctx.limit("R-12") if f in (None, "none") else f
        if f is None:
            ctx.need("R-12", ["f"], why="Minimum frontage is the 'f' value (6.0 m if none).")
        else:
            ctx.check_min("R-12", "lot_frontage", lim)
        return
    rid = f"{p}-27"
    f = ctx.get("f")
    if f is None:
        ctx.need(rid, ["f"], why="Minimum frontage is the 'f' value (12.0 m if none).")
        min_front = None
    else:
        min_front = ctx.limit(rid) if f == "none" else f
        ctx.check_min(rid, "lot_frontage", min_front)
    rid = f"{p}-28"
    a = ctx.get("a")
    if a is None:
        ctx.need(rid, ["a"], why="Minimum lot area is the 'a' value (or min frontage × 30 m).")
    elif a == "none":
        if min_front is not None:
            ctx.check_min(rid, "lot_area", min_front * 30,
                          message=f"No 'a' value: min lot area = min frontage {fmt(min_front)} m × 30 m = {fmt(min_front * 30)} m². "
                                  f"Yours: {fmt(ctx.num('lot_area'))} m².")
    else:
        ctx.check_min(rid, "lot_area", a)


@register("upper_platforms")
def upper_platforms(ctx):
    """RD-31: balconies at/above the 2nd storey (detached house)."""
    p = zone_ready(ctx)
    if p is None or p == "R" or ctx.is_houseplex():
        return
    rid = f"{p}-31"
    if ctx.need(rid, ["upper_platforms"], why="Tell us how many balconies/decks are at or above the 2nd storey (0 if none)."):
        return
    n = ctx.num("upper_platforms")
    if n == 0:
        ctx.add(rid, PASS, value=0, message="No platforms at or above the 2nd storey.")
        return
    if n > 4:                                   # "max 4 total" (from the rule text)
        ctx.add(rid, FAIL, value=n, limit=4, unit="platforms", message=f"Maximum 4 platforms; you have {fmt(n)}.",
                fix_data={"kind": "max", "key": "upper_platforms", "value": n, "limit": 4})
        return
    if ctx.no("upper_platforms_one_per_side"):
        ctx.add(rid, FAIL, message="Only one platform is allowed on each side.")
        return
    ctx.check_max(rid, "upper_platform_area", ctx.limit(rid))


# ---------------------------------------------------------------- R zone (step 5)

def r_zone_main(ctx):
    houseplex = ctx.is_houseplex()

    # R-01 permitted building types
    if not ctx.need("R-01", ["building_type"]):
        ctx.add("R-01", PASS, message=f"{ctx.get('building_type')} is permitted in the R zone.")

    # R-02 height
    limit, rid = max_height(ctx, "R")
    if limit is None:
        ctx.need("R-02", ["ht"], why="The height limit depends on the Height Overlay (HT) value.")
    else:
        ctx.check_max("R-02", "height", limit)
        height_method(ctx)
        # R-03 main wall height
        mw = max(ctx.limit("R-03"), limit - 2.5)
        ctx.check_max("R-03", "main_wall_height", mw,
                      message=f"Main wall max = higher of {fmt(ctx.limit('R-03'))} m or (max height − 2.5) = {fmt(mw)} m. "
                              f"Yours: {fmt(ctx.num('main_wall_height'))} m.")

    # R-04 roof slope above 2nd storey (detached house): max 5 vertical : 3 horizontal
    if ctx.get("building_type") == "Detached house" and ctx.has("roof_slope"):
        ctx.check_max("R-04", "roof_slope", round(5 / 3, 2), unit="",
                      message=f"Max slope 5:3 (= 1.67). Yours: {fmt(ctx.num('roof_slope'))}.")

    # R-05 building depth (houseplex deep lots 19.0 m, from the Notes column)
    lim = ctx.limit("R-05")
    fr, depth = ctx.num("lot_frontage"), ctx.num("lot_depth")
    if houseplex and fr is not None and depth is not None and ((depth >= 36 and fr < 10) or (depth >= 40 and fr >= 10)):
        lim = 19.0
    ctx.check_max("R-05", "building_depth", lim)

    # R-06 / R-07 FSI
    r_fsi(ctx, houseplex)

    # R-08 front, R-09 rear
    _front(ctx, "R-08")
    ctx.check_min("R-09", "rear_setback", ctx.limit("R-09"))

    # R-10 / R-11 side
    if not ctx.need("R-10", ["side_setback"], limit=ctx.limit("R-10")):
        s = ctx.num("side_setback")
        if ctx.num("side_setback_other") is not None:
            s = min(s, ctx.num("side_setback_other"))
        if s >= ctx.limit("R-10") - 1e-9:
            ctx.add("R-10", PASS, value=s, limit=ctx.limit("R-10"), message=f"Minimum 0.9 m; yours is {fmt(s)} m.")
        elif s >= ctx.limit("R-11") - 1e-9:
            if ctx.no("side_wall_openings"):
                ctx.add("R-11", PASS, value=s, limit=ctx.limit("R-11"),
                        message="0.45 m is allowed because that wall has no windows or doors.")
            elif ctx.yes("side_wall_openings"):
                ctx.add("R-10", FAIL, value=s, limit=ctx.limit("R-10"),
                        message="0.9 m needed because that wall has windows or doors (0.45 m only without openings).",
                        fix_data={"kind": "min", "key": "side_setback", "value": s, "limit": ctx.limit("R-10")})
            else:
                ctx.need("R-11", ["side_wall_openings"], limit=ctx.limit("R-11"),
                         why="0.45 m is allowed only if that wall has no windows or doors.")
        else:
            rid = "R-11" if ctx.no("side_wall_openings") else "R-10"
            ctx.add(rid, FAIL, value=s, limit=ctx.limit(rid), message=f"Minimum {fmt(ctx.limit(rid))} m; yours is {fmt(s)} m.",
                    fix_data={"kind": "min", "key": "side_setback", "value": s, "limit": ctx.limit(rid)})


def r_fsi(ctx, houseplex):
    if houseplex or ctx.yes("has_secondary_suite"):
        ctx.add("R-06", PASS, value=ctx.num("fsi"),
                message="The FSI limit doesn't apply to a houseplex or a house with a secondary suite.")
        return
    d = ctx.get("d")
    if d is None:
        ctx.need("R-06", ["d"], limit=ctx.limit("R-06"), why="FSI limit is 0.6 if the zone label has no 'd' value.")
        return
    if not ctx.has("has_secondary_suite"):
        ctx.need("R-06", ["has_secondary_suite"], why="The FSI limit doesn't apply if there's a secondary suite.")
        return
    lim = ctx.limit("R-06") if d == "none" else d
    # R-07: pre-1953 house, rear addition: up to 0.69
    if (lim == ctx.limit("R-06") and ctx.yes("built_before_1953") and ctx.yes("pre1953_addition_ok")
            and "Rear addition" in ctx.project):
        ctx.check_max("R-07", "fsi", ctx.limit("R-07"), unit="",
                      message=f"Pre-1953 house, rear addition: total FSI up to {fmt(ctx.limit('R-07'))}. Yours: {fmt(ctx.num('fsi'))}.")
        return
    ctx.check_max("R-06", "fsi", lim, unit="")


# ---------------------------------------------------------------- general rules (G-) for all zones

@register("projections")
def projections(ctx):
    """Things that stick out into setbacks: G-02, G-09 to G-12, G-31."""
    if ctx.has("rooftop_element"):
        ctx.check_max("G-02", "rooftop_element", ctx.limit("G-02"))
    if ask_if(ctx, "G-09", "has_stairs_in_setback", "Applies if exterior stairs are inside a required setback."):
        ctx.check_max("G-09", "stairs_width", ctx.limit("G-09"))
        ctx.check_min("G-09", "stairs_to_lot_line", 0.6,               # "at least 0.6 m from lot line"
                      message=f"Stairs must be at least 0.6 m from the lot line. Yours: {fmt(ctx.num('stairs_to_lot_line'))} m.")
    if ask_if(ctx, "G-10", "has_bay_window", "Applies if bay/box windows stick into a setback."):
        if not ctx.need("G-10", ["bay_location"]):
            if ctx.get("bay_location") == "Side":
                ctx.check_max("G-10", "bay_projection", 0.6,           # side: up to 0.6 m (rule text)
                              message=f"Side bay window: max 0.6 m projection, ≤30% of the wall, ≥0.6 m from the lot line. "
                                      f"Yours: {fmt(ctx.num('bay_projection'))} m.")
                if ctx.has("bay_wall_pct"):
                    ctx.check_max("G-10", "bay_wall_pct", 30, unit="%")
            else:
                ctx.check_max("G-10", "bay_projection", ctx.limit("G-10"))
                if ctx.has("bay_wall_pct"):
                    ctx.check_max("G-10", "bay_wall_pct", 65, unit="%")
    if ask_if(ctx, "G-11", "has_eaves", "Applies if eaves stick into a setback."):
        ctx.check_max("G-11", "eaves_projection", ctx.limit("G-11"))
        ctx.check_min("G-11", "eaves_to_lot_line", 0.3,
                      message=f"Eaves must stay at least 0.3 m from the lot line. Yours: {fmt(ctx.num('eaves_to_lot_line'))} m.")
    if ask_if(ctx, "G-12", "has_ac", "Applies if there's an outdoor air conditioner or heat pump."):
        loc = ctx.get("ac_location")
        if ctx.need("G-12", ["ac_location"]):
            return
        if loc == "Front yard":
            ctx.check_min("G-31", "ac_to_front_line", ctx.limit("G-31"))
        elif loc == "Side yard (above first storey)":
            ctx.add("G-12", FAIL, message="An AC unit may project into the side setback only if not above the first storey.")
        else:
            ctx.check_max("G-12", "ac_projection", ctx.limit("G-12"))


def _landscape_front(ctx):
    fr = ctx.num("lot_frontage")
    if fr is None:
        ctx.need("G-13", ["lot_frontage"], why="Front landscaping % depends on frontage.")
    elif fr < 6.0:
        ctx.add("G-13", FLAG, message="Frontage under 6 m: all of the front yard except the driveway must be landscaped. "
                                      "Check your plan.")
    else:
        lim = ctx.limit("G-13") if fr < 15.0 else 60      # 60% for frontage >= 15 m (Notes column)
        ctx.check_min("G-13", "front_landscape_pct", lim,
                      message=f"Frontage {fmt(fr)} m: at least {fmt(lim)}% of the front yard must be landscaped. "
                              f"Yours: {fmt(ctx.num('front_landscape_pct'))}%.")
    if ctx.get("building_type") in (None, "Detached house", "Semi-detached house", "Townhouse",
                                    "Detached houseplex", "Semi-detached houseplex"):
        ctx.check_min("G-14", "front_soft_pct", ctx.limit("G-14"))
    if ctx.yes("corner_lot"):
        ctx.check_min("G-16", "street_side_landscape_pct", ctx.limit("G-16"))


@register("landscape_front")
def landscape_front(ctx):
    _landscape_front(ctx)


@register("landscape")
def landscape(ctx):
    _landscape_front(ctx)
    fr = ctx.num("lot_frontage")
    if fr is None:
        ctx.need("G-15", ["lot_frontage"], why="Rear soft landscaping % depends on frontage.")
    else:
        lim = ctx.limit("G-15") if fr > 6.0 else 25        # 25% if frontage <= 6 m (rule text)
        ctx.check_min("G-15", "rear_soft_pct", lim)


@register("ancillary")
def ancillary(ctx):
    """Sheds, garages and other accessory buildings: G-17 to G-26, R-13, R-14."""
    yes_no_rule(ctx, "G-17", "anc_in_front_yard", True,
                "Accessory buildings are not allowed in the front yard.", "Not in the front yard.")
    yes_no_rule(ctx, "G-18", "anc_living", True,
                "No one may live or sleep in an accessory building (garden/laneway suites have their own rules).",
                "No living space in it.")
    ctx.check_max("G-19", "anc_storeys", ctx.limit("G-19"))

    # G-20 height: 2.5 m if within 1.8 m of the house, else 4.0 m
    if not ctx.need("G-20", ["anc_height", "anc_to_house"], why="Height limit depends on distance to the house."):
        close_to_house = ctx.num("anc_to_house") < 1.8
        lim = 2.5 if close_to_house else ctx.limit("G-20")
        ctx.check_max("G-20", "anc_height", lim,
                      message=f"{'Within' if close_to_house else 'At least'} 1.8 m of the house: max height {fmt(lim)} m. "
                              f"Yours: {fmt(ctx.num('anc_height'))} m.")

    # G-21 rear setback
    depth, h, area = ctx.num("lot_depth"), ctx.num("anc_height"), ctx.num("anc_area")
    lim = ctx.limit("G-21")
    if depth is not None and depth > 45 and ((h or 0) > 2.5 or (area or 0) > 10):
        lim = max(lim, (h or 0) / 2)                       # deep lots: half the height (Notes column)
    ctx.check_min("G-21", "anc_rear_setback", lim)

    # G-22 side setback
    if ctx.yes("anc_in_side_yard") or (ctx.num("anc_to_house") is not None and ctx.num("anc_to_house") < 1.8):
        req = required_house_side_setback(ctx)
        if req is None:
            ctx.need("G-22", ["lot_frontage", "zone"], why="Close to the house or in a side yard: same side setback as the house.")
        else:
            ctx.check_min("G-22", "anc_side_setback", req,
                          message=f"In a side yard or within 1.8 m of the house: same side setback as the house ({fmt(req)} m). "
                                  f"Yours: {fmt(ctx.num('anc_side_setback'))} m.")
    else:
        ctx.check_min("G-22", "anc_side_setback", ctx.limit("G-22"))

    # G-23 separation from the house if over 2.5 m tall or over 10 m²
    if h is None and area is None:
        ctx.need("G-23", ["anc_height", "anc_area"], why="Must be 1.8 m from the house if over 2.5 m tall or over 10 m².")
    elif (h or 0) > 2.5 or (area or 0) > 10:
        ctx.check_min("G-23", "anc_to_house", ctx.limit("G-23"))
    elif h is not None and area is not None:
        ctx.add("G-23", PASS, message="2.5 m tall or less and 10 m² or less: no separation needed.")
    else:
        ctx.need("G-23", ctx.missing("anc_height", "anc_area"))

    # G-24 total floor area
    fr = ctx.num("lot_frontage")
    if fr is None:
        ctx.need("G-24", ["lot_frontage"], why="Total accessory floor area limit depends on frontage.")
    else:
        lim = ctx.limit("G-24") if fr >= 12.0 else 40      # 40 m² if frontage < 12 m (Notes column)
        key = "anc_total_area" if ctx.has("anc_total_area") else "anc_area"
        ctx.check_max("G-24", key, lim, message=f"Total accessory floor area max {fmt(lim)} m². Yours: {fmt(ctx.num(key))} m².")
        if ctx.num("anc_to_house") is not None and ctx.num("anc_to_house") < 1.8 and area is not None:
            ctx.check_max("G-24", "anc_area", 10, message=f"Within 1.8 m of the house: max 10 m². Yours: {fmt(area)} m².")

    # G-25 / R-13 coverage
    if ctx.zone == "R":
        ctx.check_max("R-13", "anc_coverage", ctx.limit("R-13"))
    else:
        ctx.check_max("G-25", "anc_coverage", ctx.limit("G-25"))

    # G-26 lane setback, R-14 parking setback
    if ctx.yes("lane"):
        ctx.check_min("G-26", "anc_to_lane_line", ctx.limit("G-26"))
        if ctx.has("anc_to_lane_centre"):
            ctx.check_min("G-26", "anc_to_lane_centre", 2.5,
                          message=f"At least 2.5 m from the original lane centreline. Yours: {fmt(ctx.num('anc_to_lane_centre'))} m.")
    elif not ctx.has("lane"):
        ctx.need("G-26", ["lane"], why="Buildings near a lane have a lane setback.")
    if ctx.zone == "R" and ctx.yes("anc_parking") and (ctx.yes("lane") or ctx.yes("corner_lot")):
        ctx.check_min("R-14", "anc_to_lane_line", ctx.limit("R-14"))


@register("garage")
def garage(ctx):
    """Garage extras: door width and parking access."""
    fr = ctx.num("lot_frontage")
    if fr is not None and fr < 24.0 and ctx.has("garage_door_width"):
        ctx.check_max("G-37", "garage_door_width", ctx.limit("G-37"))
    r_parking_access(ctx)


def r_parking_access(ctx):
    if ctx.zone != "R":
        return
    fr = ctx.num("lot_frontage")
    if fr is not None and fr <= ctx.limit("R-15") and ctx.has("garage_in_front_wall"):
        yes_no_rule(ctx, "R-15", "garage_in_front_wall", True,
                    f"Frontage {fmt(fr)} m (7.6 m or less): no vehicle entrance through the front main wall.",
                    "No vehicle entrance in the front wall.")
    if ctx.yes("corner_lot") or ctx.yes("lane"):
        if not ctx.need("R-16", ["parking_access"]):
            if ctx.get("parking_access") == "From the front street":
                ctx.add("R-16", FAIL, message="Corner lot or lane lot: parking access must be from the flanking street or lane.")
            else:
                ctx.add("R-16", PASS, message="Parking access is from the flanking street or lane.")


@register("deck")
def deck(ctx):
    """Decks and platforms: G-04 to G-08, G-27."""
    if ctx.need("G-04", ["deck_level"], why="Deck height limits depend on the deck level."):
        return
    upper = ctx.get("deck_level").startswith("Second")
    if upper:
        ctx.check_max("G-05", "deck_above_floor", ctx.limit("G-05"))
        upper_platforms(ctx)
    else:
        ctx.check_max("G-04", "deck_height", ctx.limit("G-04"))
    _deck_encroach(ctx, upper)
    # G-27 setback = greater of 0.3 m or deck height
    if ctx.get("deck_location") in ("Rear yard", "Side yard") or not ctx.has("deck_location"):
        h = ctx.num("deck_height") or 0
        lim = max(ctx.limit("G-27"), h)
        ctx.check_min("G-27", "deck_setback", lim,
                      message=f"Setback = greater of 0.3 m or the deck height ({fmt(h)} m) = {fmt(lim)} m. "
                              f"Yours: {fmt(ctx.num('deck_setback'))} m.")


def _deck_encroach(ctx, upper=False):
    if ctx.need("G-07", ["deck_location"], why="Encroachment limits depend on which yard the deck is in."):
        return
    loc = ctx.get("deck_location")
    if loc == "Front yard":
        _encroach_formula(ctx, "G-06", "front", 1.5 if upper else ctx.limit("G-06"), _req_front(ctx))
    elif loc == "Rear yard":
        _encroach_formula(ctx, "G-07", "rear", ctx.limit("G-07"), _req_rear(ctx))
    else:
        if upper and not ctx.yes("corner_lot"):
            ctx.add("G-08", FAIL, message="Side-yard platforms above the first storey are only allowed if the side yard abuts a street.")
            return
        ctx.check_max("G-08", "deck_encroachment", ctx.limit("G-08"))
        ctx.check_min("G-08", "deck_to_side_line", 0.3,
                      message=f"Must stay at least 0.3 m from the side lot line. Yours: {fmt(ctx.num('deck_to_side_line'))} m.")


def _req_front(ctx):
    rid = "R-08" if ctx.zone == "R" else f"{ctx.zone}-15"
    return ctx.limit(rid) if rid in ctx.rules else None


def _req_rear(ctx):
    if ctx.zone == "R":
        return ctx.limit("R-09")
    rid = f"{ctx.zone}-16"
    if rid in ctx.rules and ctx.num("lot_depth") is not None:
        return max(ctx.limit(rid), 0.25 * ctx.num("lot_depth"))
    return None


def _encroach_formula(ctx, rid, yard, cap, required_setback):
    if required_setback is None:
        ctx.need(rid, ["zone", "lot_depth"] if yard == "rear" else ["zone"],
                 why=f"Encroachment = lesser of {fmt(cap)} m or 50% of the required {yard} setback.")
        return
    lim = min(cap, 0.5 * required_setback)
    ctx.check_max(rid, "deck_encroachment", lim,
                  message=f"May stick into the {yard} setback the lesser of {fmt(cap)} m or 50% of {fmt(required_setback)} m "
                          f"= {fmt(lim)} m. Yours: {fmt(ctx.num('deck_encroachment'))} m.")


@register("porch")
def porch(ctx):
    """Front porch / front addition: entrance height, front encroachment, platform height."""
    p = zone_ready(ctx)
    if p is not None and p != "R":
        ctx.check_max(f"{p}-06", "entrance_height", ctx.limit(f"{p}-06"))
    ctx.check_max("G-04", "deck_height", ctx.limit("G-04"))
    _encroach_formula(ctx, "G-06", "front", ctx.limit("G-06"), _req_front(ctx))


@register("pool")
def pool(ctx):
    """Pools: G-28 to G-30."""
    # G-28 rear setback: 1.2 m (through lot 25.0 m, corner lot 3.0 m -- from the rule text)
    if ctx.need("G-28", ["corner_lot", "through_lot"], why="Pool rear setback is different for corner and through lots."):
        pass
    else:
        if ctx.yes("through_lot"):
            lim, kind = 25.0, "through lot"
        elif ctx.yes("corner_lot"):
            lim, kind = 3.0, "corner lot"
        else:
            lim, kind = ctx.limit("G-28"), "regular lot"
        ctx.check_min("G-28", "pool_rear_setback", lim,
                      message=f"{kind.capitalize()}: pool needs {fmt(lim)} m from the rear lot line. "
                              f"Yours: {fmt(ctx.num('pool_rear_setback'))} m.")
    # G-29 side setback = greater of 1.2 m or the house's side setback
    house = required_house_side_setback(ctx)
    if house is None:
        ctx.need("G-29", ["zone", "lot_frontage"], why="Pool side setback = greater of 1.2 m or the house's side setback.")
    else:
        lim = max(ctx.limit("G-29"), house)
        note = ""
        if ctx.yes("pool_street_side"):
            if ctx.num("street_side_setback") is None:
                ctx.need("G-29", ["street_side_setback"], why="Street side: the house's setback + 1.5 m.")
                lim = None
            else:
                lim = ctx.num("street_side_setback") + 1.5
                note = " (street side: house setback + 1.5 m)"
        if lim is not None:
            ctx.check_min("G-29", "pool_side_setback", lim,
                          message=f"Pool side setback {fmt(lim)} m{note}. Yours: {fmt(ctx.num('pool_side_setback'))} m.")
    # G-30 water area <= 15% of lot area
    if not ctx.need("G-30", ["pool_area", "lot_area"]):
        lim = ctx.limit("G-30") / 100 * ctx.num("lot_area")
        ctx.check_max("G-30", "pool_area", lim, unit="m²",
                      message=f"Max water area = 15% of {fmt(ctx.num('lot_area'))} m² = {fmt(lim)} m². Yours: {fmt(ctx.num('pool_area'))} m².")


@register("driveway")
def driveway(ctx):
    """Driveways and parking: G-32 to G-37, R-15, R-16."""
    yes_no_rule(ctx, "G-32", "front_yard_parking", True,
                "Parking in the front yard is only allowed on a permitted driveway (a parking pad needs a City licence, Ch. 918).",
                "No front-yard parking outside the driveway.")
    if ctx.has("rear_parking_spaces"):
        ctx.check_max("G-33", "rear_parking_spaces", ctx.limit("G-33"))
    fr = ctx.num("lot_frontage")
    if fr is None:
        ctx.need("G-35", ["lot_frontage"], why="Driveway width limit depends on frontage.")
    elif not ctx.need("G-35" if 6 <= fr <= 23 else ("G-34" if fr < 6 else "G-36"), ["driveway_width"]):
        w = ctx.num("driveway_width")
        if fr < 6.0:
            rid = "G-34"
            if w < 2.0:
                ctx.check_min(rid, "driveway_width", 2.0)
            else:
                ctx.check_max(rid, "driveway_width", ctx.limit(rid))
        else:
            rid = "G-35" if fr <= 23.0 else "G-36"
            cap = ctx.limit(rid)                       # 6.0 m or 9.0 m
            behind = 2.6 if ctx.yes("all_parking_rear") else ctx.num("parking_width_behind_wall")
            if w < 2.0:
                ctx.check_min(rid, "driveway_width", 2.0)
            elif w > cap:
                ctx.check_max(rid, "driveway_width", cap,
                              message=f"Maximum {fmt(cap)} m (or less: the width of the parking behind the front wall). "
                                      f"Yours: {fmt(w)} m.")
            elif behind is None:
                ctx.need(rid, ["parking_width_behind_wall"], limit=cap,
                         why=f"Driveway max = lesser of {fmt(cap)} m or the width of the parking behind the front wall.")
            else:
                lim = min(cap, behind)
                ctx.check_max(rid, "driveway_width", lim,
                              message=f"Max = lesser of {fmt(cap)} m or {fmt(behind)} m (parking behind the front wall) = "
                                      f"{fmt(lim)} m. Yours: {fmt(w)} m.")
    if fr is not None and fr < 24.0 and ctx.has("garage_door_width"):
        ctx.check_max("G-37", "garage_door_width", ctx.limit("G-37"))
    r_parking_access(ctx)


@register("solar")
def solar(ctx):
    ctx.check_max("G-03", "solar_above_height", ctx.limit("G-03"))
    if ctx.yes("solar_in_front"):
        ctx.add("G-03", FAIL, message="Rooftop solar can't be in the front yard or street-side yard.")
