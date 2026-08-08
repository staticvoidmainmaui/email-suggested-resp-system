"""Phase 4 — does the evaluator agree with the humans? One file, four questions.

This is the part the challenge actually asks about. Everything before it built a
measurement; this checks whether the measurement is any good.

Four numbers, in order of how much they matter:

  1. kappa        — agreement with the human `acceptable` label, corrected for
                    chance. Plain accuracy is misleading when the classes are
                    unbalanced: guessing "acceptable" on a 60/40 set scores 60%
                    while knowing nothing. Kappa scores that 0.
  2. trap recall  — of the deliberately-broken replies, how many did we catch?
  3. tier check   — was each one caught by the tier that OWNS its defect? A
                    WRONG_FACT caught by the judge instead of the fact gate is
                    luck, not a working gate.
  4. exclusions   — what we didn't count, and why. Reported, never hidden.

Run: PYTHONPATH=src python scripts/validate.py --dry-run
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evalsys import dataset as d
from evalsys.evaluate import evaluate_all
from evalsys.llm import MockLLM, get_llm


# ─── 1. kappa ────────────────────────────────────────────────────────────────

def cohens_kappa(human: list[bool], machine: list[bool]) -> float:
    """Agreement between two raters, corrected for chance. -1 to 1."""
    # TODO 1 — four counts, then two formulas. No library needed.
    #
    #   both_yes = count where human and machine are both True
    #   both_no  = both False
    #   n        = len(human)
    #
    #   observed = (both_yes + both_no) / n
    #
    #   expected = chance agreement:
    #       p_yes = (human_yes/n) * (machine_yes/n)
    #       p_no  = (human_no/n)  * (machine_no/n)
    #       expected = p_yes + p_no
    #
    #   return (observed - expected) / (1 - expected)
    #
    #   Reading it: 1.0 = perfect, 0.0 = no better than chance, >0.6 is usually
    #   called substantial. Report the number, don't grade yourself on it.
    return 0.0


# ─── 2. trap recall ──────────────────────────────────────────────────────────

def trap_recall(replies, verdicts) -> tuple[int, int]:
    """How many broken replies did we reject? Returns (caught, total)."""
    # TODO 2 — loop the replies where reply.defect is not Defect.NONE.
    #   caught = the verdict for that reply has acceptable == False.
    #   Return (caught, total).
    #
    #   NOTE this asks "did we reject it", not "did we name the right defect".
    #   That's question 3.
    return (0, 0)


# ─── 3. tier check ───────────────────────────────────────────────────────────

def tier_check(replies, verdicts) -> tuple[int, int]:
    """Was each trap caught by the tier that owns its defect? (right, total)."""
    # TODO 3 — for each broken reply:
    #   expected = reply.defect          (the label)
    #   actual   = verdicts[reply.id].failures   (what we claimed)
    #   right if expected is in actual.
    #
    #   WHY this is separate from recall: rejecting a reply for the wrong reason
    #   still counts as a catch in question 2. Here it doesn't. The gap between
    #   the two numbers is the interesting part of the writeup.
    return (0, 0)


# ─── 4. exclusions ───────────────────────────────────────────────────────────

def exclusions(threads, replies, verdicts) -> dict[str, int]:
    """What we did not count. Reported, never silently dropped."""
    # TODO 4 — three counts:
    #   gate_skipped  = threads with gate_applicable == False
    #   judge_skipped = verdicts where judge_ran is False (a gate sank it first)
    #   parse_failed  = replies the judge returned unreadable JSON for
    #
    #   WHY report these: a gate that "passes" threads it declined to examine
    #   looks more accurate than it is. Saying so is the difference between a
    #   result and a claim.
    return {"gate_skipped": 0, "judge_skipped": 0, "parse_failed": 0}


# ─── run it ──────────────────────────────────────────────────────────────────

def main() -> int:
    dry = "--dry-run" in sys.argv

    if dry:
        # canned all-pass judge, so the plumbing runs free
        canned = json.dumps({
            k: {"passed": True, "reason": "mock"}
            for k in ["coverage", "resolution", "next_step", "tone", "concision"]
        })
        llm = MockLLM(fallback=canned)
    else:
        llm = get_llm()

    threads = d.load_threads()
    replies = d.load_replies()

    verdicts = evaluate_all(llm, replies, threads)

    human = [r.acceptable for r in replies]
    machine = [verdicts[r.id].acceptable for r in replies]

    k = cohens_kappa(human, machine)
    caught, total = trap_recall(replies, verdicts)
    right, t_total = tier_check(replies, verdicts)
    skipped = exclusions(threads, replies, verdicts)

    agree = sum(1 for h, m in zip(human, machine) if h == m)

    print()
    print("=" * 55)
    print(f"replies evaluated   {len(replies)}")
    print(f"raw agreement       {agree}/{len(replies)}")
    print(f"cohen's kappa       {k:.2f}")
    print(f"trap recall         {caught}/{total}")
    print(f"caught by own tier  {right}/{t_total}")
    print(f"exclusions          {skipped}")
    print("=" * 55)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
