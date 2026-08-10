"""Phase 1 runner — load the dataset, print the counts, fail loudly if it's broken.

Run it from the repo root:

    python check_dataset.py
"""

from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from evalsys import dataset  # noqa: E402  (import must follow the path fix above)

def main() -> int:
   
    threads = dataset.load_threads()
    replies = dataset.load_replies()
    
    print(dataset.summary(threads, replies))
   
    res = dataset.check(threads, replies)
    if res:
        for problem in res:
            print(problem, file=sys.stderr)
        return 1
    else:
        print("Dataset is clean.")
        return 0
    
if __name__ == "__main__":

    sys.exit(main())
