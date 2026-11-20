"""Re-import the planning workbook into the data files the app reads.

Golden rule 1: rules live in DATA, not in code. This script turns your
spreadsheet into JSON files in data/toronto/. Run it again every time you
change a rule, a number or a test in the workbook.

How to run it (in Terminal, from this folder):
    python3 import_workbook.py "/Users/you/Downloads/Toronto Low-Rise Permit Checker – Sources.xlsx"

If you leave out the file name, it looks for the newest
"Toronto Low-Rise Permit Checker*.xlsx" in your Downloads folder.

Another city? Make a workbook with the same tabs and run:
    python3 import_workbook.py their_workbook.xlsx --city ottawa
That writes data/ottawa/ and leaves Toronto alone.

It uses only what comes with Python (no installs). An .xlsx file is really a
zip of XML files, so we open the zip and read the XML ourselves.
"""

import glob
import json
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))

# XML "namespaces" used inside every .xlsx file (just labels, not web links we visit)
NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
}


# ---------------------------------------------------------------- reading the .xlsx

def _column_number(cell_ref):
    """'M12' -> 12 (zero-based column index for column M)."""
    letters = re.match(r"[A-Z]+", cell_ref).group()
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def read_workbook(path):
    """Return {tab name: list of rows}. Each row is a list of cell texts.
    Hyperlinks (like the 'Open' links) are returned as the real web address."""
    z = zipfile.ZipFile(path)
    names = z.namelist()

    # 1) Shared strings: most text in a workbook is stored once here and referenced by number.
    shared = []
    if "xl/sharedStrings.xml" in names:
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in root.findall("m:si", NS):
            shared.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["m"])))

    # 2) Which file holds which tab.
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    rel_target = {r.get("Id"): r.get("Target") for r in rels}

    tabs = {}
    for sheet in wb.find("m:sheets", NS):
        tab_name = sheet.get("name")
        target = rel_target[sheet.get("{%s}id" % NS["r"])].lstrip("/")
        sheet_path = target if target.startswith("xl/") else "xl/" + target
        root = ET.fromstring(z.read(sheet_path))

        # 3) Hyperlinks for this tab: cell ref -> web address.
        links = {}
        rel_path = sheet_path.replace("worksheets/", "worksheets/_rels/") + ".rels"
        if rel_path in names:
            link_rels = {r.get("Id"): r.get("Target")
                         for r in ET.fromstring(z.read(rel_path))}
            hl = root.find("m:hyperlinks", NS)
            if hl is not None:
                for h in hl:
                    rid = h.get("{%s}id" % NS["r"])
                    if rid in link_rels:
                        links[h.get("ref")] = link_rels[rid]

        # 4) The cells themselves.
        rows = []
        for row in root.iter("{%s}row" % NS["m"]):
            cells = {}
            for c in row.findall("m:c", NS):
                ref, kind = c.get("r"), c.get("t")
                v = c.find("m:v", NS)
                if kind == "s" and v is not None:
                    text = shared[int(v.text)]
                elif kind == "inlineStr":
                    text = "".join(t.text or "" for t in c.iter("{%s}t" % NS["m"]))
                else:
                    text = v.text if v is not None else ""
                cells[_column_number(ref)] = text
                if ref in links:
                    cells[("link", _column_number(ref))] = links[ref]
            if cells:
                width = max(k for k in cells if isinstance(k, int)) + 1
                values = [cells.get(i, "") for i in range(width)]
                row_links = {i: cells[("link", i)] for i in range(width) if ("link", i) in cells}
                rows.append((values, row_links))
        tabs[tab_name] = rows
    return tabs


def table(rows, link_columns=()):
    """Turn rows (first row = headers) into a list of dicts. Blank rows are skipped.
    For each column in link_columns, a 'X url' field is added with the real link."""
    if not rows:
        return []
    headers = [h.strip() for h in rows[0][0]]
    out = []
    for values, links in rows[1:]:
        if not any(str(v).strip() for v in values):
            continue
        item = {}
        for i, h in enumerate(headers):
            if not h:
                continue
            item[h] = values[i].strip() if i < len(values) else ""
            if h in link_columns:
                item[h + " url"] = links.get(i, "")
        out.append(item)
    return out


def _from_header(rows, first_header):
    """Skip title lines until the row whose first cell is first_header."""
    for i, (values, _) in enumerate(rows):
        if values and values[0].strip() == first_header:
            return rows[i:]
    return rows


def to_number(text):
    """'0.6' -> 0.6, '15' -> 15, '' -> None. Leaves words alone (returns None)."""
    try:
        n = float(str(text).replace(",", ""))
        return int(n) if n.is_integer() else n
    except ValueError:
        return None


# ---------------------------------------------------------------- shaping the data

def build_rules(rows):
    """Rules Table -> list of rule dicts with short, code-friendly names."""
    rules = []
    for r in table(rows, link_columns=("Source link",)):
        if not r.get("Rule ID"):
            continue
        rules.append({
            "id": r["Rule ID"],
            "project_type": r.get("Project type", ""),
            "category": r.get("Category", ""),
            "rule": r.get("Rule (plain language)", ""),
            "limit": to_number(r.get("Limit", "")),
            "limit_text": r.get("Limit", ""),
            "unit": r.get("Unit", ""),
            "applies_when": r.get("Applies when", ""),
            "source": r.get("Source", ""),
            "section": r.get("Section", ""),
            "check_type": r.get("Check type", ""),
            "confidence": r.get("Confidence", "") or "Verify",
            "verified_vs_pdf": r.get("Verified vs PDF", "") in ("1", "TRUE", "True", "true", "Yes"),
            "link": r.get("Source link url", "") or "",
            "notes": r.get("Notes", ""),
        })
    return rules


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    city = "toronto"
    if "--city" in sys.argv:
        city = sys.argv[sys.argv.index("--city") + 1]
        if city in args:
            args.remove(city)

    if args:
        path = args[0]
    else:
        found = sorted(glob.glob(os.path.expanduser("~/Downloads/Toronto Low-Rise Permit Checker*.xlsx")),
                       key=os.path.getmtime)
        if not found:
            sys.exit("Could not find the workbook. Run: python3 import_workbook.py path/to/workbook.xlsx")
        path = found[-1]

    print(f"Reading {path}")
    tabs = read_workbook(path)
    needed = ["Read Me", "Sources", "Project Types", "Rules Table", "Test Cases", "Build Plan"]
    missing = [t for t in needed if t not in tabs]
    if missing:
        sys.exit(f"The workbook is missing these tabs: {', '.join(missing)}")

    out_dir = os.path.join(HERE, "data", city)
    os.makedirs(out_dir, exist_ok=True)

    rules = build_rules(tabs["Rules Table"])
    ids = [r["id"] for r in rules]
    dupes = sorted({i for i in ids if ids.count(i) > 1})

    files = {
        "rules.json": rules,
        "project_types.json": table(tabs["Project Types"]),
        "test_cases.json": table(tabs["Test Cases"]),
        "sources.json": table(tabs["Sources"], link_columns=("Link",)),
        "build_plan.json": table(tabs["Build Plan"]),
        # Read Me has a title line first; the real table starts at the "Topic" header row.
        "read_me.json": table(_from_header(tabs["Read Me"], "Topic")),
    }
    for name, data in files.items():
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=1, ensure_ascii=False)

    # A small record of when and from what the data was imported (shown on the report).
    meta = {"imported_on": date.today().isoformat(), "workbook": os.path.basename(path),
            "rule_count": len(rules)}
    with open(os.path.join(out_dir, "import_info.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=1)

    # Summary for you
    by_prefix = {}
    for r in rules:
        by_prefix.setdefault(r["id"].split("-")[0], 0)
        by_prefix[r["id"].split("-")[0]] += 1
    print(f"Wrote {len(rules)} rules to data/{city}/rules.json")
    print("  by group: " + ", ".join(f"{k} {v}" for k, v in by_prefix.items()))
    print(f"  {len(files['project_types.json'])} project types, {len(files['test_cases.json'])} test cases, "
          f"{len(files['sources.json'])} sources, {len(files['build_plan.json'])} build steps")
    verified = sum(r["verified_vs_pdf"] for r in rules)
    print(f"  {verified} of {len(rules)} rules ticked 'Verified vs PDF'")
    if dupes:
        print(f"  WARNING: duplicate rule IDs: {', '.join(dupes)}")
    no_limit = [r["id"] for r in rules if r["limit_text"] and r["limit"] is None]
    if no_limit:
        print(f"  WARNING: these limits are not numbers: {', '.join(no_limit)}")


if __name__ == "__main__":
    main()
