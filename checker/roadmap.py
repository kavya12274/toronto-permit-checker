"""The full permit roadmap: what happens after the check.

  1. Submission checklist: the drawings and forms to attach (City of Toronto
     Small Residential Additions guide, and Chapter 363 s. 363-3.5 for the site plan)
  2. Inspection stages the City will do (City's 'When to Call for Inspection of
     Small Buildings' list)
  3. A step-by-step timeline from idea to final inspection, including any
     other approvals or minor variance this project's results flagged

The lists live in data/toronto/roadmap.json. This file only picks the items that
fit the project type and answers. Every item says which source it came from.
"""

from .core import FAIL, FLAG, fmt

# Which tags each project type has (tags are the "when" values in roadmap.json)
TAGS = {
    "Rear addition (1 or 2 storey)": {"building", "roof", "exterior", "new_space", "foundation", "framing"},
    "Second-storey addition": {"building", "roof", "exterior", "new_space", "framing"},
    "Front porch / front addition": {"building", "exterior", "deck", "new_space", "foundation", "framing"},
    "Deck / platform": {"building", "deck", "exterior", "foundation", "framing"},
    "Shed / accessory building": {"building", "accessory", "roof", "exterior", "foundation", "framing"},
    "Detached garage": {"building", "accessory", "roof", "exterior", "foundation", "framing"},
    "Pool": set(),
    "Garden suite": {"building", "roof", "exterior", "new_space", "foundation", "framing", "units", "plumbing", "hvac", "mechanical"},
    "Laneway suite": {"building", "roof", "exterior", "new_space", "foundation", "framing", "units", "plumbing", "hvac", "mechanical"},
    "Secondary suite (e.g. basement apartment)": {"building", "framing", "units", "plumbing", "hvac", "mechanical"},
    "Multiplex conversion (house to 2-4 units)": {"building", "framing", "units", "plumbing", "hvac", "mechanical"},
    "New detached house / houseplex (replacement)": {"building", "roof", "exterior", "new_space", "foundation", "framing",
                                                     "units", "plumbing", "hvac", "mechanical", "demolition", "infill"},
    "Interior alterations / basement finishing": {"building", "framing"},
    "Driveway / parking pad": set(),
    "Solar panels": {"building", "roof"},
    "Demolition only": {"demolition"},
}


def tags_for(ctx):
    tags = set(TAGS.get(ctx.project, set())) | {"always"}
    if ctx.yes("demolition"):
        tags.add("demolition")
    if ctx.yes("hvac_plumbing"):
        tags |= {"plumbing", "hvac", "mechanical"}
    if ctx.yes("existing_tenants"):
        tags.add("tenants")
    eu, pu = ctx.num("existing_units"), ctx.num("proposed_units")
    if eu is not None and pu is not None and pu > eu:
        tags.add("units")
    area = ctx.num("work_area")
    if "new_space" in tags and "addition" in ctx.project.lower() and area is not None and area > 100:
        tags.add("infill")                      # additions over 100 m² need the infill notice
    return tags


def add_to_report(ctx, report):
    data = ctx.data.get("roadmap")
    if not data or report["stopped"]:
        report["roadmap"] = None
        return
    project = ctx.project
    answer = (report.get("permit") or {}).get("answer", "")
    tags = tags_for(ctx)

    def pick(items):
        return [dict(i) for i in items if i["when"] in tags]

    if answer == "No building permit needed":
        checklist = {"general": [], "drawings": [], "forms": [], "none": "No building permit needed, so there's nothing to submit "
                     "to Toronto Building. Zoning rules still apply, and other approvals listed in your results may still be needed."}
        inspections = []
    elif project == "Pool":
        checklist = {"general": [], "drawings": [], "forms": [], "none": "Pools need a pool enclosure (fence) permit from the City, "
                     "a separate application from a building permit. Check the City's pool enclosure page."}
        inspections = []
    elif project == "Driveway / parking pad":
        checklist = {"general": [], "drawings": [], "forms": [], "none": "No building permit, but a new curb cut or front-yard "
                     "parking pad needs City approval (Chapter 918 / 743), with its own application."}
        inspections = []
    else:
        drawings, forms = pick(data["drawings"]), pick(data["forms"])
        # optional forms people should know about even if we can't tell yet
        if "infill" not in tags and "addition" in project.lower():
            forms.append({"item": "Residential Infill Public Notice Declaration", "when": "maybe",
                          "detail": "Only if the addition adds more than 100 m² of floor area."})
        if "engineer" not in tags and "building" in tags:
            forms.append({"item": "Assumption of Responsibility for Engineering Content", "when": "maybe",
                          "detail": "Only if a professional engineer seals any of your drawings."})
        checklist = {"general": data["general"], "drawings": drawings, "forms": forms}
        inspections = pick(data["inspections"])

    report["roadmap"] = {
        "checklist": checklist,
        "inspections": inspections,
        "inspection_notes": data["inspection_notes"] if inspections else [],
        "timeline": timeline(ctx, report, answer),
        "sources": data["sources"],
    }


def timeline(ctx, report, answer):
    """From idea to closed permit, with the extra stops this project's results flagged."""
    results = report["results"]
    flagged = {r["rule_id"] for r in results if r["status"] == FLAG}
    fails = [r for r in results if r["status"] == FAIL and r["group"] in ("Zoning", "Suites")]
    fees = ctx.data.get("fees", {}).get("timelines", {})
    steps = [{"title": "Idea and pre-check", "time": "Today",
              "detail": "You're here. Fix what you can from the results and answer the open questions."}]

    if answer in ("No building permit needed", "Check with the City") or ctx.project in ("Driveway / parking pad", "Pool"):
        steps.append({"title": "Other approvals", "time": "Varies",
                      "detail": "Get any approvals listed in your results (for example a curb cut, pool enclosure or tree permit)."})
        steps.append({"title": "Build it", "time": "Your schedule", "detail": "Zoning rules still apply even with no building permit."})
        return steps

    steps.append({"title": "Survey and drawings", "time": "Usually a few weeks",
                  "detail": "Get a current survey and have a qualified designer draw the plans on the checklist below."})
    if fails:
        steps.append({"title": "Minor variance (Committee of Adjustment)", "time": fees.get("committee_of_adjustment", "Months"),
                      "detail": f"{len(fails)} zoning rule(s) don't pass. Change the design, or ask the Committee for a minor variance before the permit."})
    extra = []
    names = {"AP-03": "heritage consent", "AP-04": "heritage district permit", "AP-05": "TRCA permit", "AP-06": "ravine permit",
             "AP-07": "tree permit", "AP-10": "flightpath check", "AP-14": "MTO permit", "AP-13": "Record of Site Condition"}
    for rid, name in names.items():
        if rid in flagged:
            extra.append(name)
    if extra:
        steps.append({"title": "Other approvals first", "time": "Weeks to months",
                      "detail": "Get these before the building permit can be issued: " + ", ".join(extra) + "."})
    steps.append({"title": "Apply online", "time": "1 day",
                  "detail": "Submit the drawings and forms as PDFs through Toronto Building's online portal and pay the fees."})
    steps.append({"title": "City review", "time": f"Up to {fees.get('house_business_days', 10)} business days once complete",
                  "detail": "The legal maximum for house projects once the application is complete. Missing items restart the clock."})
    steps.append({"title": "Permit issued", "time": "",
                  "detail": "Post the permit card (and the infill notice, if you need one) where it can be seen from the street."})
    steps.append({"title": "Build, with inspections", "time": "Your build schedule",
                  "detail": "Book each inspection on the list below when that stage is ready. They happen within 2 business days."})
    steps.append({"title": "Final inspection: permit closed", "time": "",
                  "detail": "Book the final inspection to close the permit. Open permits can cause trouble when you sell."})
    return steps
