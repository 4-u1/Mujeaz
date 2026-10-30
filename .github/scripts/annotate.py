"""Turns the tail of CI logs into GitHub error annotations (readable without log access)."""

import sys
from pathlib import Path

MAX_ANNOTATIONS, LINES = 9, 40


def esc(s: str) -> str:
    return s.replace("%", "%25").replace("\r", "").replace("\n", "%0A")


count = 0
for path in sys.argv[1:]:
    p = Path(path)
    if not p.exists() or count >= MAX_ANNOTATIONS:
        continue
    lines = p.read_text(errors="replace").splitlines()[-LINES * 2:]
    for i in range(0, len(lines), LINES):
        if count >= MAX_ANNOTATIONS:
            break
        print(f"::error title={p.name} (part {i // LINES + 1})::{esc(chr(10).join(lines[i:i + LINES]))}")
        count += 1
