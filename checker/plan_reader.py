"""AI plan reader (Build Plan step 20): turn a plain-words description into form answers.

How it stays safe:
  1. The AI may ONLY use the question keys from checker/fields.py, and must copy the
     exact words it read each value from (the "quote").
  2. Then CODE (not the AI) checks every suggestion:
       - the key is a real question
       - numbers are numbers in a sensible range, yes/no is yes or no,
         choices match the form's choices exactly
       - the quote really is in the description (if not, it's marked and left unticked)
  3. The web page shows each suggestion. The user ticks the ones to keep. Only then
     do they go into the form, and the normal checker decides PASS/FAIL (golden rule 2).
"""

import re

from .ai_client import ask_json, AIError
from .core import load_city
from .fields import FIELDS, FIELD_BY_KEY

MAX_CHARS = 3000                     # keeps each read cheap (well under a tenth of a cent on Haiku)
SKIP = {"description"}               # the description itself isn't something to fill in

SYSTEM = """You read a homeowner's description of a building project in Toronto and fill in a form.

Rules:
- Only fill in a question when the description clearly states the answer. Never guess or assume.
- Use only the question keys in the list below.
- "quote" must be copied exactly, word for word, from the description: the words you took the value from.
- Numbers: give just the number in the question's unit. If the description uses another unit
  (feet, inches, square feet), convert it and keep the original words in the quote.
- Sizes of only the NEW part (e.g. "an addition 4 m deep") are not the whole building's size: don't use them for
  building_depth or building_length unless the description gives the whole building's measurement.
- Yes/no questions: answer "yes" or "no".
- Choice questions: answer with one of the listed choices, copied exactly.
- If something in the description matters but doesn't fit any question, or is unclear, put a short
  note in "unclear". Do not explain anything else.

The questions (key | question | type | unit or choices):
"""


def _project_types():
    return [t["Project type"] for t in load_city("toronto")["project_types"]]


def _question_list():
    lines = []
    for f in FIELDS:
        if f["key"] in SKIP:
            continue
        choices = _project_types() if f["key"] == "project_type" else f.get("choices") or []
        extra = " / ".join(choices) if choices else f.get("unit", "")
        kind = {"overlay": "number (or none)"}.get(f["type"], f["type"])
        lines.append(f"{f['key']} | {f['label']} | {kind} | {extra}")
    return "\n".join(lines)


def _schema():
    keys = [f["key"] for f in FIELDS if f["key"] not in SKIP]
    return {
        "type": "object",
        "properties": {
            "suggestions": {"type": "array", "items": {
                "type": "object",
                "properties": {"key": {"type": "string", "enum": keys},
                               "value": {"type": "string"},
                               "quote": {"type": "string"}},
                "required": ["key", "value", "quote"], "additionalProperties": False}},
            "unclear": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["suggestions", "unclear"], "additionalProperties": False,
    }


def _squash(text):
    return re.sub(r"\s+", " ", str(text)).strip().lower()


def check_suggestion(key, value, quote, description):
    """Code checks one AI suggestion. Returns (clean value or None, quote_found, problem)."""
    f = FIELD_BY_KEY.get(key)
    if not f or key in SKIP:
        return None, False, "not a question in this form"
    raw = str(value).strip()
    clean = None
    if f["type"] in ("number", "overlay"):
        if f["type"] == "overlay" and raw.lower() in ("none", "no value"):
            clean = "none"
        else:
            try:
                n = float(raw.replace(",", "").split()[0])
            except (ValueError, IndexError):
                return None, False, f"'{raw}' isn't a number"
            if not (0 <= n <= 100000):
                return None, False, f"{raw} is outside a sensible range"
            clean = int(n) if n == int(n) else round(n, 3)
    elif f["type"] == "yesno":
        if raw.lower() not in ("yes", "no"):
            return None, False, f"'{raw}' isn't yes or no"
        clean = raw.lower() == "yes"
    elif f["type"] == "choice":
        choices = _project_types() if key == "project_type" else f.get("choices") or []
        match = next((c for c in choices if c.lower() == raw.lower()), None)
        if not match:
            return None, False, f"'{raw}' isn't one of the choices"
        clean = match
    else:
        clean = raw[:200]
    found = bool(quote) and _squash(quote) in _squash(description)
    return clean, found, ""


def read_plan(description, current=None, client=None):
    """Ask the AI for suggested answers, then check each one with code.

    Returns {"suggestions": [...], "dropped": [...], "unclear": [...], "cost": {...}}.
    Each suggestion: key, label, unit, type, value, quote, quote_found, current.
    """
    description = (description or "").strip()
    if len(description) < 10:
        raise AIError("Write a sentence or two about the project first (what you're building, sizes, distances).")
    if len(description) > MAX_CHARS:
        raise AIError(f"Please keep the description under {MAX_CHARS} characters.")
    current = current or {}

    data, info = ask_json("plan_reader", SYSTEM + _question_list(),
                          "Project description:\n\n" + description, _schema(), max_tokens=3000, client=client)

    suggestions, dropped, seen = [], [], set()
    for s in data.get("suggestions", []):
        key = s.get("key", "")
        if key in seen:                       # the AI gave the same question twice: keep the first
            continue
        clean, found, problem = check_suggestion(key, s.get("value", ""), s.get("quote", ""), description)
        if clean is None:
            dropped.append({"key": key, "value": s.get("value", ""), "why": problem})
            continue
        seen.add(key)
        f = FIELD_BY_KEY[key]
        suggestions.append({"key": key, "label": f.get("simple") or f["label"], "unit": f.get("unit", ""),
                            "type": f["type"], "value": clean, "quote": s.get("quote", ""), "quote_found": found,
                            "current": current.get(key)})
    return {"suggestions": suggestions, "dropped": dropped,
            "unclear": [u for u in data.get("unclear", []) if isinstance(u, str)][:8], "cost": info}
