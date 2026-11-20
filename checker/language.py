"""Step 17: plain language and translation (no AI).

For every result we add:
  plain        a short simple-English sentence ("Not OK: the space to the side lot line. Limit: 0.9 m. Yours: 0.8 m.")
  plain_grade  its reading grade level (Flesch-Kincaid), checked by the tests to be grade 8 or lower
  translated   the same sentence in each language in data/toronto/translations.json

The wording lives in translations.json, not in code. Translations there were written
without an AI service and still need checking by fluent speakers. The full rule
details stay in English (shown under the simple sentence).
When AI is added later, it could translate the full details too. The PASS/FAIL
never changes with language.
"""

import re

from .core import fmt
from .fields import label, SIMPLE


def syllables(word):
    """Rough syllable count for English words (good enough for a readability score)."""
    w = word.lower().strip(".,:;!?()'\"")
    if not w or w.isdigit():
        return 1
    w = re.sub(r"e$", "", w)
    groups = re.findall(r"[aeiouy]+", w)
    return max(1, len(groups))


def grade_level(text):
    """Flesch-Kincaid grade level. Numbers and units count as one-syllable words."""
    sentences = max(1, len(re.findall(r"[.!?](\s|$)", text)))
    words = re.findall(r"[A-Za-z0-9.%²']+", text)
    words = [w for w in words if w.strip(".")]
    if not words:
        return 0
    syl = sum(syllables(w) for w in words)
    return round(0.39 * len(words) / sentences + 11.8 * syl / len(words) - 15.59, 1)


def sentence(lang_block, en_block, r, asks_text):
    T = lang_block.get("templates", {})
    G = lang_block.get("glossary", {})
    thing = (lang_block.get("by_rule", {}).get(r["rule_id"]) or G.get(r["category"])
             or en_block["glossary"].get(r["category"]) or r["category"].lower())
    has_nums = r["limit"] is not None and r["value"] is not None
    unit = r.get("unit") or ""
    lim = f"{fmt(r['limit'])}{'' if not unit or unit.startswith('%') else ' '}{unit}" if r["limit"] is not None else ""
    val = f"{fmt(r['value'])}{'' if not unit or unit.startswith('%') else ' '}{unit}" if r["value"] is not None else ""
    st = r["status"]
    if st in ("PASS", "FAIL") and has_nums:
        key = st + "_NUM"
    elif st == "NEED MORE INFO" and not asks_text:
        key = "NEED_NOASK"
    else:
        key = st
    text = T.get(key) or en_block["templates"][key]
    text = text.format(thing=thing, limit=lim, value=val, asks=asks_text)
    text = text[0].upper() + text[1:]
    if r.get("safety"):
        text += " " + (T.get("SAFETY") or en_block["templates"]["SAFETY"])
    return text


def _ask(text):
    """A question ends with '?'; a plain label gets a full stop."""
    text = text.strip()
    return text if text.endswith("?") else text + "."


def add_to_report(ctx, report):
    langs = ctx.data.get("translations")
    if not langs:
        return
    en = langs["en"]
    for r in report["results"]:
        asks = " / ".join(_ask(SIMPLE.get(k) or label(k)) for k in r.get("asks", []))   # plain question names
        templated = sentence(en, en, r, asks)
        # If the full sentence is already easy to read, keep it: it says more than the short template.
        msg = r["message"]
        has_numbers = r["limit"] is not None and r["value"] is not None
        if r.get("plain"):                  # the rule wrote its own plain sentence (e.g. zone outside scope): keep it
            pass
        elif (msg and len(msg) <= 170 and grade_level(msg) <= 8
                and (r["status"] == "FLAG" or (r["status"] == "PASS" and not has_numbers))):
            r["plain"] = msg
        else:
            r["plain"] = templated
        r["plain_grade"] = grade_level(r["plain"])
        r["translated"] = {code: sentence(block, en, r, asks) for code, block in langs.items()
                           if code not in ("en",) and not code.startswith("_")}
