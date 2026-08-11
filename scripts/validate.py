"""Phase 4 — does the evaluator agree with the humans? One file, four questions.

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

#   FORMULA
#       kappa = (Po - Pe) / (1 - Pe)  =>  Po  observed agreement  | Pe  expected agreement  
#       Pe = P(both say yes by chance) + P(both say no by chance)
#
#   Read the numerator as "agreement we actually got, minus agreement we'd have
#   got for free", and the denominator as "the agreement that was available to
#   earn". Kappa is the fraction of the earnable agreement that was earned.
#
#   SCALE
#       1.0   identical verdicts
#       0.0   exactly what chance predicts — no skill demonstrated
#       < 0   worse than chance, i.e. systematically disagreeing
#     > 0.6   conventionally called "substantial" (Landis & Koch, 1977)

#   Docs: https://en.wikipedia.org/wiki/Cohen%27s_kappa
#         Landis & Koch (1977), "The Measurement of Observer Agreement"


def cohens_kappa(human: list[bool], machine: list[bool]) -> float:
    """Agreement between two raters, corrected for chance. -1 to 1."""

    both_yes = sum(1 for h, m in zip(human, machine) if h and m)
    both_no = sum(1 for h, m in zip(human, machine) if not h and not m)
    n = len(human)
    observed = (both_yes + both_no) / n
    human_yes = sum(human) # sum of True value which are synonymous with 1.
    machine_yes = sum(machine)
    human_no = n - human_yes
    machine_no = n - machine_yes
    p_yes = (human_yes / n) * (machine_yes / n)
    p_no = (human_no / n) * (machine_no / n)
    expected = p_yes + p_no

    # Pe hits exactly 1.0 only when both raters put every item in the SAME single
    # class — all-accept or all-reject on both sides. 
    if expected >= 1.0:
        return 1.0 if observed == 1.0 else 0.0

    return (observed - expected) / (1 - expected)


# ─── 2. trap recall ──────────────────────────────────────────────────────────

def trap_recall(replies, verdicts) -> tuple[int, int]:
    """How many broken replies did we reject? Returns (caught, total)."""

    caught = 0
    total = 0
    for reply in replies:
        if reply.defect != d.Defect.NONE:
            v = verdicts[reply.id]
            if not v.acceptable:
                caught += 1
            total += 1
    return (caught, total)

# ─── 3. tier check ───────────────────────────────────────────────────────────

def tier_check(replies, verdicts) -> tuple[int, int]:
    """Was each trap caught by the tier that owns its defect? (right, total)."""
    right = 0
    total = 0
    
    for reply in replies:
        if reply.defect != d.Defect.NONE:
            v = verdicts[reply.id]
            expected = reply.defect
            actual = v.failures
            if expected in actual:
                right += 1
            total += 1
    return (right, total)

# ─── 4. exclusions ───────────────────────────────────────────────────────────

def exclusions(threads, replies, verdicts) -> dict[str, int]:
    """What we did not count. Reported, never silently dropped."""
    # TODO 4 — three counts:
    #   gate_skipped  = threads with gate_applicable == False
    #   judge_skipped = verdicts where judge_ran is False (a gate sank it first)
    #   parse_failed  = replies the judge returned unreadable JSON for
    
    gate_skipped = sum(1 for t in threads.values() if not t.gate_applicable)
    judge_skipped = sum(1 for v in verdicts.values() if not v.judge_ran)
    parse_failed = 0 # currently not tracked, but could be if we catch the exception in evaluate_all and increment a counter. 
            
    return {"gate_skipped": gate_skipped, "judge_skipped": judge_skipped, "parse_failed": parse_failed}


# ─── 5. per-reply audit ──────────────────────────────────────────────────────
# WHY: "12/12 caught, 7/12 by the right tier" says a gap exists but not where.
# A trap rejected for the wrong reason counts as a catch under any accuracy
# metric and is really a near miss — this prints which mechanism fired instead.

def audit(replies, verdicts) -> None:
    """One line per trap: what we labelled it vs what the evaluator claimed."""
    print()
    print(f"{'':6}{'reply':10}{'labelled':22}{'tier':8}claimed by the evaluator")
    print("-" * 84)

    for r in replies:
        v = verdicts[r.id]
        claimed = [x.value for x in v.failures]

        if r.defect is d.Defect.NONE:
            if not v.acceptable:
                print(f"FP    {r.id:10}{'(known-good)':22}{'-':8}{claimed}")
            continue

        # Three outcomes, and they mean different things:
        #   OK     the tier that owns this defect named it — the design worked
        #   WRONG  rejected, but for a different reason than the human labelled
        #   MISS   not rejected at all
        if r.defect in v.failures:
            mark = "OK   "
        elif not v.acceptable:
            mark = "WRONG"
        else:
            mark = "MISS "

        # A skipped judge is the likeliest cause of a WRONG on a scored-tier
        # defect: a gate sank the reply first, so the criterion never ran.
        note = "" if v.judge_ran else "   <- judge never ran (gate sank it)"
        # Humans allow style defects to still be acceptable; the evaluator does
        # not. Those show up as rejections of replies humans would have sent.
        fp = "   <- human said ACCEPTABLE" if r.acceptable and not v.acceptable else ""

        print(f"{mark} {r.id:10}{r.defect.value:22}{r.defect.tier:8}{claimed}{note}{fp}")

    print("-" * 84)


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

    print(f"provider: {getattr(llm, 'model', 'MOCK (no API key)')}")

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

    audit(replies, verdicts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
