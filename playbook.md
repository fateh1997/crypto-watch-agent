<!--
Rules-only file — this repo is public. No keys, no personal data, no commentary that isn't a rule.
Each section starts with "## " (the search tool matches on these headers and their body words).
Write for the search: it matches literal words, not meaning — use the words your agent will actually
use when it cites a source (e.g. if your code calls it "volatility", don't only write "fluctuation"
here).
Every threshold below needs: a value, a reason, and a source (your own Assignment 1 analysis is a
valid source — cite it specifically, e.g. "30-day std dev of daily returns, computed in Assignment 1").
-->

## Volatility

Flag if 30-day volatility (sample std dev of daily returns) exceeds 4%.

Reason: BTC's observed 2.23% was labeled "typical" (not elevated) under
Assignment 1's own relative rule. 4% is a round cutoff well above that,
chosen as a starting estimate rather than derived from multiple coins or
days — there isn't enough historical data yet to set this precisely.
Revisit once the agent's own logged history (tool_get_history) has
accumulated a few weeks of real readings across BTC/ETH/SOL.

Source: Assignment 1 — BTC's 30-day volatility reading of 2.23% ("typical").
Cutoff itself is a provisional estimate, not Assignment-1-derived.

## Trend Against the Average

Flag if price deviates more than 5.0 percentage points above or below its
7-day moving average.

Reason: matches the "notably above/below" label from Assignment 1's own
trend analysis, and the 7-day window matches TREND_WINDOW in agent.py.

Source: Assignment 1 — 7-day moving average deviation rule.

## Drawdown

Flag if max drawdown over the last 30 days exceeds 15%.

Reason: BTC's observed 23.69% drawdown this period would clear this
cutoff, consistent with a near-quarter decline over a month being
genuinely notable rather than routine. Like the volatility cutoff, this
is a reasoned starting number, not one derived from comparing multiple
drawdown events.

Source: Assignment 1 — BTC's 30-day max drawdown reading of 23.69%.
Cutoff itself is a provisional estimate, not Assignment-1-derived.

## Alert Rules

Any single triggered threshold above (volatility, trend, or drawdown) is
enough to alert — it does not require two or more at once.

Reason: matches how the watch question itself is framed — "behaving most
unlike its own recent self — by volatility, trend against its 30-day
average, OR drawdown" lists three independent conditions, any one of
which answers the question "is that worth flagging?" Requiring two at
once would mean a single severe, isolated move (e.g. a sharp drawdown
with otherwise ordinary volatility) never gets flagged, which seems to
miss the point of a watch agent.

Source: this project's own watch question (README).

## Wording Rules

- Never name a single cause for a price move (a specific headline, a
  regulatory event, a macro factor) — most single-factor explanations for
  crypto price moves have weak or contested supporting evidence. Describe
  what the numbers show, not why they moved.
- Block any message containing an instruction to act on the asset: buy,
  sell, long, short, hold, invest, accumulate, exit, enter, "take profit",
  "stop loss", "go long", "go short". (Starting list — finalize and
  document the exact word list in README per the assignment's Step 6
  requirement; this is meant to be yours to own, not copied verbatim.)