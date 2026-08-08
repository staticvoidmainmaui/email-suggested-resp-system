"""Aggregation — gates, then scored. The rule that makes the verdict defensible.

This file is small on purpose. It contains one decision, and that decision is the
answer to the challenge question:

    a reply is acceptable if it passes every gate AND every scored criterion,
    and the judge does not run at all if a gate failed.

WHY not a weighted average: a weighted average invites "why is faithfulness 0.3?"
and there is no principled answer. Worse, it lets three good criteria outvote one
disqualifying failure — a reply that invents a refund policy would score 7/10 on
tone, coverage and concision and come out "acceptable". Gates make that
arithmetically impossible rather than unlikely.

WHY the judge is skipped after a gate failure: the verdict is already decided, so
the calls would be spent to produce a tone score for a reply nobody will send.
Phase 4 has to know this happened — a reply with no judge results is not a reply
the judge passed, and conflating those two would inflate the judge's apparent
accuracy.

Reading conventions match gates.py / judge.py: WHY / HOW / laddered TODO.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .gates import GateResult, drift_flag, run_gates
from .judge import JudgeResult, run_judge
from .llm import LLM
from .schema import Defect, Thread


@dataclass(frozen=True)
class Verdict:
    """Everything the evaluator concluded about one reply."""

    acceptable: bool
    gates: list[GateResult]
    judged: list[JudgeResult] = field(default_factory=list)
    drift: float = 0.0

    # WHY keep the full result lists and not just the bool: phase 4 needs to ask
    # "which tier caught this trap?", and the bool can't answer it. The lists are
    # also the audit trail — a rejection you can't explain is a rejection nobody
    # will trust.

    @property
    def judge_ran(self) -> bool:
        """False when a gate failure short-circuited the scored tier."""

        return bool(self.judged)

    # create a list of the entire set of failures on valid set of gate applicaple entries
    @property
    def failures(self) -> list[Defect]:
        """Every defect the evaluator claims, gates first."""
        return ([g.defect for g in self.gates if not g.passed and g.defect]
        + [j.defect for j in self.judged if not j.passed and j.defect])

#aggregate the results of the different evaluators
def evaluate(llm: LLM, reply: str, thread: Thread) -> Verdict:
    """Gates, then scored. The whole aggregation rule."""
    # TODO 3 — implement the two-stage rule.

    gates = run_gates(reply, thread)
    if any(not gate.passed for gate in gates):
        return Verdict(False, gates)

    judged = run_judge(llm, reply, thread)
    return Verdict(all(j.passed for j in judged) , gates, judged)


def evaluate_all(llm: LLM, replies, threads: dict[str, Thread]) -> dict[str, Verdict]:
    """Every labeled reply -> its verdict, keyed by reply id."""
    # TODO 4 — loop over replies, look up replies[i].thread_id in threads, call
    #   evaluate, collect into a dict keyed by reply.id.
    #   Print progress. 21 sequential calls is a long silent wait.
    results: dict[str, Verdict] = {}
    for i, labeled in enumerate(replies, start=1):
        print(f"[{i}/{len(replies)}] {labeled.id} ({labeled.thread_id})")
        results[labeled.id] = evaluate(llm, labeled.body, threads[labeled.thread_id])

    return results


# ─── what phase 4 asks this file ─────────────────────────────────────────────
# Not code, but the reason the shapes above are what they are:
#
#   agreement   — verdict.acceptable vs LabeledReply.acceptable, over all replies
#                 that ran. That's the kappa.
#   trap recall — for each broken reply, is its labelled Defect in
#                 verdict.failures? Caught, or missed?
#   tier check  — was it caught by the tier that Defect.tier says owns it? A
#                 WRONG_FACT caught by the judge rather than the fact gate is a
#                 lucky pass, not a working gate, and reporting it as a catch
#                 would overstate the design.
#   exclusions  — count of gate_applicable=False threads, and of replies where
#                 judge_ran is False. Both get reported, never silently dropped.
