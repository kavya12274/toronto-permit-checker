"""The building blocks every checker uses.

- load_city():  reads the data files for a city (rules, project types...)
- clean_inputs(): tidies the form answers (numbers, yes/no, zone label)
- Context:      holds the answers + rules, and records each result

A RESULT always has (golden rule 3):
  status      PASS / FAIL / NEED MORE INFO / FLAG
  limit       the number the rule allows/requires
  value       the user's number
  rule_id     e.g. RD-18
  section     the by-law section, e.g. 10.20.40.70(3)(B)
  confidence  High / Verify / Needs human check (from the Rules Table)
"""

import json
import os
import re

from .fields import FIELD_BY_KEY, label

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(HERE), "data")

PASS = "PASS"
FAIL = "FAIL"
NEED = "NEED MORE INFO"
FLAG = "FLAG"

DESIGNER_NOTE = "A qualified designer must confirm."   # golden rule 6


# ---------------------------------------------------------------- data

_cache = {}


def load_city(city="toronto"):
    """Read every JSON file in data/<city>/ into one dict (cached)."""
    if city in _cache:
        return _cache[city]
    folder = os.path.join(DATA_DIR, city)
    if not os.path.isdir(folder):
        raise FileNotFoundError(f"No data for city '{city}'. Run import_workbook.py first.")
    data = {}
    for name in os.listdir(folder):
        if name.endswith(".json"):
            with open(os.path.join(folder, name), encoding="utf-8") as f:
                data[name[:-5]] = json.load(f)
    data["rules_by_id"] = {r["id"]: r for r in data.get("rules", [])}
    _cache[city] = data
    return data


def reload_city(city="toronto"):
    _cache.pop(city, None)
    return load_city(city)


# ---------------------------------------------------------------- inputs

def parse_zone_label(text):
    """Read a zone label like 'RD (f12.0; a370; d0.6) (x1234)'.

    Returns {'zone': 'RD', 'f': 12.0, 'a': 370, 'd': 0.6, 'u': 'none', 'exception': '1234'}.
    If a label is given, any of f/a/d/u it does NOT show is set to 'none',
    because the label is the official place those values appear.
    """
    out = {}
    if not text or not str(text).strip():
        return out
    text = str(text).strip()
    m = re.match(r"\s*([A-Z]{1,3})\b", text)
    if m:
        out["zone"] = m.group(1)
    for key in ("f", "a", "d", "u"):
        found = re.search(r"[(;\s]" + key + r"\s*([0-9]+(?:\.[0-9]+)?)", text)
        out[key] = _num(found.group(1)) if found else "none"
    exc = re.search(r"\(\s*x\s*(\d+)\s*\)", text, re.I)
    if exc:
        out["exception"] = exc.group(1)
    return out


def _num(text):
    try:
        n = float(str(text).strip().replace(",", ""))
        return int(n) if n.is_integer() else n
    except (TypeError, ValueError):
        return None


def clean_inputs(raw):
    """Turn form answers into tidy Python values.
    Blank -> removed. Numbers -> numbers. 'yes'/'no' -> True/False.
    Overlay fields may be a number or 'none'."""
    out = {}
    for key, value in (raw or {}).items():
        if value is None or (isinstance(value, str) and not value.strip()):
            continue
        field = FIELD_BY_KEY.get(key)
        kind = field["type"] if field else "text"
        if kind == "number":
            n = _num(value)
            if n is not None:
                out[key] = n
        elif kind == "overlay":
            if str(value).strip().lower() in ("none", "no value", "n/a"):
                out[key] = "none"
            else:
                n = _num(value)
                if n is not None:
                    out[key] = n
        elif kind == "yesno":
            if isinstance(value, bool):
                out[key] = value
            elif str(value).strip().lower() in ("yes", "y", "true", "1"):
                out[key] = True
            elif str(value).strip().lower() in ("no", "n", "false", "0"):
                out[key] = False
        else:
            out[key] = value.strip() if isinstance(value, str) else value

    # The zone label fills in zone, f, a, d, u and exception unless typed separately.
    parsed = parse_zone_label(out.get("zone_label"))
    for key, value in parsed.items():
        out.setdefault(key, value)
    return out


# ---------------------------------------------------------------- context

class Context:
    """Holds one check: the answers, the rules, and the list of results."""

    def __init__(self, inputs, city="toronto"):
        self.city = city
        self.data = load_city(city)
        self.rules = self.data["rules_by_id"]
        self.inputs = clean_inputs(inputs)
        self.results = []
        self.notes = []          # general notes shown at the top of the report

    # ---- reading answers
    def get(self, key):
        return self.inputs.get(key)

    def has(self, key):
        return key in self.inputs

    def yes(self, key):
        return self.inputs.get(key) is True

    def no(self, key):
        return self.inputs.get(key) is False

    def num(self, key):
        v = self.inputs.get(key)
        return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None

    @property
    def project(self):
        return self.inputs.get("project_type", "")

    @property
    def zone(self):
        return (self.inputs.get("zone") or "").upper()

    def is_houseplex(self):
        return "houseplex" in (self.get("building_type") or "").lower()

    # ---- reading rules
    def rule(self, rule_id):
        return self.rules.get(rule_id)

    def limit(self, rule_id):
        """The number in the Limit column for this rule (None if blank)."""
        r = self.rules.get(rule_id)
        return r["limit"] if r else None

    # ---- recording results
    def add(self, rule_id, status, value=None, limit=None, message="", unit=None,
            fix=None, group=None, fix_data=None, asks=None):
        """Record one result. Section, confidence and link come from the Rules Table."""
        r = self.rules.get(rule_id)
        if r is None:
            # A rule the code knows about but the data no longer has: say so, never guess.
            self.results.append({
                "rule_id": rule_id, "status": FLAG, "title": "Rule missing from data file",
                "message": f"The code expected rule {rule_id} but it is not in rules.json. "
                           "Check the Rules Table and re-import.",
                "limit": None, "value": None, "unit": "", "section": "", "confidence": "Needs human check",
                "group": group or "Other", "link": "", "category": "", "fix": None})
            return
        confidence = r["confidence"] or "Verify"
        is_code = rule_id.startswith("BC-")
        if is_code:
            confidence = "Needs human check"            # step 8: always for Building Code
            if DESIGNER_NOTE not in message:
                message = (message + " " if message else "") + DESIGNER_NOTE
        self.results.append({
            "rule_id": rule_id,
            "status": status,
            "title": r["rule"],
            "category": r["category"],
            "message": message.strip(),
            "limit": limit,
            "value": value,
            "unit": r["unit"] if unit is None else unit,
            "section": r["section"],
            "source": r["source"],
            "confidence": confidence,
            "verified_vs_pdf": r["verified_vs_pdf"],
            "link": r["link"],
            "group": group or group_for(rule_id),
            "fix": fix,
            "fix_data": fix_data,
            "safety": is_code,
            "asks": asks or [],          # field keys still needed (for NEED MORE INFO)
        })

    def missing(self, *keys):
        """Return the keys that have no answer."""
        return [k for k in keys if not self.has(k)]

    def need(self, rule_id, keys, limit=None, why=""):
        """If any key is missing, record NEED MORE INFO and return True."""
        miss = self.missing(*keys)
        if miss:
            asks = "; ".join(label(k) for k in miss)
            end = "" if asks.endswith("?") else "."
            msg = (why + " " if why else "") + f"Please tell us: {asks}{end}"
            self.add(rule_id, NEED, limit=limit, message=msg, asks=miss)
            return True
        return False

    def check_max(self, rule_id, key, limit, message="", unit=None):
        """value must be <= limit."""
        if self.need(rule_id, [key], limit=limit):
            return None
        value = self.num(key)
        ok = value <= limit + 1e-9
        u = unit_str(self, rule_id, unit)
        self.add(rule_id, PASS if ok else FAIL, value=value, limit=limit, unit=unit,
                 message=message or f"Maximum {fmt(limit)}{u}; yours is {fmt(value)}{u}.",
                 fix_data=None if ok else {"kind": "max", "key": key, "value": value, "limit": limit})
        return ok

    def check_min(self, rule_id, key, limit, message="", unit=None):
        """value must be >= limit."""
        if self.need(rule_id, [key], limit=limit):
            return None
        value = self.num(key)
        ok = value >= limit - 1e-9
        u = unit_str(self, rule_id, unit)
        self.add(rule_id, PASS if ok else FAIL, value=value, limit=limit, unit=unit,
                 message=message or f"Minimum {fmt(limit)}{u}; yours is {fmt(value)}{u}.",
                 fix_data=None if ok else {"kind": "min", "key": key, "value": value, "limit": limit})
        return ok


def fmt(n):
    """Show numbers nicely: 10 -> '10.0', 0.45 -> '0.45'."""
    if n is None:
        return "?"
    if isinstance(n, (int, float)):
        n = round(float(n), 3)
        if n.is_integer() and abs(n) >= 100:       # 1000 mm, 370 m² (no ".0")
            return str(int(n))
        return f"{n:.1f}" if abs(n - round(n, 1)) < 1e-9 else f"{n:g}"
    return str(n)


def unit_str(ctx, rule_id, unit=None):
    u = unit if unit is not None else (ctx.rules.get(rule_id) or {}).get("unit", "")
    if not u:
        return ""
    return u if u.startswith("%") else " " + u


def group_for(rule_id):
    """Which part of the report a rule belongs to."""
    prefix = rule_id.split("-")[0]
    return {
        "P": "Does it need a permit?",
        "SS": "Suites", "GS": "Suites", "LS": "Suites",
        "ON": "Provincial rules",
        "BC": "Building Code (safety)",
        "AP": "Other approvals",
    }.get(prefix, "Zoning")
