"""Run the generator over every thread once and freeze the output.

Run: PYTHONPATH=src python scripts/generate.py
     PYTHONPATH=src python scripts/generate.py --dry-run    (mock, no key, free)

Reading conventions match dataset.py / generator.py: WHY / HOW / laddered TODO.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evalsys import dataset as d
from evalsys.generator import Generator
from evalsys.llm import LLMRefusal, MockLLM, get_llm

OUT_PATH = Path(__file__).resolve().parents[1] / "data" / "generated.jsonl"


def main() -> int:
    if(OUT_PATH.exists() and "--force" not in sys.argv):
            print(f"ERROR: {OUT_PATH} already exists. Use --force to overwrite.")
            return 1
    
    # TODO 1 — pick the provider.
  
    providermodel = MockLLM() if "--dry-run" in sys.argv else get_llm()
    threads = d.load_threads()  # dict[str, Thread]

    # TODO 2 — generate one reply per thread.
   
    generator = Generator(providermodel)
    list_items = []
    for tid in sorted(threads):
        print(f"INFO [{tid}] Generating reply...")
        try:
            reply = generator.generate(threads[tid])
        except LLMRefusal as e:
            print(f"ERROR [{tid}] Failed to generate reply: {e}")
            reply = None
        info = {"thread_id" : tid, "reply": reply, "model": getattr(providermodel, "model", "mock"), "prompt_version": "v2"}
        list_items.append(info)
        

    # TODO 3 — handle a refusal without losing the whole run.
    #   ClaudeLLM raises LLMRefusal. Eight good replies shouldn't be thrown away
    #   because the ninth thread tripped something.
    #
    #   Decide and write down: skip the row, or write it with reply=None and a
    #   "refused": true flag? The second is better for the writeup — a refusal is
    #   a real generator failure and silently dropping it makes the system look
    #   like it handled 9/9. Whatever you choose, the count in the summary line
    #   should make it visible.
    ...

    # TODO 4 — write the file.
    #   goal:  one JSON object per line, UTF-8, newline-terminated.
    #   shape: "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n"
    #   nudge: ensure_ascii=False keeps the em-dashes and curly quotes readable
    #          in the file rather than as — escapes. Same reason normalize
    #          _jsonl.py uses it.
    #
    #   WHY not append: this script is idempotent by design — rerunning it should
    #          replace the frozen set, not grow it. Appending would leave you with
    #          two replies per thread and no way to tell which was current.
    #
    #   Guard worth adding: if OUT_PATH already exists and --force wasn't passed,
    #          refuse and say so. Overwriting the frozen set is exactly the
    #          accident this file exists to prevent.
    generatedcontent= "\n".join(json.dumps(info, ensure_ascii=False) for info in list_items) + "\n"
    OUT_PATH.write_text(generatedcontent, encoding="utf-8")

    # TODO 5 — print a one-line summary: how many written, which model, where.
    print(f"INFO: {len(list_items)} items written for model {getattr(providermodel, 'model', 'mock')} to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
