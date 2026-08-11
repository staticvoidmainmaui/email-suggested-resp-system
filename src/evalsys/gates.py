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

 

# ─── gate 1: critical facts ( deterministic) ──────────────────────────────
_FACT_PATTERN = re.compile(r"[A-Za-z]{2,}-\d+|\$[\d,]+(?:\.\d{2})?|\b\d{4,}\b")


def check_facts(reply: str, thread: Thread) -> GateResult:
    """Fail if the reply states an identifier or amount that isn't in the context."""
    # TODO 1 — find the fact-shaped tokens in the reply and check each one.

    #strip
    critical_facts = {fact.strip("$,. ") for fact in thread.critical_facts}

    #check
    unverified= [] #list of unmatched numbers in the reply not in critical facts
    for candidate in _FACT_PATTERN.findall(reply):
        candidate = candidate.strip("$,.")
       
        if not any(candidate in fact for fact in critical_facts):
            unverified.append(candidate)
            
    if unverified:
        return GateResult("facts", False, f"Unverified facts: {', '.join(unverified)}", Defect.WRONG_FACT)
    
    return GateResult("facts", True, "No Matched Unverified Number", None)
    

# ─── gate 2: faithfulness (NLI) ──────────────────────────────────────────────

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
   
    raw = [s.strip() for s in re.split(r"(?<=[.!?])\s+", reply)]
    kept=[s for s in raw if s and not s.endswith("?") and len(s.split()) >= 5] #filter the ? and short phrases - "hi"
    #return [f"Claim {i+1}: {s}" for i,s in enumerate(kept)]
    return kept



def check_faithfulness(reply: str, thread: Thread) -> GateResult:
    """run each claim past the NLI model"""

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

def drift_flag(reply: str, thread: Thread) -> float:
    """Cosine similarity between the reply and thread.ideal_reply. STUB."""
    # TODO 5 (optional) — sentence-transformers, all-MiniLM-L6-v2, cosine of the
    #   two embeddings. 
    
    # NOTE Completeled stubbed and skipped the actual implementation of the drift flag. The function currently returns 0.0 as a placeholder.
    return 0.0


# ─── the harness ─────────────────────────────────────────────────────────────

GATES = [check_facts, check_faithfulness]


def run_gates(reply: str, thread: Thread) -> list[GateResult]:
    """call each gate and return all results"""
    
    return [gate(reply, thread) for gate in GATES]
    
    
