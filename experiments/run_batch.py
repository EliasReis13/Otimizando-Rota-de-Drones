"""
Ponto de entrada “simples” do trabalho prático.

Gera ≥50 instâncias reproduzíveis e exporta CSV com métricas dos cinco algoritmos.

Fatias experimentais (coluna experiment_slice):
- baseline: vento + TNFZ + bateria confortável
- no_wind: sem campo de vento
- no_tnfz: sem zonas temporárias
- low_battery: autonomia inicial baixa (força paradas em estações)

Uso (a partir da raiz do repositório, com o ambiente virtual ativo):
    python3 experiments/run_batch.py
    python3 experiments/run_batch.py --output results/meu_lote.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.environment import generate_instance
from src.runners import run_all_algorithms
from src.search_problem import DroneUrbanSearchProblem


def _instances():
    """55 instâncias: 4 fatias × 10 seeds + 15 seeds baseline extras."""
    specs = []
    for seed in range(0, 10):
        specs.append((seed, "baseline", {}))
    for seed in range(10, 20):
        specs.append((seed, "no_wind", {"with_wind": False}))
    for seed in range(20, 30):
        specs.append((seed, "no_tnfz", {"with_tnfz": False}))
    for seed in range(30, 40):
        specs.append((seed, "low_battery", {"low_battery": True}))
    for seed in range(40, 55):
        specs.append((seed, "baseline", {}))
    return specs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results" / "batch_runs.csv",
        help="Arquivo CSV de saída",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=45.0,
        help="Tempo máximo (s) de parede por algoritmo e instância",
    )
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "seed",
        "experiment_slice",
        "nx",
        "ny",
        "nz",
        "battery_max",
        "initial_battery",
        "time_horizon",
        "algorithm",
        "success",
        "path_cost",
        "plan_length",
        "wall_time_sec",
        "visited_nodes",
        "max_fringe_size",
        "iterations",
        "timeout",
        "error",
    ]

    rows_written = 0
    with args.output.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()

        for seed, slice_name, kwargs in _instances():
            inst = generate_instance(seed, experiment_slice=slice_name, **kwargs)
            problem = DroneUrbanSearchProblem(inst)
            results = run_all_algorithms(
                problem,
                graph_search=True,
                wall_timeout_sec=args.timeout,
            )
            for algo_key, rr in results.items():
                w.writerow(
                    {
                        "seed": seed,
                        "experiment_slice": slice_name,
                        "nx": inst.nx,
                        "ny": inst.ny,
                        "nz": inst.nz,
                        "battery_max": inst.battery_max,
                        "initial_battery": inst.initial_battery,
                        "time_horizon": inst.time_horizon,
                        "algorithm": algo_key,
                        "success": rr.success,
                        "path_cost": rr.path_cost if rr.success else "",
                        "plan_length": rr.plan_length if rr.plan_length is not None else "",
                        "wall_time_sec": f"{rr.wall_time_sec:.6f}",
                        "visited_nodes": rr.visited_nodes,
                        "max_fringe_size": rr.max_fringe_size,
                        "iterations": rr.iterations,
                        "timeout": rr.timeout,
                        "error": rr.error or "",
                    }
                )
                rows_written += 1

    print(f"Escrito {rows_written} linhas de dados em {args.output}")


if __name__ == "__main__":
    main()
