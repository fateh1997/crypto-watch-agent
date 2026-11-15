#!/usr/bin/env python3
"""
Crypto Watch Agent - entrypoint.

Scaffold only: structure and signatures, no logic. Every TODO below is yours to write
(tools, guardrails, agent loop, reviewer, planner) - see claude/crypto-watch-agent-spec.md
in the AI Course project for the full build checklist and step numbers.

Usage (once implemented):
    python agent.py --mode daily
    python agent.py --mode daily --planner
    python agent.py --mode daily --reviewer
    python agent.py --mode daily --planner --reviewer
    python agent.py --mode test [same flags]
"""

import argparse
import json
import os
import re
import statistics
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import namedtuple
from pathlib import Path
from groq import Groq
WATCHLIST = ["BTC", "ETH", "SOL"]
KRAKEN_PAIRS = {"BTC": "XBTUSD", "ETH": "ETHUSD", "SOL": "SOLUSD"}  # Kraken's own symbols,
# ported from Assignment 1's fetch.py - don't guess these, Kraken uses its own names.

INTERVAL = 1440          # daily candles
VOLATILITY_WINDOW = 30
TREND_WINDOW = 7
DRAWDOWN_WINDOW = 30

MODEL = "..."            # YOUR CALL - check console.groq.com/docs/models, pick one
SYSTEM_PROMPT = """..."""   # YOUR CALL - the watch question, watchlist, tool-first
                             # instruction, and the exact final-JSON shape you want back


Candle = namedtuple("Candle", "time open high low close vwap volume count")

# ---------------------------------------------------------------------------
# Calculation helpers - ported directly from Assignment 1 (fetch.py / metrics.py),
# same method, same windows. Not AI-facing tools themselves; tool_market_summary
# below wraps them into the one tool the agent actually calls.
# ---------------------------------------------------------------------------

def _fetch_ohlc(pair, interval=INTERVAL):
    """Raises RuntimeError on any failure - never fabricates data."""
    url = f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval={interval}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read())
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Kraken fetch failed for {pair}: {e}") from e

    if data["error"]:
        raise RuntimeError(f"Kraken returned an error for {pair}: {data['error']}")

    # Kraken's result key isn't always the pair name we asked for (e.g. XBTUSD comes
    # back as XXBTZUSD) - read it dynamically, same as Assignment 1.
    result_key = next(k for k in data["result"] if k != "last")
    raw_candles = data["result"][result_key]
    candles = [
        Candle(time=row[0], open=float(row[1]), high=float(row[2]), low=float(row[3]),
               close=float(row[4]), vwap=float(row[5]), volume=float(row[6]), count=row[7])
        for row in raw_candles
    ]
    # Last candle is always today's, still-forming one (per Kraken's docs).
    return candles[:-1], candles[-1]


def _daily_returns(closes):
    return [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes))]


def _volatility(closes, window=VOLATILITY_WINDOW):
    """Sample standard deviation (n-1) of the last `window` days' returns."""
    recent_closes = closes[-(window + 1):]
    return statistics.stdev(_daily_returns(recent_closes))


def _moving_average(closes, window=TREND_WINDOW):
    return statistics.mean(closes[-window:])


def _trend_status(current_price, ma):
    deviation_pct = (current_price - ma) / ma * 100
    direction = "above" if current_price >= ma else "below"
    return direction, deviation_pct


def _max_drawdown(closes, window=DRAWDOWN_WINDOW):
    """Largest peak-to-trough decline, as a positive fraction, over the window."""
    recent = closes[-window:]
    peak = recent[0]
    worst = 0.0
    for price in recent:
        peak = max(peak, price)
        worst = max(worst, (peak - price) / peak)
    return worst


# ---------------------------------------------------------------------------
# Tools - each one the AI can request by name; your code is what actually runs it.
# ---------------------------------------------------------------------------

def tool_market_summary(coin: str) -> dict:
    """
    Step 3. Live Kraken summary for one watchlist coin: last close, trend vs its own
    moving average, volatility, max drawdown. A small summary only - never the raw
    candle history, the free AI tier's context is tight.
    """
    if coin not in WATCHLIST:
        raise ValueError(f"{coin!r} is not on the watchlist ({WATCHLIST}) - not fetching a guess")

    pair = KRAKEN_PAIRS[coin]
    complete, current = _fetch_ohlc(pair)
    closes = [c.close for c in complete]

    vol = _volatility(closes)
    ma = _moving_average(closes)
    direction, deviation_pct = _trend_status(current.close, ma)
    dd = _max_drawdown(closes)

    return {
        "coin": coin,
        "last_close": current.close,
        "trend": {
            "direction": direction,              # "above" or "below" its own moving average
            "deviation_pct": round(deviation_pct, 2),
            "ma_window_days": TREND_WINDOW,
        },
        "volatility_30d": round(vol, 4),          # sample stdev of daily returns
        "max_drawdown_30d": round(dd, 4),         # positive fraction, e.g. 0.12 = -12%
    }


def tool_get_history() -> list:
    """
    Step 4. Recent past decisions from the Agent tab, via the Apps Script Web App, so
    the agent can tell if it already alerted on something.

    Contract with Code.gs's doGet (still a TODO there - implement it to match this):
    GET {SHEET_URL}?key=...&action=history -> JSON array of past decision rows,
    most recent last.
    """
    sheet_url = os.environ["SHEET_URL"]
    key = os.environ["AGENT_KEY"]
    url = f"{sheet_url}?key={urllib.parse.quote(key)}&action=history"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return json.loads(resp.read())
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Could not read history: {e}") from e


def tool_save_decision(decision: dict) -> None:
    """
    Step 4 / Step 8. Post the final decision to the Apps Script Web App.

    Contract with Code.gs's doPost (still a TODO there - implement it to match this):
    POST body {"key": ..., **decision} as JSON -> script appends an Agent-tab row and
    sends the email if decision["alert"] is true.
    """
    sheet_url = os.environ["SHEET_URL"]
    key = os.environ["AGENT_KEY"]
    body = json.dumps({"key": key, **decision}).encode("utf-8")
    req = urllib.request.Request(
        sheet_url, data=body, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()
    except (urllib.error.URLError, OSError) as e:
        raise RuntimeError(f"Could not save decision: {e}") from e


def load_playbook(path: str = "playbook.md") -> list:
    """
    Step 5. Parse playbook.md into [{"title": ..., "body": ...}, ...], split on lines
    starting with "## ".
    """
    text = Path(path).read_text(encoding="utf-8")
    sections = []
    title, body_lines = None, []
    for line in text.splitlines():
        if line.startswith("## "):
            if title is not None:
                sections.append({"title": title, "body": "\n".join(body_lines).strip()})
            title, body_lines = line[3:].strip(), []
        elif title is not None:
            body_lines.append(line)
    if title is not None:
        sections.append({"title": title, "body": "\n".join(body_lines).strip()})
    return sections


_STOPWORDS = {"the", "a", "an", "is", "of", "to", "and", "or", "in", "on", "for",
              "its", "this", "that", "be", "it", "as", "at", "by"}


def _words(text):
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOPWORDS]


def tool_search_playbook(query: str) -> list:
    """
    Step 5. Word-overlap search (not semantic) over load_playbook()'s sections: scores
    each section by words shared with `query`, returns titles with score > 0, best
    first. `sources` in the agent's final answer must be real section titles, so this
    is what makes that possible - write playbook.md using the words your prompts and
    tools actually use, or a real match will score 0 and get missed.
    """
    sections = load_playbook()
    query_words = set(_words(query))
    scored = []
    for s in sections:
        section_words = set(_words(s["title"] + " " + s["body"]))
        score = len(query_words & section_words)
        if score > 0:
            scored.append((score, s["title"]))
    scored.sort(reverse=True)
    return [title for _, title in scored]


# Tool registry the agent loop picks from. Keep descriptions short and specific - the
# AI chooses tools from these descriptions alone.
TOOLS = {
    "market_summary": {
        "fn": tool_market_summary,
        "description": "Get a small market summary (last close, % from 30-day average, "
                        "volatility, max drawdown) for one coin on the watchlist.",
    },
    "get_history": {
        "fn": tool_get_history,
        "description": "Get the agent's recent past decisions, to avoid repeating an alert.",
    },
    "search_playbook": {
        "fn": tool_search_playbook,
        "description": "Search the playbook for the sections most relevant to a query.",
    },
}

def _tool_schemas():
    return [
        {"type": "function", "function": {
            "name": "market_summary",
            "description": TOOLS["market_summary"]["description"],
            "parameters": {
                "type": "object",
                "properties": {"coin": {"type": "string", "enum": WATCHLIST}},
                "required": ["coin"],
            },
        }},
        {"type": "function", "function": {
            "name": "get_history",
            "description": TOOLS["get_history"]["description"],
            "parameters": {"type": "object", "properties": {}},
        }},
        {"type": "function", "function": {
            "name": "search_playbook",
            "description": TOOLS["search_playbook"]["description"],
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        }},
    ]

# ---------------------------------------------------------------------------
# Guardrails - run in code, after the AI answers. The AI cannot talk its way past these.
# ---------------------------------------------------------------------------

def validate_decision_json(raw_response: str) -> dict:
    """
    TODO (Step 7): parse `raw_response` as JSON, confirm it has the required keys
    (alert decision, message, sources, plus whatever else you design in). If invalid,
    the caller should re-ask the AI rather than proceed.
    """
    raise NotImplementedError("TODO: implement JSON/shape guardrail (Step 7)")


def check_source(decision: dict, playbook_sections: list) -> bool:
    """
    TODO (Step 7): every entry in decision["sources"] must be a real playbook section
    title. No valid source -> no alert.
    """
    raise NotImplementedError("TODO: implement source guardrail (Step 7)")


def check_advice_language(message: str) -> bool:
    """
    TODO (Step 7): return False (block) if `message` contains buy/sell/long/short/etc.
    Pick your own banned-word list and explain the choice in the README.
    """
    raise NotImplementedError("TODO: implement advice-language guardrail (Step 7)")


# ---------------------------------------------------------------------------
# Agent loop (plain) and planner (Part B) - the AI requests tools, your code runs them.
# ---------------------------------------------------------------------------

def run_agent_loop(step_limit: int = 8) -> dict:
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "..."},   # YOUR CALL - the actual ask
    ]
    for step in range(step_limit):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=_tool_schemas(),
            tool_choice="auto",
        )
        msg = response.choices[0].message
        if msg.tool_calls:
            messages.append(msg)
            for call in msg.tool_calls:
                name = call.function.name
                args = json.loads(call.function.arguments)
                print(f"[step {step}] tool call: {name}({args})")  # YOUR CALL - real log format
                try:
                    result = TOOLS[name]["fn"](**args)
                except Exception as e:
                    result = {"error": str(e)}
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result),
                })
            continue
        # No tool call -> this is meant to be the final answer. Only a bare parse
        # here; full shape/required-key checking is Step 7's job (validate_decision_json),
        # called separately after this function returns.
        try:
            return json.loads(msg.content)
        except json.JSONDecodeError:
            messages.append({"role": "user",
                              "content": "That wasn't valid JSON. Reply with only the final JSON decision."})
            continue
    raise RuntimeError(f"Agent did not produce a final answer within {step_limit} steps")

def make_plan() -> list:
    """
    TODO (Step 11): ask the AI for a JSON plan - a list of
    {"tool": ..., "args": ..., "reason": ...} steps - before anything runs.
    """
    raise NotImplementedError("TODO: implement planner (Step 11)")


def validate_plan(plan: list) -> bool:
    """
    TODO (Step 11): only allowed tools, only watchlist coins, a sane max step count,
    arguments in the right shape. Bad plan -> caller retries once, then stops.
    """
    raise NotImplementedError("TODO: implement plan guardrail (Step 11)")


def execute_plan(plan: list) -> list:
    """
    TODO (Step 11): your code runs every validated step itself. The AI never runs a
    tool directly. Return the collected evidence for the AI to decide from.
    """
    raise NotImplementedError("TODO: implement plan executor (Step 11)")


# ---------------------------------------------------------------------------
# Reviewer (Part B) - second pass over evidence + draft, before the guardrails run.
# ---------------------------------------------------------------------------

def review_draft(draft: dict, evidence: dict, history: list, revise_limit: int = 1) -> dict:
    """
    TODO (Step 10): check every number in the draft's reasoning appears in `evidence`,
    any alert follows a real playbook rule, the draft doesn't repeat an alert already in
    `history`, and nothing reads as advice. On a problem, let the agent revise once
    (respect revise_limit). A broken/unparseable reviewer reply must never block the
    job - fall through to the draft as-is and let the guardrails below catch it.
    """
    raise NotImplementedError("TODO: implement reviewer (Step 10)")


# ---------------------------------------------------------------------------
# Test mode (Step 9) - fake market data, fake tools, no live Kraken/Sheet calls.
# ---------------------------------------------------------------------------

def run_tests() -> bool:
    """
    TODO (Step 9): run at least 6 scenarios against fake data/fake tools:
      1. calm market -> no alert
      2. volatility spike -> alert, cites a real playbook section
      3. same spike, already alerted yesterday per fake history -> no alert
      4. Kraken/tool failure -> no alert, no invented numbers
      5. advice trap (data that tempts a buy/sell-worded alert) -> blocked
      6. one scenario of your own
    A failing scenario must make this return False / raise, so the GitHub Actions run
    goes red. Print enough to the log that a green run clearly ran real scenarios, not
    nothing.
    """
    raise NotImplementedError("TODO: implement test scenarios (Step 9)")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Crypto Watch Agent")
    parser.add_argument("--mode", choices=["daily", "test"], required=True)
    parser.add_argument("--planner", action="store_true",
                         help="use the planner instead of the plain agent loop")
    parser.add_argument("--reviewer", action="store_true", help="turn the reviewer pass on")
    args = parser.parse_args()

    if args.mode == "test":
        ok = run_tests()
        return 0 if ok else 1

    # args.mode == "daily"
    # TODO (Step 12): wire this up once run_agent_loop / make_plan / execute_plan /
    # review_draft exist - roughly:
    #   if args.planner:
    #       plan = make_plan()
    #       if not validate_plan(plan):
    #           ... retry once, then exit with an error if the retry is also bad ...
    #       evidence = execute_plan(plan)
    #   else:
    #       evidence = run_agent_loop()
    #   draft = ...decide from evidence, via the AI...
    #   if args.reviewer:
    #       draft = review_draft(draft, evidence, tool_get_history())
    #   decision = validate_decision_json(...)       # guardrail
    #   ...check_source(...), check_advice_language(...)...  # guardrails
    #   tool_save_decision(decision)
    raise NotImplementedError("TODO: wire up daily mode (Step 12)")


if __name__ == "__main__":
    sys.exit(main())
