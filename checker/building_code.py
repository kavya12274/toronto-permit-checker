"""Step 8: Ontario Building Code basics (BC- rules).

Golden rule 6: these are SAFETY rules. Every BC- result
  - is marked confidence 'Needs human check' (done in core.Context.add), and
  - says "A qualified designer must confirm."
We never say a design is "safe" or "approved".

Rows whose Check type is 'To extract' (BC-06 to BC-11) don't have numbers yet,
so they are shown as REMINDERS (FLAG), not checked. When you fill in those rows
in the workbook, give them a real check type and limit, re-import, and add a
check here.
"""

from .engine import register
from .core import PASS, FAIL, FLAG, fmt


def reminders(ctx, ids):
    """Show 'To extract' rows as reminders."""
    for rid in ids:
        r = ctx.rule(rid)
        if not r:
            continue
        if r["check_type"] == "To extract" or r["limit"] is None:
            ctx.add(rid, FLAG, message=f"Reminder: {r['rule']} ({r['section']}). This rule is not checked automatically yet "
                                       "(its numbers haven't been extracted from the Building Code).")


def stairs(ctx):
    """BC-01: private stair run between 255 and 355 mm."""
    if not ctx.has("stair_run"):
        ctx.need("BC-01", ["stair_run"], limit=ctx.limit("BC-01"))
        return
    run = ctx.num("stair_run")
    lo, hi = ctx.limit("BC-01"), 355                       # max 355 mm from the Notes column
    ok = lo <= run <= hi
    ctx.add("BC-01", PASS if ok else FAIL, value=run, limit=f"{fmt(lo)}–{fmt(hi)}",
            message=f"Stair run must be {fmt(lo)} to {fmt(hi)} mm. Yours: {fmt(run)} mm.",
            fix_data=None if ok else {"kind": "min" if run < lo else "max", "key": "stair_run", "value": run,
                                      "limit": lo if run < lo else hi})


def egress(ctx):
    """BC-02, BC-03, BC-04: bedroom egress windows."""
    if ctx.need("BC-02", ["has_bedroom"], why="Egress rules apply to floors with a bedroom."):
        return
    if not ctx.yes("has_bedroom"):
        return
    if ctx.has("egress_window"):
        if ctx.yes("egress_window"):
            ctx.add("BC-02", PASS, message="Each bedroom floor has an outside window or door that opens from inside.")
        else:
            ctx.add("BC-02", FAIL, message="Every floor with a bedroom needs an outside window or door that opens from inside without tools.")
    elif not ctx.has("egress_sill"):
        ctx.need("BC-02", ["egress_window"])
    ctx.check_max("BC-03", "egress_sill", ctx.limit("BC-03"))
    if ctx.yes("window_well"):
        ctx.check_min("BC-04", "window_well_clearance", ctx.limit("BC-04"))


def guards(ctx):
    """BC-05: low windows with a big drop need a guard or limiter."""
    if not ctx.yes("low_window_high_drop"):
        return
    if ctx.need("BC-05", ["low_window_guarded"]):
        return
    if ctx.yes("low_window_guarded"):
        ctx.add("BC-05", PASS, message="Low window with a big drop has a guard or opening limiter.")
    else:
        ctx.add("BC-05", FAIL, message="An openable window with sill under 900 mm and a drop over 1.8 m needs a guard or opening limiter.")


def conversion_flag(ctx):
    """BC-12: existing house gaining units -> Fire Code retrofit."""
    eu, pu = ctx.num("existing_units"), ctx.num("proposed_units")
    gains = (eu is not None and pu is not None and pu > eu) or "Secondary suite" in ctx.project or "Multiplex" in ctx.project
    if gains:
        ctx.add("BC-12", FLAG, message="Converting an existing house to 2+ units must meet the Fire Code retrofit rules "
                                       "(fire separations, alarms, exits).")


@register("code_general")
def code_general(ctx):
    guards(ctx)
    if ctx.has("has_bedroom"):
        egress(ctx)
    reminders(ctx, ["BC-06", "BC-07", "BC-10", "BC-11"])


@register("code_stairs")
def code_stairs(ctx):
    if ctx.has("stair_run"):
        stairs(ctx)
    reminders(ctx, ["BC-06"])


@register("code_suite")
def code_suite(ctx):
    egress(ctx)
    guards(ctx)
    if ctx.has("stair_run"):
        stairs(ctx)
    reminders(ctx, ["BC-07", "BC-08", "BC-09", "BC-10"])
    conversion_flag(ctx)


@register("code_interior")
def code_interior(ctx):
    egress(ctx)
    guards(ctx)
    if ctx.has("stair_run"):
        stairs(ctx)
    reminders(ctx, ["BC-07", "BC-08"])
    conversion_flag(ctx)
