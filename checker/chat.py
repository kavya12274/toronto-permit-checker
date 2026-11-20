"""The chatbot: "Ask about my project".

It answers questions about YOUR results, using:
  - your answers and the checker's results (sent in with every question)
  - a short summary of any drawings you uploaded
  - tools that run OUR code (the AI asks, our code answers):
      what_if        -> runs the real checker with changed numbers and reports what changes
      get_rule       -> the rule's limit, section and source from the Rules Table
      define_term    -> the by-law dictionary
      suggest_answer -> offers to put a number into your form (you tap to confirm)

Golden rules, enforced in code where possible:
  - The AI never decides PASS/FAIL: for "what if" it must call what_if, and the reply shows
    the checker's own result. The system prompt forbids judging rules itself.
  - Rule IDs and sections come from the results/tools, so the AI can cite them.
  - Never "approved" or "safe": code adds a reminder if those words appear.
  - Building Code answers always say a qualified designer must confirm.
"""

import json
import re

from .ai_client import ask_with_tools, AIError
from .core import load_city
from .engine import run
from .fields import FIELDS, FIELD_BY_KEY
from .plan_reader import check_suggestion, SKIP

MAX_HISTORY = 12          # earlier messages are dropped, to keep each question cheap
MAX_QUESTION = 1500

SYSTEM = """You are the helper inside a Toronto low-rise permit PRE-CHECK tool for homeowners. You explain the tool's
results in plain words (grade 8). Be short: usually 2 to 5 sentences, or a short list.

Strict rules:
1. Never decide yourself whether something passes or fails. Use the results below. For any "what if I change X"
   question, call the what_if tool and report what the checker says.
2. When you mention a rule, give its rule ID and by-law section from the results or get_rule (e.g. "RD-18, s. 10.20.40.70").
3. Missing information means NEED MORE INFO, never a pass.
4. Never say "approved", "allowed for sure" or "safe". This is a draft pre-check, not an approval.
5. For Building Code (safety) topics, always say a qualified designer must confirm.
6. If the tool doesn't cover something (site-specific exceptions, other cities, legal disputes), say so and suggest
   Toronto Building (311) or a qualified designer. Don't guess.
7. If the user tells you a measurement, you may call suggest_answer so they can add it to the form with one tap.
8. Use define_term for zoning words the user asks about.
"""


def _context(answers, drawings_summary):
    r = run(answers)
    lines = [f"Project type: {answers.get('project_type') or 'not chosen'}",
             f"Permit needed? {(r.get('permit') or {}).get('answer', '?')}: {(r.get('permit') or {}).get('reason', '')}",
             f"Overall: {r.get('overall', '')}", f"Counts: {r.get('counts')}"]
    if r.get("stopped"):
        lines.append("THE CHECK STOPPED: " + (r["results"][0]["message"] if r["results"] else ""))
    lines.append("\nAnswers in the form:")
    for k, v in answers.items():
        if k in FIELD_BY_KEY and k != "description":
            f = FIELD_BY_KEY[k]
            lines.append(f"- {k} ({f['label']}): {v} {f.get('unit', '')}".rstrip())
    if answers.get("description"):
        lines.append(f"Description: {answers['description'][:600]}")
    lines.append("\nResults that aren't PASS (rule | status | message | limit | value | section):")
    for x in r["results"]:
        if x["status"] != "PASS":
            lines.append(f"- {x['rule_id']} | {x['status']} | {x['message']} | {x.get('limit')} | {x.get('value')} | {x['section']}"
                         + (f" | fix: {x['fix']}" if x.get("fix") else ""))
    passed = [x["rule_id"] for x in r["results"] if x["status"] == "PASS"]
    lines.append(f"\nRules that PASS: {', '.join(passed) or 'none'}")
    if r.get("wait"):
        lines.append(f"Typical Toronto wait for this permit type: {r['wait']['median_days']} days (median).")
    if drawings_summary:
        lines.append(f"\nUploaded drawings (AI summary, may be wrong): {drawings_summary[:800]}")
    return "\n".join(lines)[:14000]


def _tools():
    keys = [f["key"] for f in FIELDS if f["key"] not in SKIP and f["type"] != "text"]
    change = {"type": "object", "properties": {"key": {"type": "string", "enum": keys}, "value": {"type": "string"}},
              "required": ["key", "value"], "additionalProperties": False}
    return [
        {"name": "what_if", "strict": True,
         "description": "Run the real permit checker with some answers changed, and get back which results change. "
                        "Use for every 'what if' or 'would it pass if' question.",
         "input_schema": {"type": "object", "properties": {"changes": {"type": "array", "items": change}},
                          "required": ["changes"], "additionalProperties": False}},
        {"name": "get_rule", "strict": True, "description": "Look up one rule from the Rules Table by its ID (e.g. RD-18).",
         "input_schema": {"type": "object", "properties": {"rule_id": {"type": "string"}},
                          "required": ["rule_id"], "additionalProperties": False}},
        {"name": "define_term", "strict": True, "description": "Look up a zoning word in the by-law dictionary.",
         "input_schema": {"type": "object", "properties": {"term": {"type": "string"}},
                          "required": ["term"], "additionalProperties": False}},
        {"name": "suggest_answer", "strict": True,
         "description": "Offer to put a value the user told you into their form. The user must tap to confirm.",
         "input_schema": {"type": "object", "properties": {"key": {"type": "string", "enum": keys},
                                                           "value": {"type": "string"}, "quote": {"type": "string"}},
                          "required": ["key", "value", "quote"], "additionalProperties": False}},
    ]


def _brief(x):
    return {"rule_id": x["rule_id"], "status": x["status"], "message": x["message"], "limit": x.get("limit"),
            "value": x.get("value"), "section": x["section"]}


def chat(messages, answers, drawings_summary="", client=None):
    """messages: [{"role": "user"|"assistant", "content": "text"}], the last one is the new question."""
    answers = answers or {}
    msgs = [{"role": m["role"], "content": str(m.get("content", ""))[:MAX_QUESTION * 3]}
            for m in (messages or []) if m.get("role") in ("user", "assistant") and str(m.get("content", "")).strip()]
    msgs = msgs[-MAX_HISTORY:]
    while msgs and msgs[0]["role"] != "user":
        msgs.pop(0)
    if not msgs or msgs[-1]["role"] != "user":
        raise AIError("Type a question first.")
    if len(msgs[-1]["content"]) > MAX_QUESTION:
        raise AIError(f"Please keep questions under {MAX_QUESTION} characters.")

    data = load_city("toronto")
    rules = data["rules_by_id"]
    terms = {t["term"].lower(): t for t in (data.get("glossary") or {}).get("terms", [])}
    before = {x["rule_id"]: x for x in run(answers)["results"]}
    suggestions, what_ifs = [], []

    def run_tool(name, inp):
        if name == "what_if":
            changed, bad = dict(answers), []
            for c in inp.get("changes", [])[:8]:
                clean, _, problem = check_suggestion(c.get("key"), c.get("value"), "", "")
                if clean is None:
                    bad.append(f"{c.get('key')}: {problem}")
                else:
                    changed[c["key"]] = clean
            after = run(changed)
            diffs = []
            for x in after["results"]:
                b = before.get(x["rule_id"])
                if not b or b["status"] != x["status"] or b.get("value") != x.get("value"):
                    diffs.append({"before": b["status"] if b else "not checked", **_brief(x)})
            out = {"changes_used": {k: changed[k] for k in changed if changed.get(k) != answers.get(k)},
                   "rejected_changes": bad, "results_that_changed": diffs[:25], "new_counts": after["counts"],
                   "new_overall": after["overall"], "still_failing": [_brief(x) for x in after["results"] if x["status"] == "FAIL"][:10]}
            what_ifs.append({"changes": out["changes_used"], "counts": after["counts"], "overall": after["overall"],
                             "changed": [{"rule_id": d["rule_id"], "before": d["before"], "after": d["status"]} for d in diffs[:10]]})
            return out
        if name == "get_rule":
            r = rules.get(str(inp.get("rule_id", "")).strip().upper())
            return r if r else {"error": "No rule with that ID in the Rules Table."}
        if name == "define_term":
            q = str(inp.get("term", "")).lower().strip()
            t = terms.get(q) or next((v for k, v in terms.items() if q in k or k in q), None)
            return t if t else {"error": "That word isn't in the by-law dictionary."}
        if name == "suggest_answer":
            clean, _, problem = check_suggestion(inp.get("key"), inp.get("value"), "", "")
            if clean is None:
                return {"error": problem}
            f = FIELD_BY_KEY[inp["key"]]
            suggestions.append({"key": inp["key"], "label": f.get("simple") or f["label"], "unit": f.get("unit", ""),
                                "type": f["type"], "value": clean, "quote": str(inp.get("quote", ""))[:160]})
            return {"ok": "Shown to the user as a button. It is only added if they tap it."}
        return {"error": "unknown tool"}

    system = SYSTEM + "\n\n--- THIS PROJECT ---\n" + _context(answers, drawings_summary)
    reply, info, calls = ask_with_tools("chat", system, msgs, _tools(), run_tool, client=client)
    if re.search(r"\b(approved|safe)\b", reply, re.I):
        reply += "\n\n(Reminder: this is a draft pre-check, not an approval.)"
    return {"reply": reply, "suggestions": suggestions[:6], "what_ifs": what_ifs, "cost": info,
            "tools_used": [c["tool"] for c in calls]}
