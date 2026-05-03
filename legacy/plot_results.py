"""Gera graficos comparativos a partir do JSON do benchmark legacy."""

import json
import os
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RESULTS_FILE = str(ROOT / "results" / "legacy" / "benchmark.json")
OUTPUT_DIR = str(ROOT / "results" / "legacy" / "graficos")
 
CORES  = {"astar": "#4C9BE8", "greedy": "#E8784C"}
LABELS = {"astar": "A*",      "greedy": "Busca Gulosa"}
 
 
def load_results():
    """Carrega resultados JSON de benchmark.

    Returns:
        Lista de dicionarios com resultados por instancia.

    Raises:
        SystemExit: Quando o arquivo de resultados nao existe.
    """
    if not os.path.isfile(RESULTS_FILE):
        print(f"Arquivo '{RESULTS_FILE}' nao encontrado.")
        sys.exit(1)
    with open(RESULTS_FILE, encoding="utf-8") as f:
        return json.load(f)
 
 
def split_by_algo(data):
    """Agrupa resultados por algoritmo.

    Args:
        data: Resultados brutos do benchmark.

    Returns:
        Dicionario indexado por nome de algoritmo.
    """
    by_algo = {}
    for r in data:
        by_algo.setdefault(r["algoritmo"], []).append(r)
    return by_algo
 
 
def save_and_show(fig, filename):
    """Salva figura no diretorio de saida e exibe na tela.

    Args:
        fig: Figura Matplotlib a ser salva.
        filename: Nome do arquivo de saida (png).
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, filename)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    print(f"  Salvo: {path}")
    plt.show()
    plt.close(fig)
 
 
def plot_barras(by_algo, metrica, ylabel, titulo, filename):
    """Gera grafico de barras para uma metrica agregada.

    Args:
        by_algo: Resultados agrupados por algoritmo.
        metrica: Chave numerica usada para media.
        ylabel: Rotulo do eixo Y.
        titulo: Titulo da figura.
        filename: Nome do arquivo png de saida.
    """
    fig, ax = plt.subplots(figsize=(7, 5))
    algos  = list(by_algo.keys())
    medias = [np.mean([r[metrica] for r in by_algo[a]]) for a in algos]
 
    bars = ax.bar(
        [LABELS[a] for a in algos], medias,
        color=[CORES[a] for a in algos],
        edgecolor="white", width=0.5,
    )
    for bar, media in zip(bars, medias):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() * 1.02,
            f"{media:.2f}",
            ha="center", va="bottom", fontsize=12, fontweight="bold",
        )
 
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(titulo, fontsize=14, fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    save_and_show(fig, filename)
 
 
def plot_taxa_sucesso(by_algo):
    """Gera grafico de taxa de sucesso por algoritmo.

    Args:
        by_algo: Resultados agrupados por algoritmo.
    """
    fig, ax = plt.subplots(figsize=(7, 5))
    algos = list(by_algo.keys())
    taxas, labels_bar = [], []
 
    for algo in algos:
        subset = by_algo[algo]
        n = len(subset)
        s = sum(1 for r in subset if r["sucesso"])
        taxas.append(100 * s / n)
        labels_bar.append(f"{s}/{n}\n({100*s/n:.1f}%)")
 
    bars = ax.bar(
        [LABELS[a] for a in algos], taxas,
        color=[CORES[a] for a in algos],
        edgecolor="white", width=0.5,
    )
    for bar, lbl in zip(bars, labels_bar):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 1,
            lbl,
            ha="center", va="bottom", fontsize=11, fontweight="bold",
        )
 
    ax.set_ylim(0, 115)
    ax.set_ylabel("Taxa de Sucesso (%)", fontsize=12)
    ax.set_title("Taxa de Sucesso", fontsize=14, fontweight="bold")
    ax.axhline(100, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    save_and_show(fig, "1_taxa_sucesso.png")
 
 
def main():
    """Ponto de entrada para gerar todos os graficos do experimento legacy."""
    data    = load_results()
    by_algo = split_by_algo(data)
 
    print(f"\nAlgoritmos: {list(by_algo.keys())}")
    print("Gerando graficos...\n")
 
    plot_taxa_sucesso(by_algo)
 
    plot_barras(by_algo, "pontuação",          "Média de pontuação", " Média de pontuação",          "2_pontuação.png")
    plot_barras(by_algo, "tempo_s",        "Média de Tempo (s)",      "Média de Tempo",          "3_tempo.png")
    plot_barras(by_algo, "nos_expandidos", "Média de Nós Expandidos", "Média de Nós Expandidos", "4_nos.png")
    plot_barras(by_algo, "passos",         "Média de passos",        "Média de Passos",        "5_passos.png")
 
    print(f"\nGraficos salvos em '{OUTPUT_DIR}/'")
 
 
if __name__ == "__main__":
    main()