"""Where the AI features show up in the report (Build Plan steps 20-22).

All built. Nothing in this file calls the AI: the AI runs only when the user presses
a button, and every request goes through checker/ai_client.py (the $5 budget guard).

  Step 20  AI plan reader        checker/plan_reader.py   (description -> answers to confirm)
           AI drawing reader     checker/drawing_reader.py (drawings/PDFs -> answers, checklist, conflicts)
           Chatbot               checker/chat.py           (explains results; "what if" runs the real checker)
  Step 21  Vibes check           checker/vibes.py          (opinions that quote the guidelines; never PASS/FAIL)
  Step 22  Shadow preview        checker/shadow.py         (plain maths, no AI)

The AI never decides PASS/FAIL (golden rule 2). engine.run() does.
"""

from .ai_client import status


def add_to_report(ctx, report):
    in_hcd = ctx.yes("in_hcd")
    report["ai"] = {
        "enabled": status()["enabled"],
        "plan_reader": {
            "status": "built",
            "text": "On step 1, describe your project and press Read my description. The AI suggests answers; "
                    "you confirm every one before anything is checked.",
        },
        "vibes_check": {
            "status": "built",
            "text": "Press Run vibes check for AI comments on how the design fits the neighbourhood, each quoting "
                    "Toronto's Official Plan Neighbourhoods policies"
                    + (" and the heritage district guidance" if in_hcd else "")
                    + ". Opinions only: they never change a PASS or FAIL.",
            "comments": [],
        },
        "shadow_preview": {"status": "built (no AI)"},
    }
