---
name: ic-memo-standard
description: Investment committee decision memo standard - memo structure, stage weighting tables for seed and growth funds, and the rules for surfacing specialist disagreement. Use whenever drafting, revising, scoring, or critiquing an investment decision memo, or when applying a weighting profile to specialist scores.
---

# IC Decision Memo Standard

## Weighting profiles

Different funds weight the same five lenses differently. Apply the profile named
in the request. Never invent a third profile.

| Lens | seed | growth |
| --- | ---: | ---: |
| Founder | 30% | 10% |
| Market | 30% | 20% |
| Product | 20% | 15% |
| Financial | 10% | 30% |
| Competitive | 10% | 25% |

**Risk is never weighted.** It is a gate, not a lens. If the Risk Specialist names
a blocker that no lens addressed, the recommendation cannot be INVEST.

### Applying the weighting

Each lens returns `SCORE: n/10`. Compute the weighted composite and show the
arithmetic in the memo:

`(Founder 7 x 0.30) + (Market 8 x 0.30) + (Product 7 x 0.20) + (Financial 3 x 0.10) + (Competitive 4 x 0.10) = 6.6 / 10`

Then state the composite's limits explicitly. A composite is a summary of five
opinions; it is not a decision, and it hides exactly the disagreement the
committee exists to argue about. Two rules follow:

- A high composite never overrides an unresolved tension or a Risk blocker.
- Never present the composite without the Tensions section on the same page.

Down-weight a lens's contribution when it reports `CONFIDENCE: low`, and say so.

## Memo structure

Use these sections, in this order, with these exact headings.

**Header line** - Company, `Research date: YYYY-MM-DD`, `Weighting profile: seed|growth`.
The date is mandatory. Funding rounds, pivots and shutdowns move fast enough that
an undated memo is misleading within a week.

`## Recommendation` - one of INVEST / PASS / REVISIT WITH CONDITIONS, plus one
sentence of reasoning. Lead with it. Never bury it.

`## Weighted score` - the table, the arithmetic, the composite, and its limits.

`## Tensions` - **mandatory.** Every material disagreement between two specialists.
Format each as:

> **Founder vs Risk - first-time founder.** Founder Specialist rates execution
> capability 8/10 citing domain depth. Risk Specialist flags no prior operating
> experience at this scale as a top-three failure mode. Unresolved.

Name both specialists. State both positions in their own terms. Mark each
Resolved / Unresolved. If you find no tensions, say so explicitly and justify it -
five independent lenses agreeing completely is itself a finding worth questioning.

`## The case for` - what we would have to believe for this to be a fund returner.

`## The case against` - what kills it, including every Risk Specialist finding.

`## Verification status` - list every claim carrying a
`[FOUNDER-PROVIDED - UNVERIFIED]` tag that materially affects the recommendation.
Founder and Product findings are largely founder-sourced; Market, Financial and
Competitive lean on third-party documents. Do not flatten that difference.

`## Conditions and next diligence` - what would move a PASS to an INVEST, or what
must be verified before wiring money.

## Prohibited

- Averaging the five opinions into a consensus narrative.
- Dropping, softening or adjudicating away a tension to make the memo read cleanly.
- Promoting a founder-provided claim to a verified fact.
- Any figure without a source document named.
