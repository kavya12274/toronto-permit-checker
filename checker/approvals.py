"""Step 10: the other approvals checklist (AP- rules), plus the STOP check.

Golden rule 5:
  - Grey property (old pre-amalgamation by-law)  -> STOP, run nothing else (AP-01)
  - Site-specific exception on the zone label     -> warning (AP-02)
Never guess.

An approval question left blank = NEED MORE INFO (we don't assume "no").
"""

from .core import PASS, FAIL, NEED, FLAG

# Simple yes/no approval flags: (rule, input key, message when yes)
SIMPLE = [
    ("AP-03", "heritage_designated",
     "Designated heritage property (Part IV, Ontario Heritage Act s. 33-34): changes need heritage consent from the City."),
    ("AP-04", "in_hcd",
     "Inside a Heritage Conservation District (Ontario Heritage Act s. 42): you need a heritage permit. "
     "On the results page, the AI vibes check can compare the design with the district's heritage character (opinions only)."),
    ("AP-05", "trca",
     "Inside the TRCA regulated area (Conservation Authorities Act s. 28): you need a TRCA permit before the building permit."),
    ("AP-06", "ravine",
     "Inside a ravine-protected area: a tree/grading permit under Chapter 658 is needed."),
    ("AP-07", "trees_near_work",
     "Work near City trees (any size) or private trees 30 cm+ wide needs a tree permit and the Tree Declaration form. "
     "The size threshold may have changed on Sept 1, 2026 (By-law 402-2026): verify."),
    ("AP-10", "flightpath",
     "Inside the hospital helicopter flightpath area: check the height limits in By-law 1432-2017."),
    ("AP-13", "former_commercial",
     "Industrial/commercial land becoming residential needs a Record of Site Condition (Environmental Protection Act s. 168)."),
    ("AP-14", "near_highway",
     "Next to a provincial highway: you need an MTO Building and Land Use Permit."),
]

STOP_MESSAGE = ("This property is shown grey on the zoning map, which means it is still under an old "
                "(pre-amalgamation) zoning by-law, not By-law 569-2013. This tool only knows 569-2013, so it has "
                "stopped and run no checks. Please contact Toronto Building to find out which rules apply.")


def stop_check(ctx):
    """Return True (and record AP-01) if the property is grey."""
    if ctx.yes("grey_property"):
        ctx.add("AP-01", FLAG, message=STOP_MESSAGE)
        return True
    return False


def check(ctx, profile):
    project = ctx.project

    # AP-01 grey property: if unknown, ask (the checks above ran, but may not apply)
    if not ctx.has("grey_property"):
        ctx.add("AP-01", NEED, message="Is the property shown grey on the zoning map? If it is, none of the zoning "
                                       "results apply. Check toronto.ca/zoning, or use address lookup.")

    # AP-02 site-specific exception
    if ctx.get("exception"):
        ctx.add("AP-02", FLAG, message=f"The zone label has site-specific exception x{ctx.get('exception')}. Extra rules in "
                                       "Chapter 900 apply to this property and may change any result above. "
                                       "This tool does not read exceptions: check Chapter 900.")

    for rid, key, msg in SIMPLE:
        if ctx.yes(key):
            ctx.add(rid, FLAG, message=msg)
        elif not ctx.has(key):
            ctx.need(rid, [key])

    # AP-08 minor variance if any zoning rule fails
    fails = [r for r in ctx.results if r["status"] == FAIL and r["group"] in ("Zoning", "Suites")]
    if fails:
        ids = ", ".join(sorted({r["rule_id"] for r in fails}))
        ctx.add("AP-08", FLAG, message=f"The project doesn't meet zoning ({ids}). Change the design, or apply to the "
                                       "Committee of Adjustment for a minor variance (see the variance path below).")

    unit_project = any(w in project for w in ("Secondary suite", "Multiplex", "Garden suite", "Laneway suite"))
    if unit_project or ctx.is_houseplex():
        ctx.add("AP-09", FLAG, limit=ctx.limit("AP-09"),
                message="Site plan control: small residential projects (up to 10 units) are generally exempt. "
                        "Confirm the exemption wording in the Planning Act (s. 41) and By-law 774-2012.")

    # AP-11 electrical, AP-12 gas
    if ctx.yes("electrical_work"):
        ctx.add("AP-11", FLAG, message="Electrical work needs a separate permit from the Electrical Safety Authority (ESA).")
    elif not ctx.has("electrical_work") and unit_project:
        ctx.add("AP-11", FLAG, message="New units almost always include electrical work, which needs a separate ESA permit.")
    elif not ctx.has("electrical_work"):
        ctx.need("AP-11", ["electrical_work"])
    if ctx.yes("gas_work"):
        ctx.add("AP-12", FLAG, message="Gas appliance work is regulated by TSSA: use a licensed gas contractor.")

    # AP-15 tenants
    if ctx.yes("existing_tenants") and (unit_project or "Interior" in project or "addition" in project.lower()):
        ctx.add("AP-15", FLAG, message="Renovating where tenants live may need a rental renovation licence (Chapter 662).")

    # AP-16 curb cut / parking pad
    if ctx.yes("new_curb_cut") or "Driveway" in project:
        ctx.add("AP-16", FLAG, message="A new curb cut or front yard parking pad needs City approval (Chapter 918 / 743).")

    # AP-17 demolition
    if ctx.yes("demolition") or "New detached house" in project or "Demolition" in project:
        ctx.add("AP-17", FLAG, message="Demolishing a house needs a demolition permit, and demolition control rules (Chapter 363) apply.")

    # AP-18 infill notice
    if "addition" in project.lower() or "New detached house" in project:
        ctx.add("AP-18", FLAG, message="A residential infill public notice may apply to additions and new houses.")

    # AP-19 fallback - always last
    ctx.add("AP-19", FLAG, message="This may need other approvals. Check with Toronto Building. (The full list of "
                                   "'applicable law' is in the Building Code, Div. A 1.4.1.3.)")
