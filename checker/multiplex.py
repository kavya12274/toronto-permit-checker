"""Step 7: multiplexes (houseplexes with 2 to 4 units).

Rules: RD-29 (units), RD-30 (bedrooms), RD-32 (platforms), G-38 (converting an
existing house). Height (RD-03) and length (RD-11) for houseplexes are handled
in zoning.py whenever the building type is a houseplex.
"""

from .engine import register
from .core import PASS, FAIL, FLAG, fmt
from .zoning import RD_LIKE, zone_ready, rd_main


@register("multiplex")
def multiplex(ctx):
    p = zone_ready(ctx)
    if p is None:
        return
    if p in RD_LIKE:
        rd_houseplex(ctx, p)
        if ctx.has("height") or ctx.has("building_length"):
            rd_main(ctx, p)          # height/length/setbacks for the houseplex, if measurements given
    else:
        # R zone permits houseplexes (R-01); unit/bedroom rules in the table are RD-only for now.
        if not ctx.need("R-01", ["building_type"]):
            ctx.add("R-01", PASS, message=f"{ctx.get('building_type')} is permitted in the R zone.")
        ctx.notes.append("R zone: the Rules Table has no houseplex unit/bedroom rules for R yet, so only the conversion rule is checked.")
    conversion(ctx)


@register("multiplex_if_houseplex")
def multiplex_if_houseplex(ctx):
    """New-house projects: only run the houseplex rules if it is a houseplex."""
    p = zone_ready(ctx)
    if p in RD_LIKE and ctx.is_houseplex():
        rd_houseplex(ctx, p)


def rd_houseplex(ctx, p):
    # RD-29 max units = 'u' value (only if the label has one)
    rid = f"{p}-29"
    u = ctx.get("u")
    if u is None:
        ctx.need(rid, ["u"], why="Max units is the 'u' value on the zone label (if there is one).")
    elif u == "none":
        ctx.add(rid, PASS, value=ctx.num("proposed_units"), message="No 'u' value on the zone label, so no unit limit from it.")
    else:
        ctx.check_max(rid, "proposed_units", u)

    # RD-30 bedrooms per unit: 2 units -> max 4; 3+ units -> max 3 (Notes column)
    rid = f"{p}-30"
    if not ctx.need(rid, ["proposed_units", "max_bedrooms_per_unit"],
                    why="Bedroom limit depends on the number of units."):
        units = ctx.num("proposed_units")
        if units >= 2:
            lim = ctx.limit(rid) if units == 2 else 3
            ctx.check_max(rid, "max_bedrooms_per_unit", lim,
                          message=f"{fmt(units)} units: max {fmt(lim)} bedrooms per unit (bachelor counts as 1). "
                                  f"Yours: {fmt(ctx.num('max_bedrooms_per_unit'))}.")

    # RD-32 houseplex platforms: max 2 per unit
    rid = f"{p}-32"
    if ctx.has("platforms_per_unit"):
        ctx.check_max(rid, "platforms_per_unit", ctx.limit(rid))


def conversion(ctx):
    """G-38: converting an existing detached house to a houseplex."""
    if ctx.need("G-38", ["within_existing_building"],
                why="A conversion is allowed if the new units fit inside the building as it existed before the permit."):
        return
    if ctx.yes("within_existing_building"):
        ctx.add("G-38", PASS, message="The new units fit inside the existing building, so the conversion is permitted. "
                                      "('Lawfully existing' = authorized on or before June 26, 2025.)")
    else:
        ctx.add("G-38", FLAG, message="Part of the project is an addition. Additions must meet zoning or get a minor "
                                      "variance. Run the addition as its own project type too.")
