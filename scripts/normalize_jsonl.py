"""Re-emit a .jsonl file as exactly one record per line.

WHY: editors with a JSON formatter will happily pretty-print or wrap long lines
in a .jsonl file, which breaks the one-record-per-line contract that json.loads
depends on. Rather than making the loader tolerant of that (which would defeat
the point of JSONL), repair the file.

HOW it survives an already-broken file: json.JSONDecoder().raw_decode reads one
object starting at a given offset and tells you where it stopped. Looping on that
parses a stream of concatenated objects regardless of how they're split across
lines, which json.loads per-line cannot do.

Run: python scripts/normalize_jsonl.py data/threads.jsonl
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def normalize(path: Path) -> int:
    raw = path.read_text(encoding="utf-8")
    decoder = json.JSONDecoder()
    records: list[dict] = []
    i = 0
    while i < len(raw):
        # skip whitespace between objects, including the newlines a formatter added
        while i < len(raw) and raw[i].isspace():
            i += 1
        if i >= len(raw):
            break
        obj, end = decoder.raw_decode(raw, i)
        records.append(obj)
        i = end

    # ensure_ascii=False keeps real characters instead of \uXXXX escapes;
    # separators drops the space after ": " so lines stay as short as they can.
    lines = [json.dumps(r, ensure_ascii=False, separators=(", ", ": ")) for r in records]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(records)


if __name__ == "__main__":
    for arg in sys.argv[1:] or ["data/threads.jsonl", "data/replies.jsonl"]:
        p = Path(arg)
        if p.exists():
            print(f"{p}: {normalize(p)} records normalized")
