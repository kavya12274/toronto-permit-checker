"""Step 18: by-law update tracker.

Shows on every report which version of the rules was used, and warns when:
  - the rules were checked a long time ago (more than stale_after_days),
  - there are known amendments not yet in the Rules Table,
  - rules haven't been ticked 'Verified vs PDF' in the workbook.
Version info lives in data/toronto/city.json and import_info.json (written by import_workbook.py).
Later idea: read the City's By-law Status Registry automatically and compare.
"""

from datetime import date


def _d(text):
    try:
        return date.fromisoformat(text)
    except (TypeError, ValueError):
        return None


def add_to_report(ctx, report, today=None):
    city = ctx.data.get("city", {})
    info = ctx.data.get("import_info", {})
    today = today or date.today()
    rules = ctx.data.get("rules", [])
    verified = sum(1 for r in rules if r.get("verified_vs_pdf"))

    summary = (f"Rules version: {city.get('bylaw', 'zoning by-law')} consolidation with city-wide amendments to "
               f"{city.get('consolidation_citywide_to', '?')} (site-specific to {city.get('consolidation_site_specific_to', '?')}); "
               f"{city.get('building_code', '')}. Rules checked {city.get('rules_checked_on', '?')}; imported from "
               f"'{info.get('workbook', 'the workbook')}' on {info.get('imported_on', '?')}.")
    warnings = []
    checked = _d(city.get("rules_checked_on"))
    if checked and (today - checked).days > city.get("stale_after_days", 180):
        warnings.append(f"The rules were last checked {(today - checked).days} days ago. Check for newer by-law amendments.")
    pending = [a for a in city.get("known_amendments", []) if not a.get("in_rules")]
    for a in pending:
        warnings.append(f"By-law {a['bylaw']} ({a['what']}) is not yet reflected in the rules. Results may be out of date.")
    if rules and verified == len(rules):
        summary += f" All {len(rules)} rules are ticked as checked against the by-law and Code PDFs."
    if verified < len(rules):
        warnings.append(f"{verified} of {len(rules)} rules are ticked 'Verified vs PDF' in the workbook. "
                        "Unverified numbers may be wrong.")
    warnings.append(f"Check the City's by-law status registry for anything newer: {city.get('status_registry', '')}")
    report["tracker"] = {"summary": summary, "warnings": warnings, "verified": verified, "rule_count": len(rules)}
