"""Core data types for the hybrid evaluation system.

Plain dataclasses on purpose — phase 1 should run with zero installs, so the
dataset and its checks stay usable before anyone sets up an API key.

Docs you'll want open:
  dataclasses: https://docs.python.org/3/library/dataclasses.html
  str-enums:   https://docs.python.org/3/howto/enum.html#others
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, asdict
from enum import Enum
from typing import Any


# ─── Defect — what is deliberately wrong with a reply ────────────────────────
# This is the label space for the whole validation set. It's a design decision,
# not bookkeeping: each member names a failure mode, and each failure mode is
# owned by exactly one evaluator tier. If a defect doesn't map to a tier, either
# the tier is missing or the defect isn't real.
#
# Subclassing str as well as Enum means Defect.NONE == "none" is True, so these
# serialize to JSONL without a custom encoder.


class Defect(str, Enum):
    NONE = "none"  # a known-good reply

    # Gate tier — non-negotiable, any of these sinks the reply outright.
    INVENTED_POLICY = "invented_policy"      # asserts a rule the context never grants
    CONTRADICTS_CONTEXT = "contradicts_context"  # asserts something the context flatly denies
    OVERPROMISE = "overpromise"              # commits to an outcome or date support can't guarantee
    WRONG_FACT = "wrong_fact"                # right shape, wrong identifier or amount

    # Scored tier — should pass the gates, but score badly.
    MISSED_ISSUE = "missed_issue"            # customer asked two things, reply answers one
    WRONG_RESOLUTION = "wrong_resolution"    # plausible, faithful, but not the right fix
    NO_NEXT_STEP = "no_next_step"            # leaves the customer with nothing to do or expect
    BAD_TONE = "bad_tone"                    # curt, blaming, or robotic
    VERBOSE = "verbose"                      # correct content buried in filler

    @property
    def tier(self) -> str:
        """Which evaluator tier owns catching this: "gate", "scored", or "none"."""
        if self is Defect.NONE:
            return "none"
        gate = {
            Defect.INVENTED_POLICY,
            Defect.OVERPROMISE,
            Defect.CONTRADICTS_CONTEXT,
            Defect.WRONG_FACT,
        }
        return "gate" if self in gate else "scored"


# ─── Message / Thread — the input side ───────────────────────────────────────

@dataclass(frozen=True)
class Message:
    """One email in a support thread."""

    sender: str  # "customer" | "agent"
    body: str


@dataclass(frozen=True)
class Thread:
    """A support thread plus the ground truth a faithful reply may draw on."""

    id: str
    category: str
    messages: list[Message]
    context: list[str]
    issues: list[str]   # distinct things the customer needs handled
    ideal_reply: str    # *a* good reply, not *the* correct answer — guardrail only

    critical_facts: list[str] = field(default_factory=list)

    # WHY: For conversational threads with no factual claims to be
    # unfaithful to. The gate trivially "passes" those, and counting free passes
    # inflates its reported accuracy. 
    gate_applicable: bool = True

    @property
    def premise(self) -> str:
        """The text handed to the NLI gate as its premise.

        Premise = everything true; hypothesis = a sentence from the reply. So
        this needs to contain both the conversation so far AND the known facts,
        flattened to plain text.
        """
        thread = "\n".join(f"{m.sender}: {m.body}" for m in self.messages)
        facts = "\n".join(f" - {block}" for block in self.context)
        return f"{thread}\n\nKnown facts available to the agent:\n{facts}"
        

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Thread:
        """Build from a parsed JSONL row."""
        return cls(
            id=data["id"],
            category=data["category"],
            messages=[Message(**m) for m in data["messages"]],
            context=data["context"],
            issues=data["issues"],
            ideal_reply=data["ideal_reply"],
            # .get() with a fallback, not [] — older rows predate these fields
            # and must keep loading.
            critical_facts=list(data.get("critical_facts", [])),
            gate_applicable=bool(data.get("gate_applicable", True)),
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to a dictionary."""
        return asdict(self)


# ─── LabeledReply — the output side, and the ruler ───────────────────────────

@dataclass(frozen=True)
class LabeledReply:
    """A reply with a human-assigned verdict.

    This is the ground truth the evaluator gets scored against in Phase 4, so
    `acceptable` is deliberately a human judgement and NOT derived from the
    evaluator. Keep it that way or the kappa is measuring nothing.
    """

    id: str
    thread_id: str
    body: str
    defect: Defect

    # "would an experienced support lead send this?" — human call, never derived
    # from the evaluator
    acceptable: bool
    notes: str =""
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> LabeledReply:
        return cls(
            id=d["id"],
            thread_id=d["thread_id"],
            body=d["body"],
            defect=Defect(d["defect"]),
            acceptable=d["acceptable"],
            notes=d.get("notes", ""),
            tags=list(d.get("tags", [])),
        )
        
    def to_dict(self) -> dict[str, Any]:
        """Convert to a dictionary."""
        data = asdict(self)
        data["defect"] = self.defect.value
        return data
