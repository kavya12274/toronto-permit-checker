"""Step 14: address lookup from City of Toronto and TRCA open map data.

What it fills in (the user can still change anything):
  zone label (and zone, f, a, d, u, exception)  City zoning map: Zoning Area layer
  HT and ST                                     City zoning map: Height Overlay layer
  lot coverage overlay                          City zoning map: Lot Coverage Overlay layer
  grey property (old by-law)                    City zoning map: Former Municipality By-laws
                                                + Not Part of This By-law layers
  Heritage Conservation District                City map: Heritage District layer
  ravine-protected area                         City map: Ravine and Natural Feature Protection
  TRCA regulated area                           TRCA: Regulation Limit (O. Reg. 41/24)

What it can NOT fill in yet: designated heritage PROPERTIES (Part IV), trees, the
helicopter flightpath, lot size. Those stay as questions on the form.

PRIVACY: the address you type is sent to the City of Toronto's map search to find
its location. Only the map point (not the address) is sent to the other layers.
If any service can't be reached, that answer is left blank (NEED MORE INFO) and
the message says so. Manual entry always keeps working.

The services and layer numbers are listed in SERVICES below. If the City renumbers
its layers, change the numbers here (no other code needs to change).
"""

import json
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request

GEOCODER = "https://map.toronto.ca/geoservices/rest/search/rankedsearch"
CITY = "https://gis.toronto.ca/arcgis/rest/services"
SERVICES = {
    "zone":      CITY + "/cot_geospatial11/MapServer/3",
    "height":    CITY + "/cot_geospatial11/MapServer/9",
    "coverage":  CITY + "/cot_geospatial11/MapServer/10",
    "former":    CITY + "/cot_geospatial11/MapServer/8",
    "not_part":  CITY + "/cot_geospatial11/MapServer/12",
    "hcd":       CITY + "/cot_geospatial11/MapServer/40",
    "ravine":    CITY + "/cot_geospatial13/MapServer/70",
    "trca":      "https://services1.arcgis.com/d0ZCwU7eGKVeNiEE/ArcGIS/rest/services/TRCA_Regulation_Limit2/FeatureServer/0",
}
TIMEOUT = 15


def fetch_json(url, params):
    """Download JSON from a web service (no API key needed).

    Python installed from python.org on a Mac often can't check website security
    certificates ("CERTIFICATE_VERIFY_FAILED"). If that happens we ask macOS's own
    'curl' program instead, which uses the Mac's certificate store. Certificate
    checking is never switched off."""
    full = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(full, headers={"User-Agent": "permit-checker-prototype"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        if "CERTIFICATE_VERIFY_FAILED" not in str(e) or not shutil.which("curl"):
            raise
        out = subprocess.run(["curl", "-sS", "--fail", "-m", str(TIMEOUT), "-A", "permit-checker-prototype", full],
                             capture_output=True, text=True, timeout=TIMEOUT + 5)
        if out.returncode != 0:
            raise RuntimeError(out.stderr.strip() or "download failed")
        return json.loads(out.stdout)


def geocode(address, fetch=fetch_json):
    data = fetch(GEOCODER, {"searchString": address})
    result = data.get("result", {})
    best = (result.get("bestResult") or []) + (result.get("likelyResults") or [])
    best = [b for b in best if b.get("featureClass") == "Address"]
    if not best:
        return None
    b = best[0]
    return {"lat": b["latitude"], "lon": b["longitude"], "matched": b.get("key_Desc", ""),
            "detail": b.get("detail", ""), "exact": b.get("matchType") == "Exact"}


def features_at(layer_url, lon, lat, fetch=fetch_json):
    """Attributes of every feature in this layer that contains the point."""
    data = fetch(layer_url + "/query", {
        "geometry": f"{lon},{lat}", "geometryType": "esriGeometryPoint", "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects", "outFields": "*", "returnGeometry": "false", "f": "json"})
    if "error" in data:
        raise RuntimeError(data["error"].get("message", "service error"))
    return [f["attributes"] for f in data.get("features", [])]


def lookup_address(address, fetch=fetch_json):
    values, messages = {}, []
    if not address.strip():
        return {"values": {}, "messages": ["Type an address first."], "summary": "No address"}
    try:
        place = geocode(address, fetch)
    except Exception as e:
        return {"values": {}, "summary": "Could not reach the City's address search",
                "messages": [f"{type(e).__name__}: {e}", "Fill in the zone and overlay values by hand."]}
    if not place:
        return {"values": {}, "summary": "Address not found in Toronto",
                "messages": ["Check the spelling (e.g. '123 Main St'), or fill in the values by hand."]}
    values["address"] = place["matched"] or address
    lon, lat = place["lon"], place["lat"]
    if not place["exact"]:
        messages.append(f"Closest match: {place['matched']}. Make sure it's the right property.")

    def layer(name, label):
        error = None
        for attempt in (1, 2):              # the City's servers are sometimes slow: try twice
            try:
                return features_at(SERVICES[name], lon, lat, fetch)
            except Exception as e:
                error = e
        messages.append(f"Couldn't read the {label} layer ({type(error).__name__}). Please answer that question by hand.")
        return None

    # Grey property (old by-law): STOP condition, so check it first
    former, not_part = layer("former", "former by-laws"), layer("not_part", "'not part of this by-law'")
    if former is not None and not_part is not None:
        grey = bool(former) or bool(not_part)
        values["grey_property"] = "yes" if grey else "no"
        if grey:
            name = (former[0].get("DISPLAY_LABEL") or former[0].get("BL_NAME")) if former else "not part of By-law 569-2013"
            messages.append(f"GREY property: still under an old by-law ({name}). The checker will stop.")

    zone = layer("zone", "zoning")
    if zone:
        z = zone[0]
        values["zone_label"] = z.get("ZN_STRING") or ""
        values["zone"] = z.get("ZN_ZONE") if z.get("ZN_ZONE") in ("RD", "R", "RS", "RT", "RM") else "Other"
        if z.get("ZN_EXCPTN_NO"):
            values["exception"] = str(z["ZN_EXCPTN_NO"])
        messages.append(f"Zone label: {values['zone_label']}")
    elif zone == []:
        messages.append("No 569-2013 zone found at this point.")

    height = layer("height", "height overlay")
    if height is not None:
        h = height[0] if height else {}
        values["ht"] = h.get("HT_HEIGHT") if h.get("HT_HEIGHT") is not None else "none"
        values["st"] = h.get("HT_STORIES") if h.get("HT_STORIES") is not None else "none"
        messages.append(f"Height overlay: {h.get('HT_STRING') or 'no HT/ST value'}")

    cov = layer("coverage", "lot coverage overlay")
    if cov is not None:
        values["coverage_overlay"] = cov[0]["ZN_COVERAGE"] if cov and cov[0].get("ZN_COVERAGE") is not None else "none"
        messages.append(f"Lot coverage overlay: {values['coverage_overlay']}{'%' if cov else ''}")

    hcd = layer("hcd", "heritage district")
    if hcd is not None:
        designated = [d for d in hcd if (d.get("DESIGNATION_TYPE") or "").startswith("Designated")]
        values["in_hcd"] = "yes" if designated else "no"
        for d in hcd:
            messages.append(f"Heritage Conservation District: {d.get('DISTRICT_NAME')} ({d.get('DESIGNATION_TYPE')}).")
        if hcd and not designated:
            messages.append("That district isn't in force yet (under study or appeal). Ask Heritage Planning whether it affects you.")

    ravine = layer("ravine", "ravine protection")
    if ravine is not None:
        values["ravine"] = "yes" if ravine else "no"

    trca = layer("trca", "TRCA regulation limit")
    if trca is not None:
        values["trca"] = "yes" if trca else "no"
        if trca:
            messages.append("Inside TRCA's regulated area (their map is approximate: TRCA confirms).")

    messages.append("Not looked up: designated heritage property (Part IV), trees, flightpath, lot size. Answer those by hand.")
    got = [k for k in values if k != "address"]
    return {"values": values, "messages": messages, "point": {"lat": lat, "lon": lon},
            "summary": f"Found {place['matched']}: filled in {len(got)} answers. Check them before relying on them."}
