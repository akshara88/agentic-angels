---
name: market-sizing
description: Market sizing discipline for venture diligence - bottom-up TAM/SAM/SOM construction, rejecting unsupported top-down analyst figures, and assessing market timing. Use whenever evaluating a startup's market size claim, building a TAM estimate, or judging whether a market is large enough and timed correctly.
---

# Market Sizing

## Rule one: rebuild the number yourself

A founder's TAM figure is a marketing artifact. Treat it as a claim to be tested,
never as an input. Report both numbers and the gap between them:

> Deck claims $40B TAM. Bottom-up construction from the market report gives
> $2.1B SAM for the US segment they actually sell to. The gap is 19x and it is
> the single most important thing in this assessment.

A large gap is not automatically disqualifying. A company can win a $2B market.
It is disqualifying to *not notice* the gap, because everything downstream -
the round size, the ownership target, the exit maths - was priced off the wrong
number.

## Bottom-up construction

Always: **units x price x attach rate**, with each factor sourced to a named
document.

```
addressable buying units (from market report)
  x realistic annual contract value (from pricing in the deck or comparables)
  x share of those units that can actually buy today
  = SAM
```

Then SOM: the slice reachable in 3 years given this team's go-to-market motion
and this competitive field. If SOM requires share the Competitive Specialist's
landscape says is unavailable, say so - that disagreement belongs in the memo.

**Reject as unusable:**
- Top-down analyst totals with no derivation ("the global healthcare AI market
  will reach $X by 2030").
- TAM built on the total spend of an adjacent category the company does not sell
  into.
- Any figure whose source document you cannot name.

State plainly when a deck's number is unusable rather than adjusting it silently.

## Timing

Size is necessary, not sufficient. Assess:

- **Growth rate and its driver.** A CAGR with no named mechanism is decoration.
  Regulatory change, reimbursement change, and cost pressure are mechanisms.
- **Why now.** What changed in the last 24 months that makes this buildable or
  buyable now? If nothing did, the market may be large and permanently stuck.
- **Budget location.** Whose line item does this come out of, and does that
  budget exist today? New-budget sales cycles are materially slower than
  replacement sales.

## Scoring

Score the market the company can realistically serve, not the market it names.

| Score | Means |
| --- | --- |
| 9-10 | Large verified SAM, mechanism-backed growth, clear existing budget |
| 7-8 | Solid SAM, credible timing, one soft assumption |
| 5-6 | Adequate SAM but timing or budget location is unproven |
| 3-4 | SAM materially smaller than claimed, or no why-now |
| 1-2 | Market does not support a venture outcome at this entry price |

## Output

Max 300 words, one message, no web search. Use only the documents provided.
Always report the deck's claimed figure, your bottom-up figure, and the ratio.
Close with exactly:

```
SCORE: n/10
CONFIDENCE: high|medium|low
TOP RISK: <one line>
```
