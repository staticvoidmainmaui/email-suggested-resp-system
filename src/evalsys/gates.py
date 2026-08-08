"""The gate tier — pass/fail checks that sink a reply outright.

WHY gates exist as a separate tier: some failures aren't degrees. A reply that
invents a refund policy isn't a 4/10, it's unusable, and a weighted average lets
three good criteria outvote it. Gates are the answer to "why is faithfulness
weighted 0.3?" — they aren't weighted at all.

WHY they run without an LLM: a gate's verdict has to be defensible without
appealing to taste. `Thread.context` is a closed world, so "this sentence asserts
something outside the context" is a fact about the text, not an opinion about it.
That's the strongest claim in the whole system and it would be weaker coming from
a judge that was prompted into it.

Reading conventions match dataset.py / generator.py: WHY / HOW / laddered TODO.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


from .schema import Defect, Thread


#   messages   the conversation
#   context    the closed world — "assume retrieval worked"
#
#   issues         pre-decomposed intent.
#   ideal_reply   - it's the answer.
#   critical_facts  the evaluator's checklist of which numbers matter.
#   gate_applicable  evaluator metadata, 

@dataclass(frozen=True)
class GateResult:
    """One gate's verdict on one reply."""

    name: str            # which gate spoke
    passed: bool
    reason: str          # why it failed; empty string when it passed
    defect: Defect | None = None  # which Defect this gate owns, None if passed

    # WHY the defect is on the result rather than inferred by the caller: phase 4
    # asks "did the gate that owns WRONG_FACT actually catch the WRONG_FACT
    # traps?" That's only answerable if each result says which defect it claims.
    # A bare bool would give you an overall accuracy and nothing diagnosable.


# ─── gate 1: critical facts ──────────────────────────────────────────────────
# The cheapest gate in the system and the one to keep if you keep only one. No
# model, no key, no dependency — pure string work, so it's instant and its
# verdict is fully explainable.
#
# WHY it's needed at all when NLI exists: an MNLI model scores a digit-swapped
# hypothesis as ENTAILED, because "refund on order 88350" is structurally
# identical to the premise about 88530. Different mechanism, different blind
# spot — see the DIGIT SWAP probe in scripts/nli_probe.py.

# Three alternatives, because the things worth checking don't share a shape:
#   [A-Za-z]{2,}-\d+      a prefixed identifier — "ML-4402", "VPN-14". Matched
#                         WHOLE so it can be compared against critical_facts as
#                         written; extracting a bare "4402" and looking that up
#                         fails, which is exactly the false positive this gate
#                         produced before.
#   \$[\d,]+(?:\.\d{2})?  a money amount of ANY size. An earlier {2,} quantifier
#                         silently skipped everything under $100 — most refunds.
#   \b\d{4,}\b            a bare run of 4+ digits, i.e. an order ref.
#
# WHY not "any number": "5-10 business days" and "2 weeks" are prose, not claims
# about account state. Matching them fails almost every reply and the gate's
# precision collapses. The 4-digit floor is a judgement call — state it as a
# limitation rather than tuning it until the numbers look good.
_FACT_PATTERN = re.compile(r"[A-Za-z]{2,}-\d+|\$[\d,]+(?:\.\d{2})?|\b\d{4,}\b")


def check_facts(reply: str, thread: Thread) -> GateResult:
    """Fail if the reply states an identifier or amount that isn't in the context."""
    # TODO 1 — find the fact-shaped tokens in the reply and check each one.
    #   goal:  _FACT_PATTERN.findall(reply) gives candidates. Any candidate not
    #          present in thread.critical_facts is a wrong fact -> fail.
    #   shape: build a list of offenders, then one return at the end.
    #
    #   HOW to compare: critical_facts holds bare strings like "88530" and "$49".
    #          A candidate "$49" should match "$49", and "88530" should match
    #          "88530" — but the reply might write "88,530". Normalising both
    #          sides by stripping "$" and "," before comparing is two lines and
    #          saves a false positive.
    #
    #   WHY "not in critical_facts" rather than "contradicts a fact": you can't
    #          tell which fact a wrong number was *meant* to be. The closed-world
    #          assumption is what makes the simple version valid — if the number
    #          isn't in the context, the reply invented it, full stop.
    #
    #   Known false positive to accept and document: a reply saying "within 5-10
    #          business days" contains no fact-shaped token, but "call us on
    #          1-800-..." would. Note it in the writeup rather than special-casing;
    #          a stated limitation beats a silent hack.
    #
    #   returns: GateResult("facts", passed, reason, Defect.WRONG_FACT if failed)
    
    #strip
    critical_facts= {fact.strip(("$,.")) for fact in thread.critical_facts}


    #check
    unverified= [] #list of unmatched numbers in the reply not in critical facts
    for candidate in _FACT_PATTERN.findall(reply):
        candidate = candidate.strip("$,.")
        # Substring, not equality: critical_facts records "ML-4402" and "30
        # minutes", but a reply may legitimately write just "4402" or "30". An
        # equality test flags those as invented, which is a false positive on a
        # correct reply — the most expensive kind of error this gate can make,
        # because it sinks a good reply outright.
        if not any(candidate in fact for fact in critical_facts):
            unverified.append(candidate)
            
    if unverified:
        return GateResult("facts", False, f"Unverified facts: {', '.join(unverified)}", Defect.WRONG_FACT)
    
    return GateResult("facts", True, "No Matched Unverified Number", None)
    
    
            
    
    
    


# ─── gate 2: faithfulness (NLI) ──────────────────────────────────────────────
# WHY the import is lazy: torch is ~200MB and the model another 400MB. The fact
# gate above must stay runnable without either, or you can't test the harness on
# a machine that hasn't installed them. Same argument as ClaudeLLM's lazy import.

_NLI_MODEL = "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli"
_nli = None  # module-level cache; loading the model twice costs 30s for nothing

ENTAIL, NEUTRAL, CONTRA = "entailment", "neutral", "contradiction"


def _get_nli():
    from transformers import pipeline # lazy import
    
    global _nli
    if _nli is None:
        _nli = pipeline("text-classification", model=_NLI_MODEL, top_k=None)
    return _nli


def split_claims(reply: str) -> list[str]:
    """Sentences worth checking. Pleasantries and questions are not claims."""
    # TODO 3 — split into sentences, then drop the ones that aren't assertions.
    #   goal:  a list of sentences the gate should actually run NLI on.
    #   shape: re.split(r"(?<=[.!?])\s+", reply) is good enough — no need for a
    #          sentence tokenizer.
    #
    #   WHY the filter is load-bearing and not tidying: "Thanks for reaching out"
    #          scores NEUTRAL against any context, because it asserts nothing.
    #          Without this filter every reply fails the gate on its greeting and
    #          the gate reports 0% pass — see the pleasantries probe in
    #          nli_probe.py, which exists to prove exactly this.
    #
    #   Drop at least: sentences ending in "?" (a question is not an assertion),
    #          and very short ones (< ~5 words) which are almost all greetings
    #          and sign-offs.
    #
    #   Write down what you dropped. "The gate examined 4 of 7 sentences" is a
    #          number the writeup needs — an unstated filter looks like cheating.
    
    raw = [s.strip() for s in re.split(r"(?<=[.!?])\s+", reply)]
    kept=[s for s in raw if s and not s.endswith("?") and len(s.split()) >= 5] #filter the ? and short phrases - "hi"
    #return [f"Claim {i+1}: {s}" for i,s in enumerate(kept)]
    return kept



def check_faithfulness(reply: str, thread: Thread) -> GateResult:
    """Fail if any claim contradicts the context or isn't supported by it."""
    # TODO 4 — run each claim past the NLI model.
    #   goal:  premise = "\n".join(thread.context), hypothesis = one claim.
    #          Collect the label per claim; fail on the first CONTRADICTION.
    #
    #   The judgement call, and it's yours to make and defend:
    #     - contradiction  -> fail. Uncontroversial.
    #     - neutral        -> ??? "Not supported" is not the same as "false".
    #                         Failing on neutral makes the gate strict and will
    #                         catch INVENTED_POLICY; it will also fire on
    #                         harmless-but-unsupported sentences that survived
    #                         split_claims.
    #   Try both over the trap set, report both numbers, pick one. "We failed on
    #   contradiction only, because neutral cost us N false positives" is a
    #   result. Guessing is not.
    #
    #   HOW to skip: if thread.gate_applicable is False, return passed=True with
    #          a reason saying it was skipped. Counting free passes as successes
    #          inflates the gate's reported accuracy — phase 4 filters on this.
    #
    #   returns: GateResult("faithfulness", ..., Defect.CONTRADICTS_CONTEXT)
    
    if(thread.gate_applicable is False):
        return GateResult("faithfulness", True, "skipped: gate_applicable=False", None)

    premise = "\n".join(thread.context)
    hypothesis = split_claims(reply) #returning the list of claims off a reply 
    
    claims= list(enumerate(hypothesis))
    
    for i, claim in claims:
        out= _get_nli()({"text": premise, "text_pair": claim})
        label= max(out,key=lambda x: x['score'])['label'].lower()
        if(label == CONTRA):
            return GateResult("faithfulness", False, f"Claim {i+1}: {claim} contradicts the context", Defect.CONTRADICTS_CONTEXT)

    return GateResult("faithfulness", True,"", None)

# ─── guardrail stub: semantic drift ──────────────────────────────────────────
# NOT a gate and never a score. A number you look at, not a number you act on.
#
# WHY it stays a stub for now: sentence-transformers is another dependency for
# the least load-bearing signal in the system. The harness should have the hook
# so the shape is right; filling it in is optional.


def drift_flag(reply: str, thread: Thread) -> float:
    """Cosine similarity between the reply and thread.ideal_reply. STUB."""
    # TODO 5 (optional) — sentence-transformers, all-MiniLM-L6-v2, cosine of the
    #   two embeddings. Returns 0.0 until then.
    #
    #   WHY it must never become a gate: ideal_reply is *a* good reply, not *the*
    #   correct answer. Thresholding on similarity to it reintroduces exactly the
    #   reference-matching this whole system argues against — a better-worded
    #   reply would score worse. Report it, flag outliers for a human, stop there.
    return 0.0


# ─── the harness ─────────────────────────────────────────────────────────────

GATES = [check_facts, check_faithfulness]

# WHY a list of functions rather than if/elif: phase 4 wants per-gate numbers, so
# the harness has to be able to name and iterate them. Adding a gate is then one
# list entry, and the reporting picks it up for free.


def run_gates(reply: str, thread: Thread) -> list[GateResult]:
    """Every gate, always. No short-circuit."""
    # TODO 6 — call each gate, return all results.
    #   shape: one list comprehension.
    #
    #   WHY not short-circuit on the first failure: if the fact gate rejects a
    #   reply first, the faithfulness gate never sees it — so you can't report
    #   the faithfulness gate's recall, and whichever gate runs first looks
    #   artificially good. Speed is not the constraint on 21 replies.
    #
    #   The caller decides the verdict:
    #       any(not r.passed for r in run_gates(reply, thread))
    
    #if gate in GATES calls a list of gate checks with reply, and thread , then it will return a list of gate results
    #how done
    #gate in GATES iterates the list of gate methods
    #and calls each one with the reply and thread as arguments
    #returning a list of 2 gateresult obejcts
    
    return [gate(reply, thread) for gate in GATES]
    
    
