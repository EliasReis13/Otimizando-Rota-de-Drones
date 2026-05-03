# Otimizando-Rota-de-Drones

Projeto de planejamento de rota para drone em grade 3D com restrições de tempo, bateria, vento, obstáculos fixos, estações de recarga e zonas de exclusão temporária (TNFZ). O núcleo usa `simpleai` (`SearchProblem`) e compara **BFS**, **DFS**, **UCS**, **busca gulosa** e **A\***.

**Implementação final (âmbito da entrega):** [src/](src/) e [experiments/](experiments/), mais os artefactos gerados em [results/](results/) (CSV, HTML). O diretório [legacy/](legacy/) contém **apenas código legado** (não entra na implementação final); [scripts/](scripts/) reúne pontos de entrada opcionais (demos) que podem invocar esse legado, por exemplo para visualização.

## Estrutura do repositório

| Caminho | Função |
|--------|--------|
| [src/](src/) | Biblioteca principal: ambiente (`UrbanInstance`), problema de busca (`DroneUrbanSearchProblem`), execução dos algoritmos e métricas. |
| [experiments/](experiments/) | Pipeline do trabalho: lote reprodutível, relatório HTML; inclui atalho para a demo Pygame. |
| [scripts/](scripts/) | Demos opcionais (ex.: [scripts/arena_pygame.py](scripts/arena_pygame.py) — arena visual que usa `legacy/`). |
| [legacy/](legacy/) | Código legado: arena Pygame (`astas3d.py`), benchmark antigo em lote e `plot_results.py`. Fora do âmbito da implementação final. |
| [results/](results/) | Saídas do pipeline moderno (`batch_runs.csv`, `report.html`, etc.). |
| [results/legacy/](results/legacy/) | Ficheiros produzidos pelos scripts legados (métricas da arena, JSON do benchmark, gráficos). |
| [arena.py](arena.py) | Atalho na raiz para a demo da arena (delega para [scripts/arena_pygame.py](scripts/arena_pygame.py)). |

Fluxo lógico do núcleo `src/`:

1. [src/environment.py](src/environment.py): gera instâncias (`UrbanInstance`) com mapa, vento, TNFZ e estações.
2. [src/search_problem.py](src/search_problem.py): estados, ações, custo e heurística admissível.
3. [src/runners.py](src/runners.py): executa os algoritmos e recolhe métricas.
4. [experiments/run_batch.py](experiments/run_batch.py): lote de instâncias e exportação CSV.
5. [experiments/generate_report.py](experiments/generate_report.py): gera o relatório HTML a partir do CSV.

## Algoritmos: código vs documentação

### O que este repositório executa

**Núcleo principal (`simpleai` em `src/`):** em [src/runners.py](src/runners.py) estão expostos cinco algoritmos usados nos experimentos em lote:

- **BFS** (`breadth_first`)
- **DFS** (`depth_first`)
- **UCS** (`uniform_cost`, custo uniforme)
- **Busca gulosa** (`greedy`)
- **A\*** (`astar`)

**Demo Pygame (legado, fora do núcleo final):** em [legacy/astas3d.py](legacy/astas3d.py) o planejador usa `astar` ou `greedy`. [scripts/arena_pygame.py](scripts/arena_pygame.py) (e [arena.py](arena.py)) abrem primeiro uma **janela de escolha** entre A* e busca gulosa; opcionalmente `--algorithm` / `-a` salta esse menu (útil em scripts). [legacy/run.py](legacy/run.py) compara em lote `astar` e `greedy` no modelo antigo.

### O que o enunciado em `docs/request.pdf` deixa explícito (texto)

No PDF [docs/request.pdf](docs/request.pdf) (camada de texto extraível), consta:

- Heurística para **busca gulosa** e **A\***, com justificativa de **admissibilidade**.
- **Resultados comparativos** entre **diferentes estratégias de busca**.
- Execução do **conjunto de algoritmos obrigatórios** em número suficiente de instâncias (referência da ordem de **pelo menos 50**).

Nessa extração textual **não há lista nominal** do conjunto obrigatório (por exemplo, não aparecem explicitamente BFS, DFS e UCS no texto recuperado). Para a lista completa, use a versão visual do PDF, material de aula ou orientação docente, se existir.

## Requisitos

- Python 3.10 ou superior
- Dependências em [requirements.txt](requirements.txt)

---

## Passo a passo

Siga os passos **na ordem** da primeira utilização; depois pode saltar para o que precisar.

### 1. Clonar e entrar na pasta do projeto

```bash
git clone <url-do-repositório>
cd Otimizando-Rota-de-Drones
```

### 2. Criar e ativar um ambiente virtual

**Linux / macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell)**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

Mantenha o ambiente virtual **ativo** nos passos seguintes.

### 4. (Opcional) Arena visual Pygame

Demo sobre o código **legado** (ritmo e água configuráveis no topo de [scripts/arena_pygame.py](scripts/arena_pygame.py)). Ao iniciar, abre-se uma **janela Pygame** para escolher **A\*** ou **busca gulosa**. **Depois de terminar a rota** (vitória ou fim de jogo): **R** reinicia com o mesmo algoritmo; **M** ou **N** voltam ao menu para escolher outro algoritmo; **ESC** fecha.

```bash
python3 arena.py
```

Equivalente:

```bash
python3 scripts/arena_pygame.py
```

Para **saltar o menu** e fixar o algoritmo (automação / terminal):

```bash
python3 scripts/arena_pygame.py --algorithm greedy
python3 arena.py -a astar
```

Para **BFS, DFS, UCS** e comparação dos cinco algoritmos no modelo do trabalho, use o lote em [experiments/run_batch.py](experiments/run_batch.py) (não estão ligados à arena Pygame).

Métricas opcionais da sessão são acrescentadas a [results/legacy/arena_metrics.csv](results/legacy/arena_metrics.csv).

Atalho a partir de `experiments/`:

```bash
python3 experiments/demo_compare_3d.py
python3 experiments/demo_compare_3d.py --algorithm greedy
```

### 5. Experimento em lote (cinco algoritmos, ≥50 instâncias)

Gera CSV com quatro cenários de teste (`baseline`, `no_wind`, `no_tnfz`, `low_battery`):

```bash
python3 experiments/run_batch.py
```

Ficheiro por omissão: [results/batch_runs.csv](results/batch_runs.csv).

Opções úteis:

```bash
python3 experiments/run_batch.py --output results/outro.csv --timeout 45
```

`--timeout` é o tempo máximo de execução (relógio real), em segundos, por algoritmo e por instância.

### 6. Relatório HTML

Depois de existir um CSV (por exemplo o do passo 5):

```bash
python3 experiments/generate_report.py
```

Saída por omissão: [results/report.html](results/report.html).

Outro ficheiro de entrada:

```bash
python3 experiments/generate_report.py --input results/outro.csv
```

Abrir no navegador:

- Linux: `xdg-open results/report.html`
- macOS: `open results/report.html`
- Windows (PowerShell): `start results\\report.html`

### 7. (Opcional) Benchmark legado em lote e gráficos

Fora da implementação final: caminho longo e dependente de Pygame; gera JSON em `results/legacy/`:

```bash
python3 legacy/run.py
```

Depois de existir [results/legacy/benchmark.json](results/legacy/benchmark.json):

```bash
python3 legacy/plot_results.py
```

As figuras PNG ficam em [results/legacy/graficos/](results/legacy/graficos/).

---