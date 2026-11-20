"""'What can I build?': the rules in reverse.

Instead of checking a design you already have, you give the lot (zone, overlay
values, frontage, depth...) and this works out the BIGGEST design the rules allow:
  - a main house / rear addition envelope (RD-, R- rules)
  - a garden suite (GS- rules)
  - a laneway suite (LS- rules), if the lot touches a lane for 3.5 m or more
  - a multiplex (RD-29, RD-30, ON-01)

Every number comes from the same Rules Table limits the checker uses (ctx.limit()),
so if you change a limit in the spreadsheet, this changes too.

Then it PROVES the answer: it builds that biggest design as form answers and runs
it through the normal checker (engine.run). If any rule fails, it says so.
Missing lot facts are listed as "still needed", never guessed.
"""

from . import engine  # noqa: F401  (load the engine first: it loads the rule modules in the right order)
from .core import Context, FAIL, fmt
from .zoning import RD_LIKE, side_rule_for_frontage


def _r(x):
    return round(x + 1e-9, 2) if isinstance(x, (int, float)) else x


def calculate(inputs, city="toronto"):
    from .engine import run          # imported here to avoid a circular import
    ctx = Context(inputs, city)
    zone, fr, depth, area = ctx.zone, ctx.num("lot_frontage"), ctx.num("lot_depth"), ctx.num("lot_area")
    if area is None and fr is not None and depth is not None:
        area = fr * depth                                    # rectangle assumption, said in the notes
        area_note = f"Lot area worked out as {fmt(fr)} × {fmt(depth)} m = {fmt(area)} m² (assumes a rectangle)."
    else:
        area_note = ""
    out = {"zone": zone, "options": [], "needed": [], "notes": [area_note] if area_note else []}

    if ctx.yes("grey_property"):
        out["stop"] = ("This lot is grey on the zoning map (old by-law). The rules here don't apply. "
                       "Contact Toronto Building.")
        return out
    if zone not in ("R",) + RD_LIKE or (zone in RD_LIKE and f"{zone}-02" not in ctx.rules):
        out["stop"] = f"Zone '{zone or '?'}' isn't covered yet (this tool knows the R and RD zones)."
        return out
    for key, label in (("lot_frontage", "lot frontage"), ("lot_depth", "lot depth"), ("ht", "height overlay (HT)")):
        if not ctx.has(key):
            out["needed"].append(label)
    if out["needed"]:
        return out

    p = zone
    ht = ctx.get("ht")
    if p == "R":
        max_h = ctx.limit("R-02") if ht == "none" else ht
        front, rear, side = ctx.limit("R-08"), ctx.limit("R-09"), ctx.limit("R-10")
        side_rule, depth_rule, depth_max = "R-10", "R-05", ctx.limit("R-05")
        length_max = None
        d = ctx.get("d")
        fsi = ctx.limit("R-06") if d in (None, "none") else d
        wall = max(ctx.limit("R-03"), max_h - 2.5)
        rules_used = ["R-02", "R-03", "R-05", "R-06", "R-08", "R-09", "R-10"]
    else:
        max_h = ctx.limit(f"{p}-02") if ht == "none" else ht
        front = ctx.limit(f"{p}-15")
        rear = max(ctx.limit(f"{p}-16"), 0.25 * depth)
        side_rule = side_rule_for_frontage(p, fr)
        side = ctx.limit(side_rule)
        depth_rule, depth_max = f"{p}-12", (ctx.limit(f"{p}-12") if fr <= 18 else None)
        length_max = ctx.limit(f"{p}-09") if fr <= 18 else None
        d = ctx.get("d")
        fsi = d if isinstance(d, (int, float)) else None
        wall = max(ctx.limit(f"{p}-04"), max_h - 2.5)
        rules_used = [f"{p}-02", f"{p}-04", side_rule, f"{p}-15", f"{p}-16"] + ([f"{p}-09", f"{p}-12"] if fr <= 18 else [])
        if d is None:
            out["notes"].append("Add the zone label so we know the floor space limit ('d' value).")

    st = ctx.get("st")
    storeys = st if isinstance(st, (int, float)) else (3 if max_h >= 10 else 2)   # practical storeys within the height
    storey_note = "storey limit from the ST overlay" if isinstance(st, (int, float)) else "about 3 floors fit in 10 m (no ST limit)"

    # ---- 1. biggest house / addition envelope
    width = fr - 2 * side
    house_depth = depth - front - rear
    if depth_max is not None:
        house_depth = min(house_depth, depth_max)
    if length_max is not None:
        house_depth = min(house_depth, length_max)
    footprint = max(0, width) * max(0, house_depth)
    cov = ctx.get("coverage_overlay")
    cov_cap = None
    if isinstance(cov, (int, float)) and area:
        cov_cap = cov / 100 * area
        if footprint > cov_cap:
            footprint = cov_cap
    gfa_by_fsi = fsi * area if (fsi is not None and area) else None
    gfa = min(footprint * storeys, gfa_by_fsi) if gfa_by_fsi is not None else footprint * storeys
    house = {
        "kind": "house", "title": "Biggest house or addition",
        "headline": f"{fmt(_r(width))} m wide × {fmt(_r(house_depth))} m deep, up to {fmt(max_h)} m tall",
        "facts": [
            ["Footprint", f"up to {fmt(_r(footprint))} m²" + (" (lot coverage limit)" if cov_cap and footprint == cov_cap else "")],
            ["Total floor area", f"up to {fmt(_r(gfa))} m²" + (f" (FSI {fmt(fsi)} × lot area)" if gfa_by_fsi is not None and gfa == gfa_by_fsi else f" ({fmt(storeys)} floors × footprint; {storey_note})")],
            ["Height", f"{fmt(max_h)} m to the top; side walls up to {fmt(_r(wall))} m"],
            ["Setbacks", f"front {fmt(front)} m · back {fmt(_r(rear))} m · sides {fmt(side)} m"],
        ],
        "rules": rules_used,
        "design": {"project_type": "Rear addition (1 or 2 storey)", "building_type": "Detached house",
                   "height": max_h, "main_wall_height": _r(wall), "roof_type": "Pitched", "storeys": storeys,
                   "front_setback": front, "rear_setback": _r(rear), "side_setback": side, "side_setback_other": side,
                   "building_length": _r(house_depth), "building_depth": _r(house_depth),
                   "lot_coverage": _r(footprint / area * 100) if area else None,
                   "fsi": _r(gfa / area) if area else None, "has_secondary_suite": False},
    }
    # Lot-size rules apply to a NEW house, not to an addition to the house that's already there
    if p in RD_LIKE:
        f_val, a_val = ctx.get("f"), ctx.get("a")
        min_f = ctx.limit(f"{p}-27") if f_val in (None, "none") else f_val
        min_a = (min_f * 30) if a_val in (None, "none") else a_val
        short = []
        if fr < min_f:
            short.append(f"narrower than the {fmt(min_f)} m minimum ({p}-27)")
        if area and area < min_a:
            short.append(f"smaller than the {fmt(min_a)} m² minimum ({p}-28)")
        if short:
            house["facts"].append(["New house?", "This lot is " + " and ".join(short) + ". An addition is fine, but a brand-new "
                                   "replacement house would need a minor variance for lot size."])
    out["options"].append(house)

    # ---- 2. biggest garden suite (behind the house)
    gs_side = min(max(ctx.limit("GS-05"), 0.10 * fr), 3.0)         # side with windows (GS-05)
    gs_width = fr - 2 * gs_side
    gs_rear = ctx.limit("GS-03")
    house_rear = ctx.num("rear_setback")                           # where the house's back wall is now
    gs = {"kind": "garden", "title": "Biggest garden suite", "rules": ["GS-03", "GS-05", "GS-10", "GS-11", "GS-12", "GS-13", "GS-15", "GS-16", "GS-17"]}
    if house_rear is None:
        gs["headline"] = "Tell us the house's current rear setback to size this"
        gs["facts"] = [["Still needed", "Space between the back of the house and the back lot line (Step 4 or the field below)"]]
        gs["needed"] = ["rear_setback"]
    else:
        two = {"h": ctx.limit("GS-12"), "sep": ctx.limit("GS-10"), "storeys": 2, "gfa": ctx.limit("GS-15")}
        one = {"h": ctx.limit("GS-11"), "sep": ctx.limit("GS-09"), "storeys": 1, "gfa": ctx.limit("GS-16")}
        best = None
        for opt in (two, one):
            rear_needed = gs_rear if depth <= 45 else max(gs_rear, opt["h"] / 2)
            space = house_rear - opt["sep"] - rear_needed
            if space >= 3.0 and gs_width >= 3.0:                     # at least a 3 m room to be useful
                foot = min(space * gs_width, opt["gfa"] / opt["storeys"])
                best = dict(opt, space=space, rear_needed=rear_needed, foot=foot)
                break
        if best is None:
            gs["headline"] = "Not enough room behind the house"
            gs["facts"] = [["Why", f"The back yard is {fmt(house_rear)} m. A suite needs at least {fmt(one['sep'])} m from the house, "
                                   f"{fmt(gs_rear)} m from the back line and about 3 m of its own."]]
        else:
            gfa_cap = best["foot"] * best["storeys"]
            house_gfa = ctx.num("house_gfa")
            if house_gfa is not None:
                gfa_cap = min(gfa_cap, house_gfa - 0.1)
            gs["headline"] = (f"{'Two' if best['storeys'] == 2 else 'One'} storey{'s' if best['storeys'] == 2 else ''}, "
                              f"up to {fmt(_r(gfa_cap))} m² of floor area, {fmt(best['h'])} m tall")
            gs["facts"] = [
                ["Space for it", f"{fmt(_r(best['space']))} m deep × {fmt(_r(gs_width))} m wide (after setbacks)"],
                ["Distance from the house", f"at least {fmt(best['sep'])} m"],
                ["Setbacks", f"back {fmt(_r(best['rear_needed']))} m · sides {fmt(_r(gs_side))} m (with windows)"],
                ["Floor area", f"up to {fmt(best['gfa'])} m² for {best['storeys']} storey{'s' if best['storeys'] == 2 else ''}"
                               + ("; must also be smaller than the house" if house_gfa is None else f"; smaller than the house ({fmt(house_gfa)} m²)")],
            ]
            gs["design"] = {"project_type": "Garden suite", "gs_height": best["h"], "gs_storeys": best["storeys"],
                            "gs_to_house": best["sep"], "gs_rear_setback": _r(best["rear_needed"]), "gs_side_setback": _r(gs_side),
                            "gs_side_openings": True, "gs_gfa": _r(gfa_cap), "other_suite_building": False}
    out["options"].append(gs)

    # ---- 3. laneway suite (only if the lot touches a lane for 3.5 m+)
    lane = ctx.num("lane_frontage")
    if lane is not None:
        ls = {"kind": "laneway", "title": "Biggest laneway suite", "rules": ["LS-01", "LS-06", "LS-07", "LS-08", "LS-09", "LS-10"]}
        if lane < ctx.limit("LS-01"):
            ls["headline"] = "Not allowed: the lot touches the lane for less than 3.5 m"
            ls["facts"] = [["Instead", "Look at the garden suite above."]]
        else:
            ls["headline"] = f"Up to {fmt(ctx.limit('LS-07'))} m long × {fmt(ctx.limit('LS-08'))} m wide, 2 storeys, {fmt(ctx.limit('LS-09'))} m tall"
            ls["facts"] = [["Distance from the house", f"7.5 m for the full {fmt(ctx.limit('LS-09'))} m height (4.0 m if it's 4 m tall or less)"],
                           ["Setbacks", f"1.0 m from the back and side lines"],
                           ["Floor area", "must be smaller than the house"]]
            ls["design"] = {"project_type": "Laneway suite", "lane_frontage": lane, "ls_length": ctx.limit("LS-07"),
                            "ls_width": ctx.limit("LS-08"), "ls_height": ctx.limit("LS-09"), "ls_storeys": 2,
                            "ls_to_house": 7.5, "ls_rear_setback": ctx.limit("LS-04"), "ls_side_setback": ctx.limit("LS-05"),
                            "other_suite_building": False}
        out["options"].append(ls)

    # ---- 4. multiplex
    if p in RD_LIKE:
        u = ctx.get("u")
        units = int(u) if isinstance(u, (int, float)) else 4          # a houseplex is 2 to 4 units
        mp = {"kind": "multiplex", "title": "Most homes on the lot", "rules": [f"{p}-29", f"{p}-30", f"{p}-03", "ON-01"]}
        mp["headline"] = f"Up to {units} units in one houseplex"
        mp["facts"] = [["Units", f"{units}" + (" ('u' value on the zone label)" if isinstance(u, (int, float)) else " (a houseplex has 2 to 4 units)")],
                       ["Bedrooms", f"up to {fmt(ctx.limit(f'{p}-30'))} per unit with 2 units; up to 3 per unit with 3 or more"],
                       ["Height", f"{fmt(max(max_h, ctx.limit(f'{p}-03')))} m"],
                       ["Provincial rule", "3 units are allowed as of right on most urban lots (ON-01, verify)"]]
        mp["design"] = {"project_type": "Multiplex conversion (house to 2-4 units)", "building_type": "Detached houseplex",
                        "existing_units": 1, "proposed_units": units, "max_bedrooms_per_unit": 3 if units >= 3 else 4,
                        "within_existing_building": True}
        out["options"].append(mp)

    # ---- prove it: run each biggest design through the normal checker
    lot = {k: v for k, v in ctx.inputs.items() if k in ("zone", "zone_label", "f", "a", "d", "u", "ht", "st", "coverage_overlay",
                                                       "lot_frontage", "lot_depth", "lot_area", "grey_property", "corner_lot",
                                                       "through_lot", "lane", "lane_frontage", "house_gfa")}
    lot.setdefault("lot_area", area)
    for opt in out["options"]:
        design = opt.get("design")
        if not design:
            continue
        design = {k: v for k, v in design.items() if v is not None}
        report = run({**lot, **design}, city)
        fails = [r for r in report["results"] if r["status"] == FAIL]
        opt["design"] = design
        opt["check"] = {"fails": [f"{r['rule_id']}: {r['message']}" for r in fails], "passed": not fails}
    return out
