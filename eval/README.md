# Eval harness

Grades a produced IC decision memo against the **ic-memo-standard** skill.
The swarm is non-deterministic; this harness is how you tell a good run from a
bad one without reading every memo by hand.

## What it checks

Two layers, run against `outputs/ic-decision.md` (or any memo you pass):

### 1. Deterministic checks (no API, fast, the CI gate)
- **Structure** — all seven required sections present, in the standard's exact headings.
- **Header** — dated (`Research date: YYYY-MM-DD`) and names the weighting profile.
- **Recommendation** — is one of `INVEST` / `PASS` / `REVISIT WITH CONDITIONS`, and leads its section.
- **Weighted score** — all five lenses in the table; weights match the profile
  (`seed`/`growth`); per-lens `score × weight = contribution`; composite = sum
  of contributions; the composite's limits are discussed.
- **Tensions** — at least one documented (or "none" explicitly justified); each
  marked Resolved/Unresolved and names two specialists (`X vs Y`).
- **Verification** — `[FOUNDER-PROVIDED - UNVERIFIED]` tags exist and the
  Verification section enumerates the material ones.
- **Sources** — figures in "case against" carry a tag or named source (warn).
- **Risk gate** — no `INVEST` when an unaddressed Risk blocker exists. *(the
  standard's hardest rule; a violation fails the run.)*

### 2. LLM-judge checks (`--judge`, needs `ANTHROPIC_API_KEY`)
The qualitative rules a linter cannot see, graded by an Opus judge that returns JSON:
- No consensus averaging.
- Tensions are genuinely opposed, not strawmen adjudicated away.
- No founder claim silently promoted to fact.
- Risk is treated as a gate.

## Usage

```bash
python eval/eval_memo.py                          # deterministic only
python eval/eval_memo.py --judge                  # + LLM judge
python eval/eval_memo.py --profile growth         # check the growth weight table
python eval/eval_memo.py outputs/ic-decision.md   # explicit path
python eval/eval_memo.py --json                   # machine-readable report
```

Exit code is `0` on pass, `1` if any `fail`-severity check (or the judge) fails,
`2` if the memo file is missing — so it drops straight into CI:

```bash
python run_deal_desk.py && python eval/eval_memo.py --judge
```

## Notes

- The weight tables in `eval_memo.py` (`WEIGHTS`) mirror `skills/ic-memo-standard/SKILL.md`.
  If the skill's tables change, update both.
- `WARN`-severity checks (source heuristics, header profile) surface signal
  without gating the build; only `FAIL` checks affect the exit code.
