"""Executa a mesma arena visual definida em `arena.py`."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.arena_pygame import main as run_arena


def main() -> None:
    """Executa a arena legacy (mesmo fluxo que ``python3 arena.py``)."""
    run_arena(sys.argv[1:])


if __name__ == "__main__":
    main()
