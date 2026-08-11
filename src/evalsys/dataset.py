"""Loading and integrity-checking the phase 1 dataset.

The dataset is two JSONL files: threads (the inputs) and replies (the labeled
outputs that later phases score the evaluator against).
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .schema import Defect, LabeledReply, Thread

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

STYLE_DEFECTS = {Defect.BAD_TONE, Defect.VERBOSE}


def _read_jsonl(path: Path) -> list[dict]:
    # HOW: the leading underscore is a convention meaning "module-private" —
    # nothing enforces it, it just tells a reader this isn't part of the API.

    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


#actually loads the threads into a dictionary

def load_threads(path: Path | None = None) -> dict[str, Thread]:
    """Threads keyed by id — replies reference threads by id, so a dict saves a scan."""

    threads: dict[str, Thread] = {}
    for row in _read_jsonl(path or DATA_DIR / "threads.jsonl"):
        t = Thread.from_dict(row)
        if t.id in threads:
            raise ValueError(f"duplicate thread id: {t.id}")
        threads[t.id] = t
    return threads

#loads the replies to read in a list 

def load_replies(path: Path | None = None) -> list[LabeledReply]:

    return [LabeledReply.from_dict(r) for r in _read_jsonl(path or DATA_DIR / "replies.jsonl")]


# ─── check(threads, replies) — the dataset's own test suite ──────────────────
# WHY this function exists: Phase 4's claim is "the evaluator agrees with humans,
# κ = 0.8x". That number only means something if the human labels are internally
# consistent. 

#Obtains the material from load_threads and load_replies and checks them against the gates
def check(threads: dict[str, Thread], replies: list[LabeledReply]) -> list[str]:
    problems: list[str] = []

    for t in threads.values():
        if not t.messages:
            problems.append(f"{t.id}: no messages")
        if not t.context:
            problems.append(f"{t.id}: empty context")
        if not t.issues:
            problems.append(f"{t.id}: empty issues")
            
    seen_ids : set[str] = set()
    
    for r in replies:
        if r.id in seen_ids:
            problems.append(f"{r.id}: duplicate id")
        if r.thread_id not in threads:
            problems.append(f"{r.id}: unknown thread {r.thread_id}")
        #flag problem if defect is none but returns not acceptable
        if r.defect is Defect.NONE and not r.acceptable:
            problems.append(f"{r.id}: NONE but not acceptable")
        # flag problem if the defect is not none and the defect is not in style defects but returns acceptable
        if r.defect is not Defect.NONE and r.acceptable and r.defect not in STYLE_DEFECTS:
            problems.append(f"{r.id}: {r.defect.value} but acceptable")
        
        seen_ids.add(r.id)

                    
    #here we have 4 situations for the reply type gotten and how to classify

    moment= {r.thread_id for r in replies if r.defect is Defect.NONE}
    for t in threads.values():
        if t.id not in moment:
            problems.append(f"{t.id}: no known-good reply")
    
    if len(replies) == 0:
        problems.append("no replies to analyze")
    else:
        acceptable_count = sum(1 for r in replies if r.acceptable)
        frac = acceptable_count / len(replies)
        if not (0.25 <= frac <= 0.6):
            problems.append(f"class balance issue: {frac:.2%} acceptable, should be 25-60%")

    return problems

# summary for Gate Counter reading the labeled replies.
def summary(threads: dict[str, Thread], replies: list[LabeledReply]) -> str:
    """Human-readable counts — this is what you paste into the writeup."""

    lines = []
    lines.append(f"Thread count: {len(threads)}")
    lines.append(f"Reply count: {len(replies)}")
    lines.append(f"Acceptable replies: {sum(1 for r in replies if r.acceptable)}")

    # Tier breakdown
    tier_counter = Counter(r.defect.tier for r in replies)
    lines.append("Breakdown by tier:")
    for tier, count in tier_counter.items():
        lines.append(f"  {tier}: {count}")

    # Defect breakdown
    defect_counter = Counter(r.defect for r in replies)
    lines.append("Breakdown by defect:")
    for defect, count in defect_counter.items():
        lines.append(f"  {defect.value}: {count}")

    return "\n".join(lines)
