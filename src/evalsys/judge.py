"""The scored tier — an LLM judge for the criteria no cheap check can measure.

WHY an LLM here and not at the gate: "does this reply address both things the
customer asked?" has no string test. That's a judgement, so it gets a judge. The
gates already caught the failures that *aren't* judgements, which is why a soft
verdict here is acceptable — nothing load-bearing rests on it alone.

WHY binary and not 1-5: a 5-point scale needs anchors for every level, and every
anchor is a paragraph you have to defend ("why is this a 3 and not a 4?"). Binary
verdicts compare directly against the human `acceptable` label, so kappa needs no
threshold in between. Fewer degrees of freedom, fewer things to argue about.

WHY all five criteria in one call: 5x fewer calls. The cost is the halo effect —
a judge that has decided a reply is weak tends to mark it down everywhere. That
cost is measurable, not theoretical, so measure it (see the note at the bottom)
rather than asserting it away.

Reading conventions match gates.py: WHY / HOW / laddered TODO.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from .llm import LLM
from .schema import Defect, Thread


@dataclass(frozen=True)
class JudgeResult:
    """One criterion's verdict on one reply."""

    criterion: str
    passed: bool
    reason: str          # the judge's own words — this is the audit trail
    defect: Defect       # which defect a failure here implies



# Order matters. Coverage runs first on purpose: it's the only criterion with
# ground truth (thread.issues), so it anchors the judge on evidence before the
# subjective ones. A judge that starts on "tone" has formed an opinion by the
# time it reaches the checkable question.

CRITERIA: dict[str, Defect] = {
    "coverage": Defect.MISSED_ISSUE,
    "resolution": Defect.WRONG_RESOLUTION,
    "next_step": Defect.NO_NEXT_STEP,
    "tone": Defect.BAD_TONE,
    "concision": Defect.VERBOSE,
}


JUDGE_SYSTEM = """\
You grade a single drafted email reply against five criteria. You are not
rewriting it and not advising on it - you are recording whether it meets each
criterion, and citing the text that decided it.

Judge the five criteria one at a time, in the order listed. Reach a verdict on
each before you consider the next, and judge each only on what its own rule says.
A reply can fail one criterion and pass the other four.

coverage
  The issues the sender raised are listed for you. Fails if any listed issue goes
  unaddressed. Addressed means answered, actioned, or explicitly deferred with a
  reason - not merely alluded to.

resolution
  Fails if the action the reply takes is not the right one given the known facts,
  or if it takes no action where the facts call for one.

next_step
  Fails if the reply leaves the sender with nothing to expect and nothing to do -
  no stated action, no timeframe, no owner. A next step can belong to either
  party, but it has to be concrete enough that nobody needs to write back to ask
  what happens now.

tone
  Fails if the reply is curt, blaming, robotic, or pitched at the wrong register
  for the sender. Warmth is not required; a stiff reply to a casual message fails
  this, and so does false cheer about a real problem.

concision
  Fails if the useful content is buried - restated background the sender already
  knows, hedging that says nothing, or padding around a short answer. Length
  alone is not the test: a long reply doing necessary work passes, a short one
  padded with filler does not.

Every reason must quote the specific words from the reply that decided the
verdict. A verdict you cannot point at is not a verdict.

Return ONLY a JSON object, with exactly these five keys:

{"coverage": {"passed": true, "reason": "..."},
 "resolution": {"passed": true, "reason": "..."},
 "next_step": {"passed": true, "reason": "..."},
 "tone": {"passed": true, "reason": "..."},
 "concision": {"passed": true, "reason": "..."}}

Each reason is one sentence. No markdown fences, no commentary before or after
the JSON.
"""

def build_user_prompt(reply: str, thread: Thread) -> str:

    text = "\n".join([
        f"--- KNOWN FACTS ---",
        *[f"- {fact}" for fact in thread.context],
        f"--- CONVERSATION ---",
        *[f"[{m.sender}] {m.body}" for m in thread.messages],
        f"--- ISSUES ---",
        *[f"- {issue}" for issue in thread.issues],
        f"--- REPLY UNDER EVALUATION ---",
        reply
    ])
    return text


def parse_verdicts(raw: str) -> dict[str, dict]:
    """Model text -> the five verdicts. Raises if it can't."""

    raw = raw.strip()
    if raw.startswith("```json"):
        raw = raw[7:]
    if raw.endswith("```"):
        raw = raw[:-3]
    try:
        parsed= json.loads(raw) # parses into json
        for criterion in CRITERIA:
            if criterion not in parsed:
                raise ValueError(f"Missing criterion: {criterion}")
    except json.JSONDecodeError as e:
        raise ValueError("Failed to parse JSON") from e
    
    return parsed


def run_judge(llm: LLM, reply: str, thread: Thread) -> list[JudgeResult]:
    """All five criteria, one call."""
    # TODO 4 — call, parse, build results.
    #   shape: llm.complete(JUDGE_SYSTEM, build_user_prompt(...)) -> parse ->
    #          one JudgeResult per entry in CRITERIA, defect from the dict.
    #
    #   HOW to iterate: `for name, defect in CRITERIA.items()` keeps the criterion
    #          and its defect together, so a result can never be built with the
    #          wrong defect attached.
    user_prompt = build_user_prompt(reply, thread)
    response = llm.complete(JUDGE_SYSTEM, user_prompt)
    verdicts = parse_verdicts(response)
    results = []
    for name, defect in CRITERIA.items():
        if name in verdicts:
            results.append(JudgeResult(criterion=name, defect=defect, passed=verdicts[name]['passed'], reason=verdicts[name]['reason']))
            #appends each name which is the criteria found in the CRITERIA lsit , with result off the json object
            #can append the whole thing with all the fields using verdicts[name][field] pattern
    return results


# ─── validating the batching decision ────────────────────────────────────────
# TODO 5  - 
#   
#   Add a `batched: bool = True` parameter. When False, make five calls, each
#   naming a single criterion. Then run both over ~10 replies and diff.
#
#   The writeup line you're buying:
#     "Batching all five criteria into one call disagreed with single-criterion
#      calls on N of 50 judgments, all in the direction of correlated failure.
#      We batch, at that measured cost, for a 5x reduction in calls."
# 
#  | Currently will run batched, with parameter can print wether batched or not in the replies |
