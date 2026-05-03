"""
Abre a arena visual Pygame que consome o código em ``legacy.astas3d``.

Faz parte dos extras/demos; a implementação final do trabalho está em ``src/``
e ``experiments/``. Execute a partir da raiz: ``python3 arena.py`` ou
``python3 scripts/arena_pygame.py``.

A arena legada só expõe ``astar`` (A*) e ``greedy`` (busca gulosa). Para BFS, DFS, UCS e
comparação completa dos cinco algoritmos no modelo ``src/``, use
``python3 experiments/run_batch.py``.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pygame

import legacy.astas3d as arena_mod

arena_mod.MOVE_DELAY = 180  # ms entre ações (maior = mais lento).
arena_mod.WATER_DENSITY = 0.12  # densidade de água na camada 0 (0.0–1.0).


def main(argv: list[str] | None = None) -> None:
    """Inicializa SDL e abre a arena; algoritmo configurável por linha de comandos."""
    p = argparse.ArgumentParser(description="Arena Pygame (legado): A* ou busca gulosa.")
    p.add_argument(
        "--algorithm",
        "-a",
        choices=("astar", "greedy"),
        default="astar",
        help="Planejador na arena: astar (omissão) ou greedy (gulosa).",
    )
    args = p.parse_args(argv)

    os.environ.pop("SDL_VIDEODRIVER", None)
    os.environ.pop("SDL_AUDIODRIVER", None)

    pygame.quit()
    pygame.init()

    arena_mod.run_game(algorithm=args.algorithm)


if __name__ == "__main__":
    main()
