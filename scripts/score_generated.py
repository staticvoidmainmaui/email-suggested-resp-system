"""Run the evaluator over the generator's own output — closes the loop.

This measures the *generator* with that evaluator, which is the only number that
says anything about the product rather than the instrument.

Read the result alongside the kappa

Run: PYTHONPATH=src python scripts/score_generated.py
     PYTHONPATH=src python scripts/score_generated.py --dry-run
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evalsys import dataset as d
from evalsys.evaluate import evaluate
from evalsys.llm import MockLLM, get_llm

GENERATED = Path(__file__).resolve().parents[1] / "data" / "generated.jsonl"


def main() -> int:
    if not GENERATED.exists():
        print(f"ERROR: {GENERATED} not found — run scripts/generate.py first.")
        return 1

    rows = [json.loads(line) for line in GENERATED.read_text(encoding="utf-8").splitlines() if line.strip()]

    models = {r.get("model") for r in rows}
    if models == {"mock"}:
        print("ERROR: generated.jsonl holds MockLLM output. Regenerate with a key:")
        print("       python scripts/generate.py --force")
        return 1

    dry = "--dry-run" in sys.argv
    if dry:
        canned = json.dumps({
            k: {"passed": True, "reason": "mock"}
            for k in ["coverage", "resolution", "next_step", "tone", "concision"]
        })
        llm = MockLLM(fallback=canned)
    else:
        llm = get_llm()

    print(f"generator: {', '.join(sorted(str(m) for m in models))}")
    print(f"judge:     {getattr(llm, 'model', 'MOCK (no API key)')}")

    threads = d.load_threads()
    passed = 0
    refused = 0

    print()
    print(f"{'':7}{'thread':10}why")
    print("-" * 84)

    for row in rows:
        tid = row["thread_id"]
        reply = row.get("reply")

        # A refused generation is a generator failure, not an evaluator verdict.
        # Counting it as a fail would blame the wrong half of the system.
        if reply is None:
            refused += 1
            print(f"REFUSED {tid:10}generator declined — excluded from the rate")
            continue

        v = evaluate(llm, reply, threads[tid])
        if v.acceptable:
            passed += 1
            print(f"PASS    {tid:10}")
        else:
            why = [f"{g.name}: {g.reason}" for g in v.gates if not g.passed]
            why += [f"{j.criterion}: {j.reason}" for j in v.judged if not j.passed]
            print(f"FAIL    {tid:10}{why[0] if why else '(no reason recorded)'}")
            for extra in why[1:]:
                print(f"{'':18}{extra}")

    scored = len(rows) - refused
    print("-" * 84)
    print(f"{passed}/{scored} generated replies passed the full evaluator"
          + (f"  ({refused} refused, excluded)" if refused else ""))
    print()
    print("Report this next to the phase 4 numbers — a pass rate is only as")
    print("trustworthy as the evaluator that produced it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
