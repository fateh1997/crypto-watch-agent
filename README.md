# Crypto Watch Agent

**Question:** On any given day, which of BTC, ETH, or SOL is behaving most unlike its own recent self —
by volatility, trend against its 30-day average, or drawdown — and is that something worth flagging?

*(Starting draft — make this your own before it ships.)*

**Watchlist:** BTC, ETH, SOL (Kraken pairs TBD — confirm exact pair names in Kraken's docs, they don't
always match the ticker)

## How to run

<!-- TODO once agent.py exists: clone steps, venv/install, env vars needed (GROQ_API_KEY, SHEET_URL),
     exact commands for each mode (daily run, test mode, planner mode, etc.) -->

## What the AI does vs. what the code does

<!-- TODO: plain-words explanation. Core point to cover: the AI only recommends (picks tools, drafts
     the decision); your code runs every tool, validates every answer, and enforces every guardrail.
     The AI never executes a tool itself. -->

## Playbook thresholds

<!-- TODO: summarize playbook.md's thresholds here with their reason and source. Keep playbook.md as
     the source of truth; this section just makes it visible without opening another file. -->

## Hand check

<!-- TODO: pick one number the market tool returns, recompute it by hand in Google Sheets, report what
     you found (match or discrepancy, and why). -->

## Sample output

<!-- TODO: screenshot of a Sheet row with its sources, and of the alert email. -->

## Guardrails and tests

<!-- TODO: list the guardrails (valid JSON, allowed tools/coins only, no valid source -> no alert,
     short message required, advice-word filter) and how the tests prove each one. Include the
     red-run-then-green-run screenshots from the break-it/fix-it exercise. -->

## Results (Step 13)

<!-- TODO: table below, one row per version, filled in after running each 3x -->

| Version | Passes (run 1, run 2, run 3) | Calls per run | Ever failed to finish? |
|---|---|---|---|
| Agent loop | | | |
| Agent loop + reviewer | | | |
| Planner | | | |
| Planner + reviewer | | | |

**Conclusion:** <!-- TODO: which version runs daily, why, and what it costs. "The reviewer didn't help"
is a fine answer if that's what the numbers show. -->

---

This project is for education only and is not financial advice.
