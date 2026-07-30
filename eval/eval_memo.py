"""
Eval harness for the Investment Committee swarm.

Grades a produced memo (outputs/ic-decision.md by default) against the
ic-memo-standard. Two layers:

  1. Deterministic checks — structure, header, weighting arithmetic, tension
     format, verification tags, and the Risk-blocker gate. No API calls, fast,
     and the backbone of the score.
  2. LLM-judge checks (optional, --judge) — the qualitative rules the standard
     cares about most and a linter cannot see: did the Chair average the lenses
     into consensus, are the tensions genuine and unresolved-where-they-should-be,
     is any founder claim silently promoted to fact.

Exit code is non-zero if any check with severity "fail" does not pass, so this
doubles as a CI gate.

Usage:
    python eval/eval_memo.py                          # deterministic only
    python eval/eval_memo.py --judge                  # + LLM judge (needs API key)
    python eval/eval_memo.py outputs/ic-decision.md   # explicit path
    python eval/eval_memo.py --profile growth         # check growth weight table
    python eval/eval_memo.py --json                    # machine-readable report
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path


# Weight tables from ic-memo-standard. If the skill changes, change these too.
WEIGHTS = {
    "seed":   {"founder": 0.30, "market": 0.30, "product": 0.20, "financial": 0.10, "competitive": 0.10},
    "growth": {"founder": 0.10, "market": 0.20, "product": 0.15, "financial": 0.30, "competitive": 0.25},
}

REQUIRED_SECTIONS = [
    "## Recommendation",
    "## Weighted score",
    "## Tensions",
    "## The case for",
    "## The case against",
    "## Verification status",
    "## Conditions and next diligence",
]

VALID_RECOMMENDATIONS = ("INVEST", "PASS", "REVISIT WITH CONDITIONS")

# Tolerance for the composite arithmetic check.
COMPOSITE_TOL = 0.05


@dataclass
class Check:
    name: str
    passed: bool
    severity: str          # "fail" (gates exit code) | "warn"
    detail: str = ""


@dataclass
class Report:
    memo_path: str
    profile: str
    checks: list = field(default_factory=list)

    @property
    def failed(self):
        return [c for c in self.checks if not c.passed and c.severity == "fail"]

    @property
    def warned(self):
        return [c for c in self.checks if not c.passed and c.severity == "warn"]

    def add(self, name, passed, severity="fail", detail=""):
        self.checks.append(Check(name, passed, severity, detail))


# ---------------------------------------------------------------------------
# Deterministic checks
# ---------------------------------------------------------------------------

def check_structure(memo: str, r: Report) -> None:
    for section in REQUIRED_SECTIONS:
        present = re.search(rf"^{re.escape(section)}\s*$", memo, re.MULTILINE) is not None
        r.add(f"section present: {section}", present,
              detail="" if present else "heading missing or misspelled")


def check_header(memo: str, r: Report, profile: str) -> None:
    head = memo.split("##", 1)[0]  # everything before the first section
    # Allow markdown emphasis/punctuation between "date" and the value
    # (e.g. "**Research date:** 2026-07-30").
    has_date = re.search(r"[Rr]esearch date[:*\s]+\d{4}-\d{2}-\d{2}", head) is not None
    r.add("header: research date present (YYYY-MM-DD)", has_date,
          detail="" if has_date else "standard requires a dated header")

    has_profile = re.search(rf"[Ww]eighting profile[:*\s]+.*{profile}", head) is not None
    r.add(f"header: weighting profile states '{profile}'", has_profile, severity="warn",
          detail="" if has_profile else f"expected profile '{profile}' in header")


def _recommendation_body(memo: str) -> str:
    m = re.search(r"^## Recommendation\s*$(.*?)(?=^## )", memo, re.MULTILINE | re.DOTALL)
    return m.group(1) if m else ""


def _verdict_token(rec_body: str):
    """The memo's actual verdict.

    A memo may mention several verdict words in prose ("INVEST is not
    defensible..."), so prefer the bolded verdict and always match the longest
    phrase first so "REVISIT WITH CONDITIONS" wins over a bare "INVEST".
    """
    ordered = sorted(VALID_RECOMMENDATIONS, key=len, reverse=True)
    # 1. Prefer a bolded verdict (**REVISIT WITH CONDITIONS.**).
    for rec in ordered:
        if re.search(rf"\*\*\s*{re.escape(rec)}", rec_body):
            return rec
    # 2. Fall back to first-line prose.
    first_line = next((ln for ln in rec_body.strip().splitlines() if ln.strip()), "")
    for rec in ordered:
        if rec in first_line:
            return rec
    # 3. Anywhere in the section.
    for rec in ordered:
        if rec in rec_body:
            return rec
    return None


def check_recommendation(memo: str, r: Report) -> None:
    body = _recommendation_body(memo)
    verdict = _verdict_token(body)
    r.add("recommendation is one of INVEST/PASS/REVISIT WITH CONDITIONS",
          verdict is not None,
          detail=f"verdict: {verdict or 'none'}")
    # Recommendation should lead — appear in the first ~2 non-empty lines of the section.
    lead_lines = [ln for ln in body.strip().splitlines() if ln.strip()][:2]
    leads = any(rec in " ".join(lead_lines) for rec in VALID_RECOMMENDATIONS)
    r.add("recommendation leads its section", leads, severity="warn",
          detail="" if leads else "verdict should not be buried")


def _parse_score_table(memo: str):
    """Extract {lens: (score, weight_pct, contribution)} from the Weighted score table."""
    m = re.search(r"^## Weighted score\s*$(.*?)(?=^## )", memo, re.MULTILINE | re.DOTALL)
    if not m:
        return {}, None
    section = m.group(1)
    rows = {}
    # Rows look like: | Founder | 6/10 | 30% | 1.80 | ... |
    for line in section.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        lens = cells[0].lower()
        if lens not in WEIGHTS["seed"]:
            continue
        score_m = re.search(r"(\d+(?:\.\d+)?)\s*/\s*10", cells[1])
        weight_m = re.search(r"(\d+(?:\.\d+)?)\s*%", cells[2])
        contrib_m = re.search(r"(\d+(?:\.\d+)?)", cells[3])
        if not (score_m and weight_m and contrib_m):
            continue
        rows[lens] = (float(score_m.group(1)), float(weight_m.group(1)),
                      float(contrib_m.group(1)))
    # Composite: last "= N / 10" or "**N / 10**" in the section
    comp_m = re.findall(r"(\d+\.\d+)\s*/\s*10", section)
    composite = float(comp_m[-1]) if comp_m else None
    return rows, composite


def check_weighting(memo: str, r: Report, profile: str) -> None:
    rows, composite = _parse_score_table(memo)
    expected = WEIGHTS[profile]

    all_lenses = all(lens in rows for lens in expected)
    r.add("weighted score: all five lenses present in table", all_lenses,
          detail="" if all_lenses else f"present: {sorted(rows)}")

    # Weights match the profile.
    if all_lenses:
        weight_ok = all(abs(rows[l][1] / 100 - w) < 1e-6 for l, w in expected.items())
        r.add(f"weighted score: weights match '{profile}' profile", weight_ok,
              detail="" if weight_ok else
              "weights: " + ", ".join(f"{l}={rows[l][1]}%" for l in expected))

        # Per-lens contribution arithmetic: score * weight == contribution.
        bad = []
        for lens, (score, wpct, contrib) in rows.items():
            if abs(score * (wpct / 100) - contrib) > COMPOSITE_TOL:
                bad.append(f"{lens}: {score}×{wpct}%={score*wpct/100:.2f} but table says {contrib}")
        r.add("weighted score: per-lens contribution arithmetic correct", not bad,
              detail="; ".join(bad))

        # Composite == sum of contributions.
        if composite is not None:
            expected_composite = sum(rows[l][0] * expected[l] for l in expected)
            comp_ok = abs(expected_composite - composite) < COMPOSITE_TOL
            r.add("weighted score: composite equals sum of contributions", comp_ok,
                  detail="" if comp_ok else
                  f"stated {composite}, computed {expected_composite:.2f}")
        else:
            r.add("weighted score: composite figure present", False,
                  detail="no 'N.NN / 10' composite found")

    # The standard: composite must not appear without Tensions on the same page —
    # proxy: Tensions section is non-trivial.
    tm = re.search(r"^## Tensions\s*$(.*?)(?=^## )", memo, re.MULTILINE | re.DOTALL)
    tensions_body = tm.group(1).strip() if tm else ""
    r.add("weighted score: 'limits of the composite' discussed",
          "limit" in memo.lower().split("## tensions")[0].split("## weighted score")[-1],
          severity="warn",
          detail="standard requires stating the composite's limits")


def check_tensions(memo: str, r: Report) -> None:
    m = re.search(r"^## Tensions\s*$(.*?)(?=^## )", memo, re.MULTILINE | re.DOTALL)
    body = m.group(1).strip() if m else ""
    # Each tension is a blockquote. Standard says name both specialists + mark resolved/unresolved.
    quotes = re.findall(r"^>.*(?:\n>.*)*", body, re.MULTILINE)
    r.add("tensions: at least one tension documented (or explicit 'none' justified)",
          bool(quotes) or "no tension" in body.lower(),
          detail=f"{len(quotes)} tension block(s) found")

    if quotes:
        marked = sum(1 for q in quotes
                     if re.search(r"resolved|unresolved", q, re.IGNORECASE))
        r.add("tensions: every tension marked Resolved/Unresolved",
              marked == len(quotes),
              detail=f"{marked}/{len(quotes)} marked")
        # "X vs Y" naming of two specialists.
        named = sum(1 for q in quotes if re.search(r"\bvs\b", q, re.IGNORECASE))
        r.add("tensions: each names two specialists (X vs Y)",
              named == len(quotes), severity="warn",
              detail=f"{named}/{len(quotes)} use 'X vs Y' form")


def check_verification(memo: str, r: Report) -> None:
    has_section = "## Verification status" in memo
    tag_count = len(re.findall(r"\[FOUNDER-PROVIDED\s*-\s*UNVERIFIED\]", memo))
    r.add("verification: [FOUNDER-PROVIDED - UNVERIFIED] tags present",
          tag_count > 0,
          detail=f"{tag_count} tag(s) found")
    # The section should enumerate the material unverified claims.
    m = re.search(r"^## Verification status\s*$(.*?)(?=^## )", memo, re.MULTILINE | re.DOTALL)
    body = m.group(1) if m else ""
    listed = len(re.findall(r"\[FOUNDER-PROVIDED\s*-\s*UNVERIFIED\]", body))
    r.add("verification: section lists material unverified claims",
          has_section and listed > 0,
          detail=f"{listed} tagged claim(s) inside the section")


def check_sources(memo: str, r: Report) -> None:
    """Prohibited: any figure without a source. Heuristic — warn only."""
    # Dollar/percent figures should co-occur with a tag or a named source nearby.
    # This is a soft signal, so it's a warning, not a gate.
    case_against = re.search(r"^## The case against\s*$(.*?)(?=^## )",
                             memo, re.MULTILINE | re.DOTALL)
    body = case_against.group(1) if case_against else ""
    bullets = [b for b in body.splitlines() if b.strip().startswith("-")]
    unsourced = [b for b in bullets
                 if re.search(r"\$\d|\d+%", b)
                 and not re.search(r"\[|benchmark|report|Financial|Market|Competitive|Founder|Product|Risk",
                                   b, re.IGNORECASE)]
    r.add("sources: figures in 'case against' carry a source/tag", not unsourced,
          severity="warn",
          detail="unsourced-looking: " + " || ".join(b.strip()[:70] for b in unsourced[:3]))


def check_risk_gate(memo: str, r: Report) -> None:
    """If a Risk blocker exists that no lens addressed, recommendation != INVEST."""
    rec_token = _verdict_token(_recommendation_body(memo))

    blocker_mentioned = bool(re.search(r"BLOCKER|blocker", memo))
    unaddressed = bool(re.search(r"no lens (addressed|assessed|cleared)|unaddressed by any lens",
                                 memo, re.IGNORECASE))
    gate_violated = (rec_token == "INVEST") and blocker_mentioned and unaddressed
    r.add("risk gate: no INVEST when an unaddressed Risk blocker exists",
          not gate_violated,
          detail="" if not gate_violated else
          "memo recommends INVEST despite an unaddressed Risk blocker")


def run_deterministic(memo: str, profile: str, path: str) -> Report:
    r = Report(memo_path=path, profile=profile)
    check_structure(memo, r)
    check_header(memo, r, profile)
    check_recommendation(memo, r)
    check_weighting(memo, r, profile)
    check_tensions(memo, r)
    check_verification(memo, r)
    check_sources(memo, r)
    check_risk_gate(memo, r)
    return r


# ---------------------------------------------------------------------------
# LLM-judge checks (optional)
# ---------------------------------------------------------------------------

JUDGE_SYSTEM = """\
You are an evaluator grading an investment-committee decision memo against a
fixed standard. You are strict and literal. You return ONLY JSON.

The standard's non-negotiable qualitative rules:
1. NO CONSENSUS AVERAGING — the memo must NOT smooth five specialist opinions
   into one agreeable narrative. Disagreement is the product.
2. TENSIONS ARE REAL AND UNRESOLVED WHERE THEY SHOULD BE — each tension in the
   '## Tensions' section must state two genuinely opposed positions, not a
   strawman that is then adjudicated away.
3. NO SILENT PROMOTION — a claim tagged [FOUNDER-PROVIDED - UNVERIFIED] must
   never be treated elsewhere in the memo as an established fact.
4. RISK IS A GATE — if the Risk Specialist named a blocker no lens addressed,
   the recommendation cannot be INVEST.

For each rule return: {"rule": "<short id>", "pass": true|false,
"evidence": "<one quote or line ref>", "reason": "<one sentence>"}.
Return a JSON object: {"verdict": "PASS"|"FAIL", "checks": [ ... ]}.
verdict is FAIL if any rule fails."""


def run_judge(memo: str) -> dict:
    try:
        from anthropic import Anthropic
    except ImportError:
        return {"error": "anthropic not installed"}
    import os
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return {"error": "ANTHROPIC_API_KEY not set — skipping judge"}

    client = Anthropic()
    msg = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=2000,
        system=JUDGE_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"Grade this memo. Return only the JSON.\n\n<memo>\n{memo}\n</memo>",
        }],
    )
    text = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")
    # Pull the first JSON object out of the reply.
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return {"error": "judge did not return JSON", "raw": text[:500]}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError as e:
        return {"error": f"judge JSON parse failed: {e}", "raw": text[:500]}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def render_human(report: Report, judge: dict | None) -> str:
    lines = []
    lines.append(f"\n  Memo:    {report.memo_path}")
    lines.append(f"  Profile: {report.profile}")
    lines.append("\n  Deterministic checks")
    lines.append("  " + "-" * 60)
    for c in report.checks:
        mark = "PASS" if c.passed else ("FAIL" if c.severity == "fail" else "WARN")
        line = f"  [{mark}] {c.name}"
        if not c.passed and c.detail:
            line += f"\n         → {c.detail}"
        lines.append(line)

    if judge is not None:
        lines.append("\n  LLM-judge checks")
        lines.append("  " + "-" * 60)
        if "error" in judge:
            lines.append(f"  (judge skipped: {judge['error']})")
        else:
            for c in judge.get("checks", []):
                mark = "PASS" if c.get("pass") else "FAIL"
                lines.append(f"  [{mark}] {c.get('rule')}: {c.get('reason', '')}")
            lines.append(f"  judge verdict: {judge.get('verdict')}")

    n_fail = len(report.failed)
    n_warn = len(report.warned)
    judge_failed = bool(judge and judge.get("verdict") == "FAIL")
    lines.append("\n  " + "=" * 60)
    status = "PASS" if (n_fail == 0 and not judge_failed) else "FAIL"
    lines.append(f"  RESULT: {status}   ({n_fail} failed, {n_warn} warnings)")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Eval an IC decision memo against ic-memo-standard.")
    ap.add_argument("memo", nargs="?", default="outputs/ic-decision.md",
                    help="path to the memo markdown (default: outputs/ic-decision.md)")
    ap.add_argument("--profile", default="seed", choices=list(WEIGHTS),
                    help="weighting profile to check against (default: seed)")
    ap.add_argument("--judge", action="store_true",
                    help="also run the LLM-judge layer (needs ANTHROPIC_API_KEY)")
    ap.add_argument("--json", action="store_true", help="emit a JSON report")
    args = ap.parse_args()

    path = Path(args.memo)
    if not path.exists():
        print(f"ERROR: memo not found: {path}", file=sys.stderr)
        print("Run `python run_deal_desk.py` first, or pass a memo path.", file=sys.stderr)
        return 2

    memo = path.read_text()
    report = run_deterministic(memo, args.profile, str(path))
    judge = run_judge(memo) if args.judge else None

    if args.json:
        out = asdict(report)
        out["judge"] = judge
        out["result"] = "PASS" if (not report.failed and not (judge and judge.get("verdict") == "FAIL")) else "FAIL"
        print(json.dumps(out, indent=2))
    else:
        print(render_human(report, judge))

    failed = bool(report.failed) or bool(judge and judge.get("verdict") == "FAIL")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
