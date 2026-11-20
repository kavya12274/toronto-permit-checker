"""Step 15: buildable area diagram.

Draws the lot (a simple rectangle: frontage x depth) as an SVG picture and shades
where the main building may go, using the REQUIRED setbacks from the rules:
  front  RD-15 / R-08
  rear   RD-16 (greater of 7.5 m or 25% of depth) / R-09
  sides  RD-17..RD-23 by frontage / R-10
  depth  RD-12: rear wall no more than 19.0 m from the required front setback (frontage <= 18 m)
Real lots are rarely perfect rectangles, and encroachments (porches, eaves) and the
neighbour-average front setback aren't shown. The caption says so.
"""

from .core import fmt
from .zoning import RD_LIKE, side_rule_for_frontage


def envelope(ctx):
    """Return the required setbacks as numbers, or None if we can't work them out."""
    zone, fr, depth = ctx.zone, ctx.num("lot_frontage"), ctx.num("lot_depth")
    if fr is None or depth is None:
        return None
    if zone in RD_LIKE and f"{zone}-15" in ctx.rules:
        front = ctx.limit(f"{zone}-15")
        rear = max(ctx.limit(f"{zone}-16"), 0.25 * depth)
        side_rule = side_rule_for_frontage(zone, fr)
        side = ctx.limit(side_rule)
        max_depth = ctx.limit(f"{zone}-12") if fr <= 18.0 else None
        rules = f"{zone}-15, {zone}-16, {side_rule}" + (f", {zone}-12" if max_depth else "")
    elif zone == "R":
        front, rear = ctx.limit("R-08"), ctx.limit("R-09")
        side = ctx.limit("R-11") if ctx.no("side_wall_openings") else ctx.limit("R-10")
        max_depth = ctx.limit("R-05")
        rules = "R-08, R-09, R-10/R-11, R-05"
    else:
        return None
    back_line = depth - rear
    if max_depth is not None:
        back_line = min(back_line, front + max_depth)
    width = fr - 2 * side
    return {"frontage": fr, "depth": depth, "front": front, "rear": rear, "side": side,
            "build_width": round(width, 2), "build_from": front, "build_to": round(back_line, 2),
            "build_depth": round(back_line - front, 2), "rules": rules}


def svg(e, drawn=None):
    W = 320                                   # drawing width in pixels
    scale = W / e["frontage"]
    H = e["depth"] * scale
    if H > 520:                               # very deep lots: shrink to fit
        scale = 520 / e["depth"]
        W, H = e["frontage"] * scale, 520
    pad = 46
    x0, y0 = pad, 20
    # The street is at the BOTTOM: y grows toward the rear of the lot (top of the picture).
    def Y(m):                                 # metres from the front lot line -> pixel y
        return y0 + H - m * scale

    bx = x0 + e["side"] * scale
    bw = max(e["build_width"], 0) * scale
    by_top, by_bot = Y(e["build_to"]), Y(e["build_from"])
    parts = [
        f'<svg viewBox="0 0 {W + pad * 2:.0f} {H + 40:.0f}" width="100%" style="max-width:{W + pad * 2:.0f}px" '
        f'role="img" aria-label="Lot diagram: buildable area {fmt(e["build_width"])} m wide by {fmt(e["build_depth"])} m deep">',
        f'<rect x="{x0}" y="{y0}" width="{W:.1f}" height="{H:.1f}" fill="var(--lot)" stroke="var(--muted)" stroke-width="2"/>',
    ]
    if bw > 0 and by_bot > by_top:
        parts.append(f'<rect x="{bx:.1f}" y="{by_top:.1f}" width="{bw:.1f}" height="{by_bot - by_top:.1f}" '
                     f'fill="var(--build)" stroke="var(--build-line)" stroke-dasharray="5 3" stroke-width="1.5"/>')
        parts.append(f'<text x="{bx + bw / 2:.1f}" y="{(by_top + by_bot) / 2:.1f}" text-anchor="middle" font-size="13" '
                     f'fill="var(--pass)" font-weight="700">Buildable area</text>')
        parts.append(f'<text x="{bx + bw / 2:.1f}" y="{(by_top + by_bot) / 2 + 16:.1f}" text-anchor="middle" font-size="12" '
                     f'fill="var(--pass)">{fmt(e["build_width"])} m × {fmt(e["build_depth"])} m</text>')
    if drawn:                                 # the user's building footprint, if we know enough
        dx, dw, dy, dd = drawn
        parts.append(f'<rect x="{x0 + dx * scale:.1f}" y="{Y(dy + dd):.1f}" width="{dw * scale:.1f}" height="{dd * scale:.1f}" '
                     f'fill="none" stroke="var(--fail)" stroke-width="2"/>')
    # labels
    parts += [
        f'<text x="{x0 + W / 2:.1f}" y="{y0 + H + 18:.1f}" text-anchor="middle" font-size="12" fill="var(--text)">STREET · frontage {fmt(e["frontage"])} m</text>',
        f'<text x="{x0 + W / 2:.1f}" y="{y0 - 6:.1f}" text-anchor="middle" font-size="11" fill="var(--muted)">rear lot line</text>',
        f'<text x="{x0 - 6}" y="{y0 + H / 2:.1f}" text-anchor="end" font-size="11" fill="var(--muted)">{fmt(e["depth"])} m</text>',
        f'<text x="{x0 + W / 2:.1f}" y="{(by_bot + Y(0)) / 2 + 4:.1f}" text-anchor="middle" font-size="11" fill="var(--muted)">front {fmt(e["front"])} m</text>',
        f'<text x="{x0 + W / 2:.1f}" y="{(Y(e["depth"]) + by_top) / 2 + 4:.1f}" text-anchor="middle" font-size="11" fill="var(--muted)">rear yard min {fmt(e["rear"])} m</text>',
        f'<text x="{x0 + 3}" y="{y0 + H - 6:.1f}" font-size="10" fill="var(--muted)">side {fmt(e["side"])}</text>',
        f'<text x="{x0 + W - 3:.1f}" y="{y0 + H - 6:.1f}" text-anchor="end" font-size="10" fill="var(--muted)">side {fmt(e["side"])}</text>',
        "</svg>",
    ]
    return "".join(parts)


def add_to_report(ctx, report):
    report["diagram"] = None
    profile = ctx.data.get("project_profiles", {}).get(ctx.project) or {}
    if "zone_main" not in profile.get("groups", []) or report["stopped"]:
        return
    e = envelope(ctx)
    if not e:
        report["diagram"] = {"svg": "", "caption": "Add the zone, lot frontage and lot depth to see the buildable area diagram."}
        return
    drawn = None
    ss, length = ctx.num("side_setback"), ctx.num("building_length")
    fs, width = ctx.num("front_setback"), None
    other = ctx.num("side_setback_other")
    if ss is not None and other is not None:
        width = e["frontage"] - ss - other
    if None not in (ss, length, fs, width) and width > 0:
        drawn = (ss, width, fs, length)
    rear_note = " The rear line is the depth limit (rear wall within 19 m of the required front setback)." \
        if e["build_to"] < e["depth"] - e["rear"] - 1e-9 else ""
    report["diagram"] = {
        "svg": svg(e, drawn), "envelope": e,
        "caption": (f"Green = where the main building may go; red outline = your building (if you gave its setbacks and length). "
                    f"Lot {fmt(e['frontage'])} m × {fmt(e['depth'])} m (drawn as a rectangle). Required setbacks: front "
                    f"{fmt(e['front'])} m, rear {fmt(e['rear'])} m, sides {fmt(e['side'])} m (rules {e['rules']}). "
                    f"Buildable area: {fmt(e['build_width'])} m wide, {fmt(e['build_depth'])} m deep.{rear_note} "
                    "Not shown: porches/eaves allowed to stick out, the neighbour-average front setback, odd-shaped lots, "
                    "site-specific exceptions."),
    }
