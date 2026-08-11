"""
Aggregation — gates, then scored. The rule that makes the verdict defensible. 

Implements criteria for 2 tier Pipeline.

This file is small on purpose. It contains one decision, and that decision is the
answer to the challenge question:

    a reply is acceptable if it passes every gate AND every scored criterion,
    and the judge does not run at all if a gate failed.

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
    gates = run_gates(reply, thread)
    if any(not gate.passed for gate in gates):
        return Verdict(False, gates)

    judged = run_judge(llm, reply, thread)
    return Verdict(all(j.passed for j in judged) , gates, judged)


def evaluate_all(llm: LLM, replies, threads: dict[str, Thread]) -> dict[str, Verdict]:
    """Every labeled reply -> its verdict, keyed by reply id."""
    results: dict[str, Verdict] = {}
    for i, labeled in enumerate(replies, start=1):
        print(f"[{i}/{len(replies)}] {labeled.id} ({labeled.thread_id})")
        results[labeled.id] = evaluate(llm, labeled.body, threads[labeled.thread_id])

    return results


# ─── what phase 4 asks this file ─────────────────────────────────────────────

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
