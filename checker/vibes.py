"""Vibes check (Build Plan step 21): does the design fit the neighbourhood?

The AI reads the project (answers, description, drawing summary, check results) and
the guideline text in data/toronto/design_guidelines.json, and writes a few comments.
Every comment must name a guideline AND quote words from it.

CODE then checks each comment: the guideline must exist and must apply to this
project, and the quoted words must really be in that guideline's text. Comments
that fail are dropped. Comments are opinions for discussion: they never change a
PASS or FAIL (golden rule 2), and the page says so.
"""

import re

from .ai_client import ask_json, AIError
from .core import load_city
from .engine import run
from .fields import FIELD_BY_KEY

APPLIES = {   # which guideline groups fit which project types (besides "all")
    "Garden suite": {"garden"}, "Laneway suite": {"laneway"}, "Detached garage": {"garage"},
    "Front porch / front addition": {"front"}, "New detached house / houseplex (replacement)": {"front", "garage"},
}

SYSTEM = """You give a short "vibes check" on a small residential project in Toronto: how well it seems to fit the
neighbourhood, based ONLY on the guideline text you are given. Zoning numbers have already been checked by code;
don't repeat PASS/FAIL results or invent new rules.

Rules:
- 3 to 6 comments. Each comment names one guideline_id and copies a short "quote" word for word from that guideline's text.
- tone: "fits" (looks in keeping), "worth a look" (could go either way; a question to think about), or "concern"
  (likely to draw comments from neighbours, heritage staff or the Committee of Adjustment).
- Plain words, grade 8 reading level, 1 to 3 sentences each. Suggest something concrete to look at when you can.
- These are opinions for discussion, not decisions. Never say "approved", "allowed", "safe" or "will pass".
- If you don't know enough about the neighbourhood (you usually don't), say what to compare it with on the street.
- Only state facts the answers give. Each answer starts with its key (e.g. ac_location is where the air conditioner is,
  eaves_to_lot_line is about the eaves): don't move one item's number or place onto another item.
"""


def _squash(t):
    return re.sub(r"\s+", " ", str(t)).strip().lower()


def guidelines_for(answers):
    data = load_city("toronto").get("design_guidelines", {"guidelines": []})
    groups = {"all"} | APPLIES.get(answers.get("project_type", ""), set())
    if answers.get("in_hcd") in (True, "yes"):
        groups.add("heritage")
    return [g for g in data["guidelines"] if g["applies"] in groups]


def vibes_check(answers, drawings_summary="", client=None):
    answers = answers or {}
    if not answers.get("project_type"):
        raise AIError("Pick a project type first.")
    report = run(answers)
    if report.get("stopped"):
        raise AIError("The check stopped (for example a property with special rules), so there's nothing to compare yet.")
    gl = guidelines_for(answers)
    facts = [f"- {k} ({FIELD_BY_KEY[k]['label']}): {v}{(' ' + FIELD_BY_KEY[k].get('unit', '')) if FIELD_BY_KEY[k].get('unit') else ''}"
             for k, v in answers.items() if k in FIELD_BY_KEY and k not in ("description",)]
    fails = [f"{r['rule_id']}: {r['message']}" for r in report["results"] if r["status"] == "FAIL"][:10]
    flags = [f"{r['rule_id']}: {r['message']}" for r in report["results"] if r["status"] == "FLAG"][:8]
    prompt = (f"Project: {answers.get('project_type')}\nDescription: {answers.get('description') or '(none)'}\n"
              f"Drawings summary: {drawings_summary or '(no drawings uploaded)'}\n\nAnswers:\n" + "\n".join(facts) +
              "\n\nZoning fails found by code: " + ("; ".join(fails) or "none") +
              "\nFlags: " + ("; ".join(flags) or "none") +
              "\n\nGuidelines (id | name | text):\n" + "\n".join(f"{g['id']} | {g['name']} | {g['text']}" for g in gl))
    schema = {"type": "object", "properties": {
        "comments": {"type": "array", "items": {"type": "object", "properties": {
            "topic": {"type": "string"}, "tone": {"type": "string", "enum": ["fits", "worth a look", "concern"]},
            "comment": {"type": "string"}, "guideline_id": {"type": "string", "enum": [g["id"] for g in gl]},
            "quote": {"type": "string"}},
            "required": ["topic", "tone", "comment", "guideline_id", "quote"], "additionalProperties": False}}},
        "required": ["comments"], "additionalProperties": False}

    data, info = ask_json("vibes_check", SYSTEM, prompt, schema, max_tokens=3000, client=client)

    by_id = {g["id"]: g for g in gl}
    comments, dropped = [], []
    for c in data.get("comments", [])[:8]:
        g = by_id.get(c.get("guideline_id"))
        quote = str(c.get("quote", "")).strip().strip('"“”')
        if not g:
            dropped.append({"comment": c.get("comment", ""), "why": "names a guideline that doesn't apply"})
            continue
        if len(quote) < 8 or _squash(quote) not in _squash(g["text"]):
            dropped.append({"comment": c.get("comment", ""), "why": "the quote isn't in the guideline"})
            continue
        text = str(c.get("comment", ""))[:600]
        if re.search(r"\b(approved|will pass|safe)\b", text, re.I):     # code keeps the golden rule on wording
            text += " (This is an opinion, not an approval.)"
        comments.append({"topic": str(c.get("topic", ""))[:80], "tone": c.get("tone", "worth a look"), "comment": text,
                         "quote": quote, "guideline": g["name"], "guideline_id": g["id"], "kind": g["kind"], "link": g["link"]})
    return {"comments": comments, "dropped": dropped, "cost": info,
            "note": "Opinions for discussion, based on the guideline text shown. They never change a PASS or FAIL. "
                    "Summaries are this tool's paraphrase, not official wording: follow the links."}
