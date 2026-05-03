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

_PICK_W, _PICK_H = 720, 420


def _ensure_pygame_ready() -> None:
    """Re-inicializa o Pygame após `run_game` (que chama `pygame.quit()` no legado)."""
    if not pygame.get_init():
        pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()


def _pick_algorithm_gui() -> str:
    """Janela inicial: escolher A* ou gulosa com rato ou teclas 1 / 2."""
    _ensure_pygame_ready()
    screen = pygame.display.set_mode((_PICK_W, _PICK_H))
    pygame.display.set_caption("Drone — escolha do algoritmo")

    try:
        title_font = pygame.font.SysFont("consolas", 32, bold=True)
        btn_font = pygame.font.SysFont("consolas", 26, bold=True)
        hint_font = pygame.font.SysFont("consolas", 18)
    except Exception:
        title_font = pygame.font.Font(None, 34)
        btn_font = pygame.font.Font(None, 28)
        hint_font = pygame.font.Font(None, 22)

    rect_astar = pygame.Rect(70, 160, 280, 110)
    rect_greedy = pygame.Rect(_PICK_W - 70 - 280, 160, 280, 110)
    clock = pygame.time.Clock()

    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit(0)
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_ESCAPE, pygame.K_q):
                    pygame.quit()
                    raise SystemExit(0)
                if ev.key in (pygame.K_1, pygame.K_KP1):
                    return "astar"
                if ev.key in (pygame.K_2, pygame.K_KP2):
                    return "greedy"
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if rect_astar.collidepoint(ev.pos):
                    return "astar"
                if rect_greedy.collidepoint(ev.pos):
                    return "greedy"

        screen.fill((18, 24, 34))
        title = title_font.render("Algoritmo de planeamento", True, (220, 230, 245))
        screen.blit(title, (_PICK_W // 2 - title.get_width() // 2, 48))

        sub = hint_font.render(
            "Clique ou 1 / 2  ·  ESC sair  ·  Após cada partida: M para voltar aqui",
            True,
            (140, 160, 185),
        )
        screen.blit(sub, (_PICK_W // 2 - sub.get_width() // 2, 100))

        for r, label, rgb in (
            (rect_astar, "A* (astar)", (129, 199, 132)),
            (rect_greedy, "Busca gulosa", (77, 208, 225)),
        ):
            pygame.draw.rect(screen, rgb, r, border_radius=12)
            pygame.draw.rect(screen, (20, 30, 45), r, width=2, border_radius=12)
            t = btn_font.render(label, True, (12, 18, 28))
            screen.blit(t, (r.centerx - t.get_width() // 2, r.centery - t.get_height() // 2))

        clock.tick(60)
        pygame.display.flip()


def main(argv: list[str] | None = None) -> None:
    """Inicializa SDL; por omissão abre menu gráfico para escolher o algoritmo."""
    p = argparse.ArgumentParser(description="Arena Pygame (legado): A* ou busca gulosa.")
    p.add_argument(
        "--algorithm",
        "-a",
        choices=("astar", "greedy"),
        default=None,
        help="Opcional: saltar o menu e usar astar ou greedy (útil para scripts).",
    )
    args = p.parse_args(argv)

    os.environ.pop("SDL_VIDEODRIVER", None)
    os.environ.pop("SDL_AUDIODRIVER", None)

    pygame.quit()
    pygame.init()

    algorithm = args.algorithm if args.algorithm is not None else _pick_algorithm_gui()

    while True:
        arena_mod.run_game(algorithm=algorithm)
        if arena_mod.REQUEST_QUIT:
            break
        if arena_mod.REQUEST_ALGO_MENU:
            _ensure_pygame_ready()
            algorithm = _pick_algorithm_gui()
            continue
        break


if __name__ == "__main__":
    main()
