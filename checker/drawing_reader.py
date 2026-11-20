"""AI drawing reader: read uploaded drawings, PDFs and photos.

Three jobs in one AI request:
  1. Read numbers off the drawings (setbacks, height, lot size...) as suggested form answers.
  2. Check the drawings against the City's submission checklist for this project
     (from the permit roadmap): is each required drawing there, and does it show what it should?
  3. Spot places where the drawings disagree with each other.

Then CODE checks the AI's answer:
  - every suggested value goes through the same checks as the plan reader (real question,
    sensible number, exact choice); bad ones are dropped
  - checklist items must be ones we asked about
  - code compares the drawing values with what's already in the form and lists every
    difference itself (the AI can miss these; code can't)

Nothing is added to the form until the user ticks it. Suggestions from drawings start
UNTICKED, because code can't see the drawing to confirm the number: the user must look.
The rules, not the AI, decide PASS/FAIL. Files are not saved anywhere: they're sent to
Anthropic for this one read and then forgotten. Only the AI's short summary is kept in the
browser, so the chatbot can talk about the drawings later.
"""

import base64
import re

from .ai_client import ask_json, settings, AIError
from .engine import run
from .fields import FIELDS, FIELD_BY_KEY
from .plan_reader import check_suggestion, SKIP

TYPES = {"application/pdf": "pdf", "image/png": "image", "image/jpeg": "image", "image/webp": "image", "image/gif": "image"}
MAX_FILES = 5
MAX_FILE_MB = 10
MAX_TOTAL_MB = 20          # the API takes up to 32 MB per request, and files grow by a third when encoded
MAX_PDF_PAGES = 40         # keeps one read under about $0.02 on Haiku

SYSTEM = """You review drawings for a small residential building project in Toronto (site plans, floor plans,
elevations, sections, surveys, or photos of sketches). You are not approving anything. You report what the
drawings show, so the homeowner can check it.

Rules:
- Only report a value when it is written or dimensioned on a drawing. Never measure with a ruler, scale or guess.
- Suggestions come from the drawings only: don't copy values from the form answers or the description.
- For each value, say where you read it ("where"): file name, page and which drawing, e.g. "plans.pdf p.1, site plan".
- Numbers: just the number in the question's unit (convert feet and inches to metres, keep the original in "where").
- Keep the NEW work and the EXISTING house apart. A size written for the new part only (e.g. "addition height 4.2,
  depth 3.6") is not the whole building's height, depth or storeys: only use it for a question that is about the new part.
- Yes/no: "yes" or "no". Choices: copy one listed choice exactly.
- Checklist: for each item you are given, say "shown", "missing" or "unclear", with a short note of what you saw.
- Conflicts: list places where two drawings, or a drawing and the description, disagree (e.g. "elevation shows 3 storeys,
  floor plans show 2"). Don't list differences you aren't sure about.
- "summary": 2 to 4 plain sentences on what the drawings show (what is being built, the main sizes).
"""


def _pdf_pages(data):
    """Count pages in a PDF without any extra library (good enough for a cost limit)."""
    return max(1, len(re.findall(rb"/Type\s*/Page(?!s)", data)))


def _checklist_items(answers):
    report = run(answers)
    rm = report.get("roadmap") or {}
    items = [d["item"] for d in (rm.get("checklist") or {}).get("drawings", [])]
    details = {d["item"]: d.get("detail", "") for d in (rm.get("checklist") or {}).get("drawings", [])}
    general = ["Drawn to scale and fully dimensioned", "Signed and dated",
               "No personal information (names, phone numbers) on the drawings"]
    return items + general, details


def _questions():
    lines = []
    for f in FIELDS:
        if f["key"] in SKIP or f["type"] == "text":
            continue
        extra = " / ".join(f.get("choices") or []) or f.get("unit", "")
        lines.append(f"{f['key']} | {f['label']} | {f['type']} | {extra}")
    return "\n".join(lines)


def read_drawings(files, answers=None, client=None):
    """files: [{"name", "type", "data" (base64)}]. Returns suggestions, checklist, conflicts, summary, cost."""
    answers = answers or {}
    if not files:
        raise AIError("Choose at least one drawing, PDF or photo first.")
    if len(files) > MAX_FILES:
        raise AIError(f"Please upload up to {MAX_FILES} files at a time.")

    blocks, total, names = [], 0, []
    for i, f in enumerate(files, 1):
        kind = TYPES.get(f.get("type", ""))
        name = str(f.get("name", f"file {i}"))[:80]
        if not kind:
            raise AIError(f"{name}: only PDF, PNG, JPG, WEBP or GIF files can be read.")
        try:
            raw = base64.b64decode(f.get("data", ""), validate=True)
        except ValueError:
            raise AIError(f"{name}: the file couldn't be read. Try saving it again.")
        mb = len(raw) / 1_000_000
        total += mb
        if mb > MAX_FILE_MB:
            raise AIError(f"{name} is {mb:.0f} MB. Please keep each file under {MAX_FILE_MB} MB.")
        if total > MAX_TOTAL_MB:
            raise AIError(f"Together the files are over {MAX_TOTAL_MB} MB. Upload fewer at a time.")
        blocks.append({"type": "text", "text": f"File {i}: {name}"})
        if kind == "pdf":
            pages = _pdf_pages(raw)
            if pages > MAX_PDF_PAGES:
                raise AIError(f"{name} has about {pages} pages. Please upload only the drawing pages (up to {MAX_PDF_PAGES}).")
            blocks.append({"type": "document", "_pages": pages,
                           "source": {"type": "base64", "media_type": "application/pdf", "data": f["data"]}})
        else:
            blocks.append({"type": "image", "source": {"type": "base64", "media_type": f["type"], "data": f["data"]}})
        names.append(name)

    items, details = _checklist_items(answers)
    project = answers.get("project_type", "not chosen yet")
    known = {k: v for k, v in answers.items() if k in FIELD_BY_KEY and k not in SKIP}
    blocks.append({"type": "text", "text":
                   f"Project type: {project}\nDescription from the homeowner: {answers.get('description') or '(none)'}\n"
                   f"Answers already in the form: {known}\n\n"
                   "Checklist items to check (use these names exactly):\n" +
                   "\n".join(f"- {it}: {details.get(it, '')}" for it in items) +
                   "\n\nForm questions you may fill in (key | question | type | unit or choices):\n" + _questions()})

    keys = [f["key"] for f in FIELDS if f["key"] not in SKIP and f["type"] != "text"]
    schema = {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "suggestions": {"type": "array", "items": {"type": "object", "properties": {
                "key": {"type": "string", "enum": keys}, "value": {"type": "string"}, "where": {"type": "string"}},
                "required": ["key", "value", "where"], "additionalProperties": False}},
            "checklist": {"type": "array", "items": {"type": "object", "properties": {
                "item": {"type": "string", "enum": items}, "status": {"type": "string", "enum": ["shown", "missing", "unclear"]},
                "note": {"type": "string"}}, "required": ["item", "status", "note"], "additionalProperties": False}},
            "conflicts": {"type": "array", "items": {"type": "object", "properties": {
                "what": {"type": "string"}, "where": {"type": "string"}},
                "required": ["what", "where"], "additionalProperties": False}},
        },
        "required": ["summary", "suggestions", "checklist", "conflicts"], "additionalProperties": False,
    }

    data, info = ask_json("drawing_reader", SYSTEM, blocks, schema, max_tokens=6000, client=client,
                          model=settings()["drawing_model"])

    suggestions, dropped, seen, conflicts, agrees = [], [], set(), [], []
    lower_names = [n.lower() for n in names]
    for s in data.get("suggestions", []):
        key = s.get("key", "")
        if key in seen:
            continue
        clean, _, problem = check_suggestion(key, s.get("value", ""), "", "")
        where = str(s.get("where", ""))
        if clean is None:
            dropped.append({"key": key, "value": s.get("value", ""), "why": problem})
            continue
        # Code checks the AI read it off a drawing: "where" must name one of the uploaded files.
        # (Otherwise it's just repeating the form or the description, which isn't new information.)
        if not any(n in where.lower() for n in lower_names):
            dropped.append({"key": key, "value": s.get("value", ""), "why": "not read from a drawing (no file named)"})
            continue
        seen.add(key)
        f = FIELD_BY_KEY[key]
        cur = answers.get(key)
        same = cur == clean or (isinstance(cur, (int, float)) and isinstance(clean, (int, float))
                                and not isinstance(cur, bool) and abs(cur - clean) < 0.01)
        if same:                                        # the drawing agrees with the form: nothing to add
            agrees.append(f.get("simple") or f["label"])
            continue
        suggestions.append({"key": key, "label": f.get("simple") or f["label"], "unit": f.get("unit", ""),
                            "type": f["type"], "value": clean, "where": str(s.get("where", ""))[:160], "current": cur})
        # Code's own conflict check: the drawing says one thing, the form says another
        if cur not in (None, ""):                         # (equal values were skipped above)
            unit = f" {f['unit']}" if f.get("unit") else ""
            conflicts.append({"what": f"{f['label']}: your form says {cur}{unit}, the drawing shows {clean}{unit}.",
                              "where": s.get("where", ""), "by": "code"})
    for c in data.get("conflicts", []):
        conflicts.append({"what": str(c.get("what", ""))[:300], "where": str(c.get("where", ""))[:160], "by": "AI"})

    checklist = []
    by_item = {c["item"]: c for c in data.get("checklist", []) if c.get("item") in items}
    for it in items:                                    # every item, in the roadmap's order; none silently skipped
        c = by_item.get(it)
        checklist.append({"item": it, "status": c["status"] if c else "unclear",
                          "note": str(c["note"])[:300] if c else "The AI didn't say."})

    return {"files": names, "summary": str(data.get("summary", ""))[:800], "suggestions": suggestions, "agrees": agrees,
            "dropped": dropped, "checklist": checklist, "conflicts": conflicts[:15], "cost": info,
            "note": "Suggestions only. The AI can misread drawings: check every number against your drawing before adding it. "
                    "This is not a plans review, and only Toronto Building can approve drawings."}
