"""Build the by-law dictionary (hover definitions) from Chapter 800 of Zoning By-law 569-2013.

For each term it keeps:
  plain     a short plain-language explanation (written for this tool)
  official  the official definition, copied from Chapter 800 (public law)
  source    where it comes from, e.g. "Ch. 800, 800.50(240)"

Run it (needs internet; re-run if the by-law changes):
    python3 tools/build_glossary.py
It writes data/toronto/glossary.json. Terms that aren't defined in Chapter 800
(like FSI or building height) are marked with the section where the by-law sets them.
"""

import html
import json
import os
import re
import subprocess
import urllib.request
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "data", "toronto", "glossary.json")
URL = "https://www.toronto.ca/zoning/bylaw_amendments/ZBL_NewProvision_Chapter800.htm"

# term (as in Chapter 800) -> (other words that should get the same tooltip, plain-language explanation)
TERMS = {
    "Established Grade": (["established grade"], "The ground level the City measures height from: the average ground height at the two front corners of the lot, at the required front setback line."),
    "Gross Floor Area": (["gross floor area", "GFA", "floor area"], "All the floor area of every level, above and below ground, measured to the outside of the walls."),
    "Lot Coverage": (["lot coverage", "coverage"], "How much of your lot is covered by buildings or structures, seen from above."),
    "Lot Frontage": (["lot frontage", "frontage"], "How wide your lot is, measured across at the required front setback line (not at the street)."),
    "Lot Depth": (["lot depth"], "How deep your lot is, from the front lot line to the back lot line, along the middle of the lot."),
    "Lot Area": (["lot area"], "The total area inside your lot lines."),
    "Front Lot Line": (["front lot line"], "The edge of your lot along the street."),
    "Rear Lot Line": (["rear lot line", "back lot line"], "The edge of your lot opposite the street."),
    "Side Lot Line": (["side lot line"], "Any edge of your lot that isn't the front or the back."),
    "Main Wall": (["main wall"], "Any outside wall of a building that holds up a roof over an enclosed space."),
    "Front Yard": (["front yard"], "The area between the street edge of your lot and the front of the house, across the full width."),
    "Rear Yard": (["rear yard", "back yard"], "The area between the back of the house and the back edge of the lot, across the full width."),
    "Side Yard": (["side yard"], "The strip beside the house, between the front yard and the back yard."),
    "Building Setback": (["setback"], "How far a wall is from a lot line, measured straight out from the line."),
    "Front Yard Setback": (["front setback", "front yard setback"], "How far the front wall of the house is from the front lot line."),
    "Rear Yard Setback": (["rear setback", "rear yard setback"], "How far the back wall of the house is from the back lot line."),
    "Side Yard Setback": (["side setback", "side yard setback"], "How far the side wall of the house is from the side lot line."),
    "Storey": (["storey", "storeys"], "One level of a building. A basement doesn't count as a storey."),
    "Basement": (["basement"], "A level that's mostly below the ground (below established grade)."),
    "Building Depth": (["building depth"], "How far the house goes back, measured from the required front setback line to its back wall."),
    "Building Length": (["building length"], "How long the house is, from its front wall to its back wall, along the middle of the lot."),
    "Garden Suite": (["garden suite"], "A small separate home in the back yard, in its own building, on a lot that doesn't touch a lane."),
    "Laneway Suite": (["laneway suite"], "A small separate home in its own building at the back of a lot that touches a public lane."),
    "Secondary Suite": (["secondary suite", "basement apartment"], "A second, self-contained home inside a house, with its own kitchen and bathroom."),
    "Ancillary": (["ancillary", "accessory building"], "Smaller and secondary to the main use, like a shed or garage that serves the house."),
    "Lane": (["lane", "laneway"], "A public road behind or beside lots that isn't meant for through traffic."),
    "Corner Lot": (["corner lot"], "A lot where two streets meet (or one street bends sharply)."),
    "Through Lot": (["through lot"], "A lot with a street at both the front and the back (and it isn't a corner lot)."),
    "Landscaping": (["landscaping", "landscaped"], "Trees, plants, walkways and decorative stone. Driveways and parking areas don't count."),
    "Soft Landscaping": (["soft landscaping"], "Landscaping that's growing: grass, plants, trees. Paving and stone don't count."),
    "Dwelling Unit": (["dwelling unit", "unit", "units"], "One home: a place with its own kitchen and bathroom for one household."),
    "Driveway": (["driveway"], "The path cars use to get from the street or lane to a parking spot."),
    "Major Street": (["major street"], "A street the City lists as a 'major street' on its policy map. Some rules are different on these streets."),
    "Detached House": (["detached house"], "A house with one home in it, not attached to any other building."),
    "Semi-Detached House": (["semi-detached house"], "A building with two homes side by side, sharing a wall."),
    "Detached Houseplex": (["houseplex", "detached houseplex"], "One building on one lot with 2 to 4 homes in it."),
    "Duplex": (["duplex"], "A building with two homes, one above the other."),
    "Triplex": (["triplex"], "A building with three homes, at least one above another."),
    "Fourplex": (["fourplex"], "A building with four homes, at least one above another."),
    "Townhouse": (["townhouse"], "Three or more homes side by side, none above another."),
    "Bedroom": (["bedroom"], "A room with a window (or other natural light) used mainly for sleeping."),
}

# Terms the by-law sets outside Chapter 800 (no Chapter 800 definition to copy)
EXTRA = [
    {"term": "FSI (floor space index)", "words": ["FSI", "floor space index", "density"],
     "plain": "Total floor area ÷ lot area. FSI 0.6 on a 400 m² lot allows 240 m² of floor area.",
     "official": "", "source": "The 'd' (density) value on the zone label, e.g. RD (d0.6); limits in 10.10.40.40 and 10.20.40.40"},
    {"term": "Building height", "words": ["height", "building height"],
     "plain": "Measured from established grade up to the highest point of the building.",
     "official": "", "source": "By-law 569-2013, 10.5.40.10 (rule G-01 in this tool)"},
    {"term": "Platform", "words": ["platform", "platforms", "deck", "balcony"],
     "plain": "The zoning by-law's word for decks, balconies, porches and similar flat outdoor floors.",
     "official": "", "source": "By-law 569-2013, 10.5.40.50 and 10.5.40.60"},
    {"term": "Overlay (HT, ST, coverage)", "words": ["overlay", "HT", "ST"],
     "plain": "Extra limits drawn on the City's zoning maps, like the height limit (HT) or storey limit (ST) for your street.",
     "official": "", "source": "By-law 569-2013, Chapter 995 (overlay maps)"},
    {"term": "Minor variance", "words": ["minor variance", "variance"],
     "plain": "Permission from the Committee of Adjustment to break a zoning rule by a small amount.",
     "official": "", "source": "Planning Act, s. 45(1)"},
    {"term": "Encroachment", "words": ["encroach", "encroachment", "sticks out"],
     "plain": "When part of a building (stairs, eaves, a porch) is allowed to stick into a setback space.",
     "official": "", "source": "By-law 569-2013, 10.5.40.60"},
]


def fetch(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "permit-checker-prototype"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read().decode("utf-8", "ignore")
    except Exception:
        return subprocess.run(["curl", "-sSL", "-m", "60", url], capture_output=True, text=True).stdout


def main():
    text = fetch(URL)
    text = re.sub(r"<script.*?</script>|<style.*?</style>", "", text, flags=re.S)
    text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text)))
    text = re.sub(r"\s+([,.;)])", r"\1", text)
    out, missing = [], []
    for term, (words, plain) in TERMS.items():
        m = re.search(r"\((\d+)\)\s*" + re.escape(term) + r"\s+means,?\s+(.*?)(?=\s\(\d+\)\s+[A-Z])", text)
        official, source = "", "Chapter 800"
        if m:
            official = term + " means " + re.sub(r"\[\s*By-law:[^\]]*\]", "", m.group(2)).strip()
            source = f"Zoning By-law 569-2013, Chapter 800, 800.50({m.group(1)})"
        else:
            missing.append(term)
        out.append({"term": term, "words": words, "plain": plain, "official": official[:700], "source": source})
    out += EXTRA
    data = {"source": URL, "built_on": date.today().isoformat(), "terms": out}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
    print(f"Wrote {len(out)} terms to {OUT}")
    if missing:
        print("Not found in Chapter 800 (check the spelling or the by-law):", ", ".join(missing))


if __name__ == "__main__":
    main()
