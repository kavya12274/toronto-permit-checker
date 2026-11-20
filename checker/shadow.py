"""Shadow preview (Build Plan step 22, optional). Plain maths, no AI.

How long a shadow the new building throws, and which way, at a few times of day.
Toronto's own shadow studies use March 21 / September 21 (the equinoxes), so we do too,
plus June 21 (shortest shadows) and December 21 (longest) at midday for comparison.

The sun's position comes from the standard formulas (latitude, the sun's declination
on that date, and the hour angle). Shadow length = height / tan(sun's height in the sky).
Times are SOLAR time (the sun is highest at 12:00); in Toronto that's about 1:20 pm
daylight time in March, or 12:20 pm standard time in December.

This is a rough sketch for talking to neighbours: a box-shaped building on flat ground.
It isn't a shadow study, which the City asks for only on bigger projects.
"""

import math

LAT = 43.65                       # Toronto
DECLINATION = {"Mar 21": 0.0, "Jun 21": 23.44, "Dec 21": -23.44}

HEIGHT_KEY = {
    "Garden suite": "gs_height", "Laneway suite": "ls_height", "Shed / accessory building": "anc_height",
    "Detached garage": "anc_height",
}
SKIP = {"Deck / platform", "Pool", "Driveway / parking pad", "Interior alterations / basement finishing",
        "Secondary suite (e.g. basement apartment)", "Demolition only", "Solar panels"}


def sun(date, solar_hour):
    """Sun's height above the horizon and compass direction (degrees, 0 = north, 90 = east)."""
    phi, dec = math.radians(LAT), math.radians(DECLINATION[date])
    h = math.radians(15 * (solar_hour - 12))
    alt = math.asin(math.sin(phi) * math.sin(dec) + math.cos(phi) * math.cos(dec) * math.cos(h))
    az = math.atan2(math.sin(h), math.cos(h) * math.sin(phi) - math.tan(dec) * math.cos(phi))  # from south, + west
    return math.degrees(alt), (math.degrees(az) + 180) % 360


def preview(project, inputs):
    if project in SKIP:
        return None
    key = HEIGHT_KEY.get(project, "height")
    height = inputs.get(key)
    if not isinstance(height, (int, float)) or height <= 0:
        return {"ready": False, "message": "Add the building's height to see a rough shadow preview."}
    if project == "Laneway suite":
        w, d = inputs.get("ls_width") or 7, inputs.get("ls_length") or 8
    elif project in ("Garden suite", "Shed / accessory building", "Detached garage"):
        w, d = 6, 6
    else:
        frontage = inputs.get("lot_frontage")
        sides = (inputs.get("side_setback") or 0.9) + (inputs.get("side_setback_other") or inputs.get("side_setback") or 0.9)
        w = max(3, (frontage - sides)) if isinstance(frontage, (int, float)) else 7
        d = inputs.get("building_depth") or 4
    times = []
    for date, hour, label in [("Mar 21", 9, "Mar 21, 9 am"), ("Mar 21", 12, "Mar 21, noon"), ("Mar 21", 15, "Mar 21, 3 pm"),
                              ("Jun 21", 12, "Jun 21, noon"), ("Dec 21", 12, "Dec 21, noon")]:
        alt, az = sun(date, hour)
        if alt <= 2:
            continue
        length = height / math.tan(math.radians(alt))
        shadow_dir = math.radians((az + 180) % 360)             # shadows point away from the sun
        times.append({"label": label, "sun_height_deg": round(alt, 1), "sun_from_deg": round(az),
                      "length_m": round(length, 1),
                      "dx": round(length * math.sin(shadow_dir), 2), "dy": round(length * math.cos(shadow_dir), 2),
                      "main": date == "Mar 21"})
    if key == "height":       # additions and houses: the form has the WHOLE building's height, not the new part's
        about = (f"the whole building ({fmt_m(height)} m tall), with the new part included. If the new part is lower "
                 "than the house, its own shadow is shorter than this")
    else:
        about = f"the {project.split(' /')[0].split(' (')[0].lower()} ({fmt_m(height)} m tall)"
    return {"ready": True, "height_m": height, "height_from": key, "about": about, "box": {"w": round(w, 1), "d": round(d, 1)},
            "times": times,
            "note": "Rough sketch: a simple box on flat ground, solar time. Not an official shadow study. "
                    "dx/dy are metres east/north."}


def fmt_m(x):
    return f"{x:g}"


def add_to_report(ctx, report):
    report["shadow"] = None if report.get("stopped") else preview(ctx.project, ctx.inputs)
