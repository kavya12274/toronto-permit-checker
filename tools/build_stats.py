"""Build the Toronto permit stats dashboard from the City's open data.

How long do Toronto building permits really take? This script reads the City of
Toronto Open Data dataset "Building Permits - Cleared Permits" (permits since 2017,
updated daily) and works out, for each type of low-rise project:
  - how many permits there were
  - the typical (median) number of days from application to permit issued
  - the middle half of cases (25th to 75th percentile)
  - the share issued within 10 business days (about 14 calendar days)
  - the trend by year

Run it (from the project folder; it downloads about 220 MB, so give it a few minutes):
    python3 tools/build_stats.py
Or, if you already downloaded the two CSVs:
    python3 tools/build_stats.py path/to/cleared.csv path/to/active.csv

It writes data/toronto/permit_stats.json, which the dashboard page reads.
Uses only what comes with Python. The big CSV is not kept in the project.

IMPORTANT for reading the numbers: "days to issue" counts calendar days from
application to permit issued. It includes time the applicant spends fixing an
incomplete application or a zoning problem, not just City review time.
"""

import csv
import json
import os
import statistics
import sys
import tempfile
import urllib.request
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "data", "toronto", "permit_stats.json")
URL = "https://ckan0.cf.opendata.inter.prod-toronto.ca/datastore/dump/a96c0ba4-3026-402b-b09d-5b1268b8f810"
# Active permits (issued but not closed yet). Without these, recent years look faster than they are,
# because slow permits from those years are still open and not in the "cleared" file.
URL_ACTIVE = "https://ckan0.cf.opendata.inter.prod-toronto.ca/datastore/dump/6d0229af-bc54-46de-9c2b-26759b01dd05"
DATASET = "https://open.toronto.ca/dataset/building-permits-cleared-permits/"

# City "WORK" values -> the project types in this tool
GROUPS = [
    ("Rear or second-storey addition", "rear", {("Small Residential Projects", "Addition(s)"), ("Small Residential Projects", "Addition")}),
    ("Deck", "deck", {("Small Residential Projects", "Deck")}),
    ("Front porch", "porch", {("Small Residential Projects", "Porch")}),
    ("Garage or carport", "garage", {("Small Residential Projects", "Garage"), ("Small Residential Projects", "Carport")}),
    ("Shed / accessory building", "shed", {("Small Residential Projects", "Accessory Building(s)")}),
    ("Garden or laneway suite", "garden", {("Small Residential Projects", "New Laneway / Rear Yard Suite")}),
    ("Secondary suite", "secondary", {("Small Residential Projects", "Second Suite (New)")}),
    ("Interior alterations / basement", "interior", {("Small Residential Projects", "Interior Alterations"),
                                                     ("Small Residential Projects", "Finishing Basements")}),
    ("Underpinning", "interior", {("Small Residential Projects", "Underpinning")}),
    ("Pool fence enclosure", "pool", {("Small Residential Projects", "Pool Fence Enclosure")}),
    ("New house", "newhouse", {("New Houses", "New Building"), ("New Houses", "New Building - Lead")}),
]


def parse(d):
    try:
        y, m, dd = d[:10].split("-")
        return date(int(y), int(m), int(dd))
    except (ValueError, AttributeError):
        return None


def pct(sorted_vals, p):
    if not sorted_vals:
        return None
    k = (len(sorted_vals) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(sorted_vals) - 1)
    return round(sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo))


def download(url, name):
    tmp = os.path.join(tempfile.gettempdir(), name)
    print(f"Downloading {name}…")
    req = urllib.request.Request(url, headers={"User-Agent": "permit-checker-prototype"})
    try:
        with urllib.request.urlopen(req, timeout=600) as r, open(tmp, "wb") as f:
            while chunk := r.read(1 << 20):
                f.write(chunk)
    except Exception as e:                          # python.org Python on a Mac: certificate problem -> use curl
        import subprocess
        if subprocess.run(["curl", "-sSL", "--fail", "-m", "900", "-o", tmp, url]).returncode != 0:
            sys.exit(f"Download failed ({e}). Download the CSVs from {DATASET} and pass their paths.")
    return tmp


def main():
    paths = sys.argv[1:3]
    temps = []
    if not paths:
        temps = [download(URL, "toronto_cleared_permits.csv"), download(URL_ACTIVE, "toronto_active_permits.csv")]
        paths = temps

    lookup = {pair: (name, key) for name, key, pairs in GROUPS for pair in pairs}
    days = {name: [] for name, _, _ in GROUPS}
    by_year = {name: {} for name, _, _ in GROUPS}
    keys = {name: key for name, key, _ in GROUPS}
    newest = None
    seen = set()                                     # the same permit can be in both files
    rows = (row for path in paths for row in csv.DictReader(open(path, newline="", encoding="utf-8", errors="ignore")))
    for row in rows:
        pid = (row.get("PERMIT_NUM", ""), row.get("REVISION_NUM", ""))
        if pid in seen:
            continue
        seen.add(pid)
        g = lookup.get((row["PERMIT_TYPE"].strip(), row["WORK"].strip()))
        if not g:
            continue
        a, i = parse(row["APPLICATION_DATE"]), parse(row["ISSUED_DATE"])
        if not a or not i or i < a or a.year < 2017:
            continue
        n = (i - a).days
        if n > 3650:                             # data errors
            continue
        name = g[0]
        days[name].append(n)
        by_year[name].setdefault(a.year, []).append(n)
        newest = max(newest or i, i)

    groups = []
    for name, vals in days.items():
        vals.sort()
        if not vals:
            continue
        groups.append({
            "name": name, "project_key": keys[name], "permits": len(vals),
            "median_days": pct(vals, 0.5), "p25_days": pct(vals, 0.25), "p75_days": pct(vals, 0.75),
            "within_14_days_pct": round(100 * sum(1 for v in vals if v <= 14) / len(vals)),
            "over_90_days_pct": round(100 * sum(1 for v in vals if v > 90) / len(vals)),
            "by_year": {str(y): {"median_days": pct(sorted(v), 0.5), "permits": len(v)}
                        for y, v in sorted(by_year[name].items()) if len(v) >= 20},
        })
    groups.sort(key=lambda g: -g["permits"])
    all_vals = sorted(v for vals in days.values() for v in vals)
    out = {
        "source": "City of Toronto Open Data: Building Permits - Cleared Permits (since 2017) and Active Permits",
        "link": DATASET,
        "built_on": date.today().isoformat(),
        "data_up_to": newest.isoformat() if newest else None,
        "measure": "Calendar days from application to permit issued, for permits that were issued. Includes time the "
                   "applicant spent fixing incomplete applications or zoning problems, not only City review time. "
                   "The latest year is incomplete: applications still waiting for a permit aren't counted yet, so it "
                   "can look faster than it will end up.",
        "overall": {"permits": len(all_vals), "median_days": pct(all_vals, 0.5),
                    "within_14_days_pct": round(100 * sum(1 for v in all_vals if v <= 14) / len(all_vals)) if all_vals else None},
        "groups": groups,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(f"Wrote {OUT}: {len(all_vals)} permits in {len(groups)} project types (data up to {out['data_up_to']}).")
    for g in groups:
        print(f"  {g['name']:<36} {g['permits']:>6} permits · median {g['median_days']:>4} days · "
              f"{g['within_14_days_pct']:>3}% within 14 days · {g['over_90_days_pct']:>3}% over 90 days")
    for t in temps:
        os.remove(t)


if __name__ == "__main__":
    main()
