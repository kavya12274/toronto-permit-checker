"""Talking to the AI (Anthropic's Claude), with a hard spending limit.

Every AI feature (plan reader, drawing reader, chatbot, vibes check) goes through
this file, so there is ONE place that checks the budget, sends the request and
records what it cost.

SETUP (once):
  1. pip3 install -r requirements.txt          (installs the "anthropic" library)
  2. Copy .env.example to .env and paste your API key after ANTHROPIC_API_KEY=
  3. Restart the app.

THE $5 LIMIT, two layers:
  - Layer 1 (the real guarantee): on console.anthropic.com, buy only $5 of credit
    and leave auto-reload OFF. Anthropic then can't charge you more than $5, whatever
    this code does.
  - Layer 2 (this file): every request's cost is worked out from the token counts
    Anthropic sends back and added up in data/ai_spending.json. Before each request,
    we work out the most it could possibly cost. If that would take the total over
    AI_BUDGET_USD (default 5.00), the request is NOT sent.

The key is read from .env and only ever used here, on your computer. It is never
sent to the web page, and .gitignore keeps .env out of GitHub.

ON THE PUBLIC SITE (the host sets HOST=0.0.0.0), two more limits so strangers can't use up the $5:
  - each visitor gets AI_VISITOR_DAILY AI requests a day (default 15)
  - the whole site stops AI for the day after AI_SITE_DAILY_USD of spending (default $0.50)
On the host, the key is a secret setting on the host's website (not a file), and the spending
record starts again whenever the free host restarts. That's why the $5-with-auto-reload-off
credit on console.anthropic.com is still the real guarantee.
"""

import json
import os
import threading
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ENV_FILE = os.path.join(ROOT, ".env")
LEDGER = os.path.join(ROOT, "data", "ai_spending.json")

# Prices in US dollars per million tokens (input, output), from Anthropic's price list
# (November 2026). Thinking tokens are billed as output. Haiku costs more when one
# request is over 100,000 input tokens (big drawing sets), so that price is here too.
PRICES = {
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
}
PRICES_LONG = {"claude-haiku-5-5": (0.50, 2.50)}
DEFAULT_MODEL = "claude-haiku-5-5"

# Rough token counts for files, used only for the "most it could cost" check (on the high side)
TOKENS_PER_IMAGE = 5000
TOKENS_PER_PDF_PAGE = 3500

_lock = threading.Lock()          # two browser tabs can't both slip past the budget check

PUBLIC = os.environ.get("HOST", "127.0.0.1") != "127.0.0.1"
_today = {"day": None, "visitors": {}, "spent": 0.0}     # the public site's limits for today (kept in memory)


class AIError(Exception):
    """A problem to show the user in plain words (no key, over budget, no internet...)."""


def load_env():
    """Read KEY=value lines from .env (no extra library needed). Real environment variables win."""
    values = {}
    if os.path.isfile(ENV_FILE):
        with open(ENV_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                values[k.strip()] = v.strip().strip('"').strip("'")
    for k in ("ANTHROPIC_API_KEY", "AI_MODEL", "AI_DRAWING_MODEL", "AI_BUDGET_USD", "AI_VISITOR_DAILY", "AI_SITE_DAILY_USD"):
        if os.environ.get(k):
            values[k] = os.environ[k]
    return values


def _model(name):
    return name if name in PRICES else DEFAULT_MODEL       # unknown price = can't keep the budget, so don't allow it


def settings():
    env = load_env()
    try:
        budget = float(env.get("AI_BUDGET_USD") or 5)
    except ValueError:
        budget = 5.0
    model = _model(env.get("AI_MODEL") or DEFAULT_MODEL)

    def number(name, default):
        try:
            return float(env.get(name) or default)
        except ValueError:
            return default
    return {"key": env.get("ANTHROPIC_API_KEY", ""), "model": model,
            "drawing_model": _model(env.get("AI_DRAWING_MODEL") or model), "budget": budget,
            "visitor_daily": int(number("AI_VISITOR_DAILY", 15)), "site_daily": number("AI_SITE_DAILY_USD", 0.50)}


# ---------- the public site's daily limits ----------

def _day():
    """Today's date in Toronto (a new day starts at midnight Toronto time)."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Toronto")).date().isoformat()
    except Exception:
        return datetime.utcnow().date().isoformat()


def _fresh_day():
    if _today["day"] != _day():
        _today.update(day=_day(), visitors={}, spent=0.0)


def limits_check(visitor):
    """Before an AI request on the public site: is this visitor (and the site) still under today's limits?
    Counts the request if so. Does nothing on your own computer."""
    if not PUBLIC:
        return
    s = settings()
    with _lock:
        _fresh_day()
        if _today["spent"] >= s["site_daily"]:
            raise AIError("The AI has reached its spending limit for today, so it's off until tomorrow. "
                          "Everything else in the checker still works.")
        used = _today["visitors"].get(visitor, 0)
        if used >= s["visitor_daily"]:
            raise AIError(f"You've used your {s['visitor_daily']} AI requests for today. They come back tomorrow. "
                          "Everything else in the checker still works.")
        _today["visitors"][visitor] = used + 1


def library_installed():
    try:
        import anthropic  # noqa: F401
        return True
    except ImportError:
        return False


# ---------- the spending record ----------

def _read_ledger():
    try:
        with open(LEDGER, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"total_usd": 0.0, "requests": []}


def spent():
    return round(_read_ledger()["total_usd"], 6)


def _record(feature, model, usage, cost):
    ledger = _read_ledger()
    ledger["total_usd"] = round(ledger["total_usd"] + cost, 6)
    ledger["requests"].append({"when": datetime.now().isoformat(timespec="seconds"), "feature": feature,
                               "model": model, "input_tokens": usage["input"], "output_tokens": usage["output"],
                               "cost_usd": round(cost, 6)})
    ledger["requests"] = ledger["requests"][-500:]          # keep the file small
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=1)
    return ledger["total_usd"]


def cost_of(model, input_tokens, output_tokens):
    pin, pout = PRICES_LONG[model] if input_tokens > 100_000 and model in PRICES_LONG else PRICES[model]
    return (input_tokens * pin + output_tokens * pout) / 1_000_000


def status(visitor=None):
    """What the web page shows: is the AI ready, and how much of the budget is left."""
    s = settings()
    used = spent()
    out = {"model": s["model"], "budget_usd": s["budget"], "spent_usd": round(used, 4),
           "left_usd": round(max(0.0, s["budget"] - used), 4)}
    if PUBLIC:
        with _lock:
            _fresh_day()
            mine = _today["visitors"].get(visitor, 0)
            site_spent = _today["spent"]
        out["visitor_left"] = max(0, s["visitor_daily"] - mine)
        if site_spent >= s["site_daily"]:
            return dict(out, enabled=False, message="The AI has reached its spending limit for today. The rest of the checker still works.")
        if mine >= s["visitor_daily"]:
            return dict(out, enabled=False, message=f"You've used your {s['visitor_daily']} AI requests for today. The rest of the checker still works.")
    if not library_installed():
        return dict(out, enabled=False, message="The AI library isn't installed. In Terminal: pip3 install -r requirements.txt")
    if not s["key"]:
        return dict(out, enabled=False, message="No API key yet. Put it in the .env file (see .env.example), then restart.")
    if used >= s["budget"]:
        return dict(out, enabled=False, message=f"The ${s['budget']:.2f} AI budget is used up. The rest of the checker still works.")
    return dict(out, enabled=True, message="AI is on.")


# ---------- sending ----------

def _client(client):
    if client is not None:
        return client
    s = settings()
    if not library_installed():
        raise AIError("The AI library isn't installed. In Terminal, run: pip3 install -r requirements.txt")
    if not s["key"]:
        raise AIError("The AI isn't set up yet: add your API key to the .env file, then restart the app.")
    import anthropic
    return anthropic.Anthropic(api_key=s["key"], max_retries=1, timeout=120)


def estimate_tokens(*parts):
    """A generous guess at input tokens: about 3 characters per token for text, and a fixed
    high number per image or PDF page. File data itself isn't counted as text."""
    total = 500

    def walk(x):
        nonlocal total
        if isinstance(x, str):
            total += len(x) // 3 + 1
        elif isinstance(x, dict):
            if x.get("type") == "image":
                total += TOKENS_PER_IMAGE
                return
            if x.get("type") == "document":
                total += TOKENS_PER_PDF_PAGE * int(x.get("_pages", 30))
                return
            for k, v in x.items():
                if not k.startswith("_"):
                    walk(v)
        elif isinstance(x, (list, tuple)):
            for v in x:
                walk(v)
        else:
            total += len(str(x)) // 3 + 1
    for p in parts:
        walk(p)
    return total


def _strip_private(x):
    """Remove our own '_pages' notes before sending (the API would reject unknown fields)."""
    if isinstance(x, dict):
        return {k: _strip_private(v) for k, v in x.items() if not k.startswith("_")}
    if isinstance(x, list):
        return [_strip_private(v) for v in x]
    return x


def _send(feature, client, model, request, worst_input, max_tokens):
    """Check the budget, send one request, record its real cost. Returns (response, cost, total)."""
    s = settings()
    worst = cost_of(model, worst_input, max_tokens)
    with _lock:
        used = spent()
        if used + worst > s["budget"]:
            raise AIError(f"Stopped to protect your budget: ${used:.2f} of ${s['budget']:.2f} is used, and this "
                          f"request could cost up to ${worst:.3f}. The checker itself still works without AI.")
        if PUBLIC:
            _fresh_day()
            if _today["spent"] + worst > s["site_daily"]:
                raise AIError("The AI has reached its spending limit for today, so it's off until tomorrow. "
                              "Everything else in the checker still works.")
        try:
            response = client.messages.create(model=model, max_tokens=max_tokens, **request)
        except AIError:
            raise
        except Exception as e:
            raise AIError(_explain(e)) from e
        usage = {"input": response.usage.input_tokens, "output": response.usage.output_tokens}
        cost = cost_of(model, usage["input"], usage["output"])
        total = _record(feature, model, usage, cost)
        if PUBLIC:
            _today["spent"] += cost
    return response, cost, total


def _info(cost, total, model):
    budget = settings()["budget"]
    return {"cost_usd": round(cost, 6), "spent_usd": round(total, 4), "budget_usd": budget,
            "left_usd": round(max(0.0, budget - total), 4), "model": model}


def _check_stop(response):
    if response.stop_reason == "refusal":
        raise AIError("The AI declined this request. Try different words.")
    if response.stop_reason == "max_tokens":
        raise AIError("That was too much for one AI request. Try something shorter or fewer pages.")


def ask_json(feature, system, user_content, schema, max_tokens=4000, client=None, model=None):
    """Send one request and get back JSON that matches `schema`.

    `user_content` is text, or a list of content blocks (text, images, PDFs).
    Returns (data, info) where info has the cost and the new total.
    `client` lets the tests pass in a pretend client, so tests never spend money.
    """
    client = _client(client)
    model = model or settings()["model"]
    worst_input = estimate_tokens(system, user_content, schema)
    request = {"system": system,
               "output_config": {"effort": "low",                       # reading jobs: keep thinking (and cost) low
                                 "format": {"type": "json_schema", "schema": schema}},
               "messages": [{"role": "user", "content": _strip_private(user_content)}]}
    response, cost, total = _send(feature, client, model, request, worst_input, max_tokens)
    info = _info(cost, total, model)
    _check_stop(response)
    text = next((b.text for b in response.content if b.type == "text"), "")
    try:
        return json.loads(text), info
    except ValueError:
        raise AIError("The AI's answer couldn't be read. Please try again.")


def ask_with_tools(feature, system, messages, tools, run_tool, max_tokens=2500, max_rounds=4, client=None):
    """A short conversation turn where the AI may call our tools (for the chatbot).

    run_tool(name, input) -> result (a dict) is OUR code, e.g. running the real checker.
    Each round goes through the budget check. Returns (reply_text, info, tool_calls).
    """
    client = _client(client)
    model = settings()["model"]
    messages = list(messages)
    calls, cost_turn, total = [], 0.0, spent()
    for _ in range(max_rounds):
        request = {"system": system, "tools": tools, "output_config": {"effort": "low"}, "messages": messages}
        response, cost, total = _send(feature, client, model, request, estimate_tokens(system, tools, messages), max_tokens)
        cost_turn += cost
        _check_stop(response)
        if response.stop_reason != "tool_use":
            text = "\n\n".join(b.text for b in response.content if b.type == "text").strip()
            return text, _info(cost_turn, total, model), calls
        messages.append({"role": "assistant", "content": response.content})     # keep every block, as the API needs
        results = []
        for b in response.content:
            if b.type != "tool_use":
                continue
            try:
                out = run_tool(b.name, b.input)
                results.append({"type": "tool_result", "tool_use_id": b.id, "content": json.dumps(out, default=str)})
            except Exception as e:                       # tell the AI the tool failed instead of crashing
                out = {"error": str(e)}
                results.append({"type": "tool_result", "tool_use_id": b.id, "content": str(e), "is_error": True})
            calls.append({"tool": b.name, "input": b.input, "result": out})
        messages.append({"role": "user", "content": results})
    return ("I couldn't finish that answer in one go. Try asking a narrower question.",
            _info(cost_turn, total, model), calls)


def _explain(e):
    """Turn a library error into a sentence a homeowner can act on."""
    try:
        import anthropic
    except ImportError:
        return str(e)
    if isinstance(e, anthropic.AuthenticationError):
        return "Your API key didn't work. Check the key in the .env file (it starts with sk-ant-), then restart."
    if isinstance(e, anthropic.PermissionDeniedError):
        return "Your API key isn't allowed to use this model. Check your Anthropic account."
    if isinstance(e, anthropic.RateLimitError):
        return "Too many AI requests at once. Wait a minute and try again."
    if isinstance(e, anthropic.BadRequestError):
        msg = str(getattr(e, "message", e))
        if "credit" in msg.lower():
            return "Your Anthropic account is out of credit (your $5 is used up)."
        return f"The AI couldn't take this request: {msg}"
    if isinstance(e, anthropic.APIConnectionError):
        return "Couldn't reach the AI. Check your internet connection."
    if isinstance(e, anthropic.APIStatusError):
        return f"The AI service had a problem (error {e.status_code}). Try again in a minute."
    return f"Something went wrong with the AI: {e}"
