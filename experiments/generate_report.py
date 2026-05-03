"""
Gera results/report.html — visão agregada do CSV (taxa de sucesso, tempos médios de
execução, estados analisados) e tabela completa com destaque para falhas.

Uso (a partir da raiz do repositório):
    python3 experiments/generate_report.py
    python3 experiments/generate_report.py --input results/outro.csv
"""

from __future__ import annotations

import argparse
import csv
import html
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Descrições dos cenários de teste (códigos em experiment_slice; alinhado a run_batch.py)
SLICE_DESCRIPTIONS: dict[str, str] = {
    "baseline": (
        "Cenário de referência: vento ativo, zonas TNFZ (temporariamente restritas) e bateria inicial "
        "confortável — combina todos os efeitos do modelo."
    ),
    "no_wind": (
        "Sem vento: o mapa e demais regras iguais ao baseline, mas sem penalidade de vento no custo "
        "de movimento."
    ),
    "no_tnfz": (
        "Sem TNFZ: sem zonas temporariamente restritas; obstáculos fixos, vento e bateria como no baseline."
    ),
    "low_battery": (
        "Bateria inicial baixa: força paradas em estações de recarga com mais frequência (mesmo vento/TNFZ "
        "do baseline, salvo ajuste de bateria)."
    ),
}

ALGORITHM_DESCRIPTIONS: dict[str, str] = {
    "bfs": "Busca em largura (explora por camadas; não usa custo nem heurística).",
    "dfs": "Busca em profundidade (explora um ramo até o fim; pode ser rápida ou não encontrar solução ótima).",
    "ucs": "Custo uniforme (Dijkstra no grafo de estados; ótimo para custo de caminho).",
    "greedy": "Busca gulosa (expande o nó que parece mais promissor pela heurística).",
    "astar": "A* (combina custo acumulado e heurística; com heurística admissível tende a ser eficiente e ótimo).",
}

# Cores fixas por algoritmo (gráficos SVG — alinhado à paleta da demo 3D)
ALGO_CHART_COLORS: dict[str, str] = {
    "bfs": "#ffb347",
    "dfs": "#b39ddb",
    "ucs": "#64b5f6",
    "greedy": "#4dd0e1",
    "astar": "#81c784",
}

# Rótulos curtos para a coluna «Resumo da condição» na tabela detalhada
SLICE_SHORT_LABELS: dict[str, str] = {
    "baseline": "Referência: vento + TNFZ + bateria confortável",
    "no_wind": "Sem vento (resto como baseline)",
    "no_tnfz": "Sem zonas TNFZ (resto como baseline)",
    "low_battery": "Bateria inicial baixa (resto como baseline)",
}


def _float(s: str) -> float | None:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _bool(s: str) -> bool:
    return str(s).strip().lower() in ("true", "1", "yes")


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def aggregate(rows: list[dict[str, str]]):
    """Por algoritmo: sucessos, tempos de execução e estados analisados (média só com sucesso)."""
    by_algo = defaultdict(lambda: {"ok": 0, "n": 0, "times": [], "nodes": [], "costs": []})
    by_slice = defaultdict(lambda: {"ok": 0, "n": 0})
    for r in rows:
        a = r["algorithm"]
        by_algo[a]["n"] += 1
        if _bool(r["success"]):
            by_algo[a]["ok"] += 1
            t = _float(r["wall_time_sec"])
            if t is not None:
                by_algo[a]["times"].append(t)
            nv = int(r["visited_nodes"] or 0)
            by_algo[a]["nodes"].append(nv)
            pc = _float(str(r.get("path_cost", "")))
            if pc is not None:
                by_algo[a]["costs"].append(pc)
        sl = r.get("experiment_slice", "—")
        by_slice[sl]["n"] += 1
        if _bool(r["success"]):
            by_slice[sl]["ok"] += 1
    return by_algo, by_slice


def _avg(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _bar_svg(
    labels: list[str],
    values: list[float],
    title: str,
    unit: str,
    *,
    bar_colors: list[str] | None = None,
) -> str:
    """SVG horizontal com rótulos legíveis, coluna fixa para o valor e cor opcional por barra."""
    if not values:
        return f"<p class='muted'>Sem dados para «{title}».</p>"
    mx = max(values)
    if mx <= 0:
        mx = 1.0

    default_fill = "#4eb0ff"
    w = 720
    label_w = 108
    val_col_w = 138
    bar_x0 = label_w + 12
    bar_max = w - bar_x0 - val_col_w - 16
    h_bar, gap = 36, 12
    row_h = h_bar + gap
    total_h = 36 + len(values) * row_h + 16

    parts = [
        f'<svg class="chart" viewBox="0 0 {w} {total_h}" xmlns="http://www.w3.org/2000/svg">',
        f'<text x="0" y="22" class="chart-title">{title}</text>',
    ]
    y0 = 40
    for i, (lab, val) in enumerate(zip(labels, values)):
        y = y0 + i * row_h
        cy = y + h_bar // 2 + 5
        frac = val / mx
        bw = max(6, int(bar_max * frac))
        val_txt = f"{val:.2f}{unit}" if unit else f"{val:.2f}"
        fill = (
            bar_colors[i]
            if bar_colors is not None and i < len(bar_colors)
            else default_fill
        )
        lab_esc = html.escape(str(lab))
        parts.append(
            f'<text x="0" y="{cy}" class="lab">{lab_esc}</text>'
            f'<rect x="{bar_x0}" y="{y}" width="{bw}" height="{h_bar}" rx="5" '
            f'fill="{fill}" stroke="rgba(0,0,0,.35)" stroke-width="1"/>'
            f'<text x="{bar_x0 + bar_max + 12}" y="{cy}" class="val">{val_txt}</text>'
        )
    parts.append("</svg>")
    return "\n".join(parts)


def build_html(rows: list[dict[str, str]], by_algo, by_slice) -> str:
    algos = ["bfs", "dfs", "ucs", "greedy", "astar"]
    algo_colors = [ALGO_CHART_COLORS.get(a, "#4eb0ff") for a in algos]
    times = [_avg(by_algo[a]["times"]) for a in algos]
    nodes = [_avg(by_algo[a]["nodes"]) if by_algo[a]["nodes"] else 0 for a in algos]
    success_pct = [
        (100.0 * by_algo[a]["ok"] / by_algo[a]["n"]) if by_algo[a]["n"] else 0 for a in algos
    ]

    slice_rows = []
    for sl, d in sorted(by_slice.items()):
        desc = SLICE_DESCRIPTIONS.get(sl, "Cenário de teste não catalogado neste glossário.")
        desc_esc = html.escape(desc)
        pct = 100.0 * d["ok"] / d["n"] if d["n"] else 0.0
        slice_rows.append(
            "<tr>"
            f"<td><code>{html.escape(sl)}</code></td>"
            f"<td class='slice-desc'>{desc_esc}</td>"
            f"<td>{d['ok']}/{d['n']}</td>"
            f"<td><strong>{pct:.1f}%</strong></td>"
            "</tr>"
        )
    slice_rows_html = "".join(slice_rows)

    table_body = []
    for r in rows:
        ok = _bool(r["success"])
        row_cls = "row-ok" if ok else "row-fail"
        sl = r.get("experiment_slice", "—")
        slice_short = SLICE_SHORT_LABELS.get(sl, sl)
        slice_full = SLICE_DESCRIPTIONS.get(sl, "")
        algo = r["algorithm"]
        algo_title = ALGORITHM_DESCRIPTIONS.get(algo, "")
        slice_title = html.escape(slice_full, quote=True)
        algo_title_esc = html.escape(algo_title, quote=True)
        table_body.append(
            f"<tr class='{row_cls}'>"
            f"<td>{r['seed']}</td>"
            f"<td><code title='{slice_title}'>{html.escape(sl)}</code></td>"
            f"<td class='slice-desc' title='{slice_title}'>{html.escape(slice_short)}</td>"
            f"<td><code title='{algo_title_esc}'>{html.escape(algo)}</code></td>"
            f"<td>{'sim' if ok else 'não'}</td>"
            f"<td>{r.get('path_cost', '')}</td><td>{r.get('plan_length', '')}</td>"
            f"<td>{r.get('wall_time_sec', '')}</td><td>{r.get('visited_nodes', '')}</td>"
            f"<td>{r.get('timeout', '')}</td></tr>"
        )

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Resultados — Otimizando Rota de Drones</title>
  <style>
    :root {{
      --bg: #0f1419;
      --card: #1a2332;
      --text: #e7ecf3;
      --muted: #8b9cb3;
      --accent: #3d9cf0;
      --ok: #3ecf8e;
      --fail: #f06b6b;
    }}
    body {{
      font-family: "Segoe UI", system-ui, sans-serif;
      background: var(--bg);
      color: var(--text);
      margin: 0;
      padding: 24px 32px 48px;
      line-height: 1.5;
    }}
    h1 {{ font-size: 1.75rem; margin-bottom: 0.25rem; }}
    .sub {{ color: var(--muted); margin-bottom: 28px; }}
    /* Gráficos à parte da tabela de cenários: evita stretch à altura da tabela. */
    .charts-row {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 20px;
      align-items: start;
      margin-bottom: 24px;
    }}
    @media (max-width: 1100px) {{
      .charts-row {{ grid-template-columns: 1fr; }}
    }}
    @media (min-width: 701px) and (max-width: 1100px) {{
      .charts-row {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    }}
    .card {{
      background: var(--card);
      border-radius: 12px;
      padding: 20px 22px;
      border: 1px solid rgba(255,255,255,.06);
    }}
    .card-table {{
      margin-bottom: 32px;
    }}
    .card h2 {{ font-size: 1rem; margin: 0 0 12px; color: var(--accent); }}
    table.summary {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
    table.summary th, table.summary td {{
      text-align: left;
      padding: 8px 10px;
      border-bottom: 1px solid rgba(255,255,255,.08);
    }}
    table.summary th {{ color: var(--muted); font-weight: 600; }}
    .chart {{
      width: 100%;
      max-width: 100%;
      height: auto;
      display: block;
    }}
    .chart .lab {{ fill: #f2f6fc; font-size: 15px; font-weight: 600; }}
    .chart .val {{ fill: #ffffff; font-size: 14px; font-weight: 600; }}
    .chart-title {{ fill: #b8c9dc; font-size: 14px; font-weight: 600; }}
    .glossary {{
      background: var(--card);
      border-radius: 12px;
      padding: 20px 24px;
      margin-bottom: 28px;
      border: 1px solid rgba(255,255,255,.08);
    }}
    .glossary h2 {{ font-size: 1.05rem; margin: 0 0 14px; color: var(--accent); }}
    .glossary dl {{ margin: 0; }}
    .glossary dt {{ margin-top: 12px; font-weight: 700; color: var(--text); }}
    .glossary dt:first-child {{ margin-top: 0; }}
    .glossary dd {{ margin: 4px 0 0 0; color: var(--muted); max-width: 900px; }}
    .explain {{
      font-size: 0.92rem;
      color: var(--muted);
      margin: -12px 0 24px;
      max-width: 960px;
    }}
    table.summary td.slice-desc {{
      font-size: 0.82rem;
      color: #c5d2e3;
      line-height: 1.35;
    }}
    table.data td.slice-desc {{
      font-size: 0.78rem;
      color: #b9c8dc;
      max-width: 220px;
    }}
    .muted {{ color: var(--muted); }}
    .full {{
      overflow-x: auto;
      background: var(--card);
      border-radius: 12px;
      padding: 16px;
      border: 1px solid rgba(255,255,255,.06);
    }}
    table.data {{ width: 100%; border-collapse: collapse; font-size: 0.88rem; }}
    table.data th {{
      position: sticky;
      top: 0;
      background: #243044;
      padding: 10px 8px;
      text-align: left;
    }}
    table.data td {{ padding: 8px; border-bottom: 1px solid rgba(255,255,255,.05); }}
    tr.row-ok td:first-of-type {{ border-left: 3px solid var(--ok); }}
    tr.row-fail td:first-of-type {{ border-left: 3px solid var(--fail); }}
    .hint {{
      margin-top: 24px;
      padding: 14px 18px;
      background: rgba(61, 156, 240, .12);
      border-radius: 8px;
      border: 1px solid rgba(61, 156, 240, .35);
      font-size: 0.9rem;
    }}
  </style>
</head>
<body>
  <h1>Resultados dos algoritmos de busca</h1>
  <p class="sub">Gerado a partir do CSV de experimentos — use no relatório ou na apresentação.</p>

  <p class="explain">
    Os gráficos por <strong>algoritmo</strong> agregam <em>todos</em> os cenários de teste e seeds do CSV.
    A tabela <strong>Sucesso por cenário de teste</strong> mostra, para cada tipo de condição, quantas execuções
    encontraram um plano válido. Passe o cursor sobre os cabeçalhos da tabela grande ou sobre o código do cenário
    para ver descrições completas.
  </p>

  <section class="glossary">
    <h2>O que significa cada cenário de teste</h2>
    <dl>
      <dt><code>baseline</code></dt>
      <dd>{html.escape(SLICE_DESCRIPTIONS["baseline"])}</dd>
      <dt><code>no_wind</code></dt>
      <dd>{html.escape(SLICE_DESCRIPTIONS["no_wind"])}</dd>
      <dt><code>no_tnfz</code> (TNFZ = zona temporariamente restrita)</dt>
      <dd>{html.escape(SLICE_DESCRIPTIONS["no_tnfz"])}</dd>
      <dt><code>low_battery</code></dt>
      <dd>{html.escape(SLICE_DESCRIPTIONS["low_battery"])}</dd>
    </dl>
    <h2 style="margin-top:22px">Algoritmos (siglas na tabela)</h2>
    <dl>
      <dt><code>bfs</code></dt><dd>{html.escape(ALGORITHM_DESCRIPTIONS["bfs"])}</dd>
      <dt><code>dfs</code></dt><dd>{html.escape(ALGORITHM_DESCRIPTIONS["dfs"])}</dd>
      <dt><code>ucs</code></dt><dd>{html.escape(ALGORITHM_DESCRIPTIONS["ucs"])}</dd>
      <dt><code>greedy</code></dt><dd>{html.escape(ALGORITHM_DESCRIPTIONS["greedy"])}</dd>
      <dt><code>astar</code></dt><dd>{html.escape(ALGORITHM_DESCRIPTIONS["astar"])}</dd>
    </dl>
  </section>

  <div class="charts-row">
    <div class="card">
      <h2>Plano encontrado por algoritmo (% das execuções)</h2>
      {_bar_svg(algos, success_pct, "Plano encontrado (%)", "%", bar_colors=algo_colors)}
    </div>
    <div class="card">
      <h2>Tempo médio de execução (s) — só execuções com sucesso</h2>
      {_bar_svg(algos, times, "Tempo de execução (s)", " s", bar_colors=algo_colors)}
    </div>
    <div class="card">
      <h2>Estados analisados (média) — só com sucesso</h2>
      {_bar_svg(algos, nodes, "Estados analisados", "", bar_colors=algo_colors)}
    </div>
  </div>
  <div class="card card-table">
    <h2>Sucesso por cenário de teste</h2>
    <table class="summary">
      <thead><tr><th>Cenário (código)</th><th>O que muda na condição</th><th>Sucessos / total</th><th>%</th></tr></thead>
      <tbody>{slice_rows_html}</tbody>
    </table>
  </div>

  <h2 style="font-size:1.1rem;margin-bottom:12px;">Todas as execuções</h2>
  <div class="full">
    <table class="data">
      <thead>
        <tr>
          <th title="Identificador da instância pseudoaleatória">Seed</th>
          <th title="Código do cenário de teste (ver glossário)">Cenário (código)</th>
          <th title="Resumo em linguagem simples">Resumo da condição</th>
          <th title="Estratégia de busca (passe o cursor para descrição)">Algoritmo</th>
          <th title="Encontrou plano até o objetivo?">Plano encontrado</th>
          <th title="Custo total do plano (modelo tempo + energia)">Custo</th>
          <th title="Quantas ações compõem o plano">Nº de ações no plano</th>
          <th title="Tempo real que o computador levou a correr o algoritmo (segundos)">Tempo de execução (s)</th>
          <th title="Quantas situações do problema o algoritmo analisou durante a busca">Estados analisados</th>
          <th title="A execução parou porque atingiu o limite de tempo definido">Parou por limite de tempo</th>
        </tr>
      </thead>
      <tbody>{"".join(table_body)}</tbody>
    </table>
  </div>

  <p class="hint">
    <strong>Como abrir:</strong> abra <code>results/report.html</code> no navegador
    (duplo clique no ficheiro, ou <code>xdg-open results/report.html</code> no Linux,
    <code>open results/report.html</code> no macOS, <code>start results\\report.html</code> no Windows PowerShell).
  </p>
</body>
</html>"""


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, default=ROOT / "results" / "batch_runs.csv")
    p.add_argument("--output", type=Path, default=ROOT / "results" / "report.html")
    args = p.parse_args()

    if not args.input.is_file():
        print(f"Ficheiro não encontrado: {args.input}", file=sys.stderr)
        sys.exit(1)

    rows = load_rows(args.input)
    by_algo, by_slice = aggregate(rows)
    html = build_html(rows, by_algo, by_slice)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html, encoding="utf-8")
    print(f"Relatório escrito em {args.output}")


if __name__ == "__main__":
    main()
