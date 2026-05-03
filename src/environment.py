"""
Gera um “cenário” fixo por seed: grelha 3D, obstáculos, vento por célula, estações
de recarga e cubos TNFZ (proibido voar ali entre os instantes t0 e t1).
Não faz busca — só descreve o mapa (dataclass UrbanInstance).
"""

from __future__ import annotations

import random
from dataclasses import dataclass


Cell = tuple[int, int, int]
WindVec = tuple[int, int, int]

# Penalidade fixa extra com vento contrário (mov. horizontal), alinhada a legacy/astas3d.WIND_COST.
WIND_COST = 3.0


@dataclass(frozen=True)
class TNFZRegion:
    """Representa uma regiao TNFZ ativa em uma janela temporal.

    A regiao e um cubo inclusivo definido por limites em `x`, `y` e `z`.
    Ela bloqueia apenas quando `t0 <= t < t1`.
    """

    x0: int
    x1: int
    y0: int
    y1: int
    z0: int
    z1: int
    t0: int
    t1: int

    def blocks(self, x: int, y: int, z: int, t: int) -> bool:
        """Indica se a celula esta bloqueada na coordenada temporal.

        Args:
            x: Coordenada X da celula consultada.
            y: Coordenada Y da celula consultada.
            z: Coordenada Z da celula consultada.
            t: Instante discreto da simulacao.

        Returns:
            `True` quando a celula esta dentro do cubo e a regiao esta ativa.
        """
        if t < self.t0 or t >= self.t1:
            return False
        return (
            self.x0 <= x <= self.x1
            and self.y0 <= y <= self.y1
            and self.z0 <= z <= self.z1
        )


@dataclass
class UrbanInstance:
    """Agrupa ambiente e parametros de dinamica para um episodio de busca."""

    nx: int
    ny: int
    nz: int
    obstacles: frozenset[Cell]
    wind: dict[Cell, WindVec]
    stations: frozenset[Cell]
    tnfz_regions: tuple[TNFZRegion, ...]
    start: Cell
    goal: Cell
    battery_max: int
    initial_battery: int
    time_horizon: int
    recharge_duration: int
    hover_battery: int
    move_battery_base: int
    w_time: float
    w_energy: float
    wind_time_scale: float
    wind_energy_scale: float
    wind_cost: float
    recharge_idle_battery: int
    experiment_slice: str = ""

    def in_bounds(self, x: int, y: int, z: int) -> bool:
        """Valida se a celula pertence aos limites da grade.

        Args:
            x: Coordenada X da celula.
            y: Coordenada Y da celula.
            z: Coordenada Z da celula.

        Returns:
            `True` quando a celula esta dentro dos limites da instancia.
        """
        return 0 <= x < self.nx and 0 <= y < self.ny and 0 <= z < self.nz

    def is_obstacle(self, x: int, y: int, z: int) -> bool:
        """Verifica se a celula e um obstaculo fixo.

        Args:
            x: Coordenada X da celula.
            y: Coordenada Y da celula.
            z: Coordenada Z da celula.

        Returns:
            `True` quando a celula pertence ao conjunto de obstaculos.
        """
        return (x, y, z) in self.obstacles

    def is_forbidden(self, x: int, y: int, z: int, t: int) -> bool:
        """Verifica se a celula esta proibida no instante informado.

        Args:
            x: Coordenada X da celula.
            y: Coordenada Y da celula.
            z: Coordenada Z da celula.
            t: Instante discreto de simulacao.

        Returns:
            `True` quando a celula esta fora da grade, em obstaculo, ou
            bloqueada por alguma regiao TNFZ ativa no instante `t`.
        """
        if not self.in_bounds(x, y, z) or self.is_obstacle(x, y, z):
            return True
        for r in self.tnfz_regions:
            if r.blocks(x, y, z, t):
                return True
        return False


MOVES_6 = (
    (1, 0, 0),
    (-1, 0, 0),
    (0, 1, 0),
    (0, -1, 0),
    (0, 0, 1),
    (0, 0, -1),
)


def _tnfz_overlaps_station(reg: TNFZRegion, stations: set[Cell]) -> bool:
    """Verifica se uma regiao TNFZ cobre alguma estacao.

    Args:
        reg: Regiao TNFZ candidata.
        stations: Estacoes fixas da instancia.

    Returns:
        `True` quando ao menos uma estacao esta dentro da regiao.
    """
    for sx, sy, sz in stations:
        if (
            reg.x0 <= sx <= reg.x1
            and reg.y0 <= sy <= reg.y1
            and reg.z0 <= sz <= reg.z1
        ):
            return True
    return False


def generate_instance(
    seed: int,
    *,
    nx: int = 5,
    ny: int = 5,
    nz: int = 3,
    obstacle_density: float = 0.12,
    num_stations: int = 2,
    num_tnfz: int = 1,
    with_wind: bool = True,
    with_tnfz: bool = True,
    low_battery: bool = False,
    time_horizon: int = 48,
    max_attempts: int = 80,
    experiment_slice: str = "",
) -> UrbanInstance:
    """Gera uma instancia pseudoaleatoria reproduzivel e valida.

    Args:
        seed: Semente para reproducao da instancia.
        nx: Tamanho no eixo X.
        ny: Tamanho no eixo Y.
        nz: Tamanho no eixo Z.
        obstacle_density: Densidade alvo de obstaculos fixos.
        num_stations: Quantidade de estacoes de recarga.
        num_tnfz: Quantidade de regioes TNFZ.
        with_wind: Se deve gerar campo de vento.
        with_tnfz: Se deve gerar regioes TNFZ.
        low_battery: Se deve reduzir autonomia inicial.
        time_horizon: Horizonte temporal maximo da simulacao.
        max_attempts: Numero maximo de tentativas de geracao valida.
        experiment_slice: Rotulo da fatia experimental para rastreio.

    Returns:
        Instancia valida pronta para uso pelos algoritmos de busca.

    Raises:
        RuntimeError: Quando nenhuma instancia valida e encontrada no limite.
    """
    rng = random.Random(seed)
    for _ in range(max_attempts):
        inst = _try_build(
            rng,
            nx=nx,
            ny=ny,
            nz=nz,
            obstacle_density=obstacle_density,
            num_stations=num_stations,
            num_tnfz=num_tnfz if with_tnfz else 0,
            with_wind=with_wind,
            low_battery=low_battery,
            time_horizon=time_horizon,
            experiment_slice=experiment_slice,
        )
        if inst is not None:
            return inst
    raise RuntimeError(f"Falha ao gerar instância válida após {max_attempts} tentativas (seed={seed})")


def _try_build(
    rng: random.Random,
    *,
    nx: int,
    ny: int,
    nz: int,
    obstacle_density: float,
    num_stations: int,
    num_tnfz: int,
    with_wind: bool,
    low_battery: bool,
    time_horizon: int,
    experiment_slice: str,
) -> UrbanInstance | None:
    """Tenta construir uma instancia unica.

    Args:
        rng: Gerador pseudoaleatorio local.
        nx: Tamanho no eixo X.
        ny: Tamanho no eixo Y.
        nz: Tamanho no eixo Z.
        obstacle_density: Densidade alvo de obstaculos fixos.
        num_stations: Quantidade de estacoes de recarga.
        num_tnfz: Quantidade de regioes TNFZ.
        with_wind: Se deve gerar vento por celula.
        low_battery: Se usa configuracao de bateria reduzida.
        time_horizon: Horizonte temporal da simulacao.
        experiment_slice: Rotulo da fatia experimental.

    Returns:
        `UrbanInstance` quando a configuracao resultante e valida; `None` caso
        viole conectividade minima entre inicio e objetivo.
    """
    cells = [(x, y, z) for x in range(nx) for y in range(ny) for z in range(nz)]
    obstacles = set()
    for c in cells:
        if rng.random() < obstacle_density:
            obstacles.add(c)

    start = (0, 0, 0)
    goal = (nx - 1, ny - 1, 0)
    for c in (start, goal):
        obstacles.discard(c)

    if _blocks_path_3d(nx, ny, nz, frozenset(obstacles), start, goal):
        return None

    stations: set[Cell] = set()
    attempts = 0
    while len(stations) < num_stations and attempts < 200:
        attempts += 1
        c = (rng.randrange(nx), rng.randrange(ny), rng.randrange(nz))
        if c in obstacles or c in (start, goal):
            continue
        stations.add(c)

    wind: dict[Cell, WindVec] = {}
    if with_wind:
        for c in cells:
            if c in obstacles:
                continue
            wind[c] = (
                rng.randint(-1, 1),
                rng.randint(-1, 1),
                rng.randint(-1, 1),
            )

    tnfz_list: list[TNFZRegion] = []
    for _ in range(num_tnfz):
        w = rng.randint(1, 2)
        hx = rng.randint(0, max(0, nx - w))
        hy = rng.randint(0, max(0, ny - w))
        hz = rng.randint(0, max(0, nz - 1))
        t0 = rng.randint(2, max(3, time_horizon // 3))
        dt = rng.randint(3, max(4, time_horizon // 2))
        reg = TNFZRegion(hx, hx + w - 1, hy, hy + w - 1, hz, hz, t0, min(t0 + dt, time_horizon - 1))
        if (goal[0], goal[1], goal[2]) in [
            (x, y, z)
            for x in range(reg.x0, reg.x1 + 1)
            for y in range(reg.y0, reg.y1 + 1)
            for z in range(reg.z0, reg.z1 + 1)
        ]:
            continue
        if _tnfz_overlaps_station(reg, stations):
            continue
        tnfz_list.append(reg)

    battery_max = 10 if low_battery else 16
    initial_battery = 4 if low_battery else 12

    return UrbanInstance(
        nx=nx,
        ny=ny,
        nz=nz,
        obstacles=frozenset(obstacles),
        wind=wind,
        stations=frozenset(stations),
        tnfz_regions=tuple(tnfz_list),
        start=start,
        goal=goal,
        battery_max=battery_max,
        initial_battery=initial_battery,
        time_horizon=time_horizon,
        recharge_duration=3,
        hover_battery=1,
        move_battery_base=2,
        w_time=1.0,
        w_energy=0.5,
        wind_time_scale=0.35,
        wind_energy_scale=0.45,
        wind_cost=WIND_COST,
        recharge_idle_battery=1,
        experiment_slice=experiment_slice,
    )


def _blocks_path_3d(
    nx: int, ny: int, nz: int, obstacles: frozenset[Cell], start: Cell, goal: Cell
) -> bool:
    """Testa conectividade espacial minima ignorando tempo e bateria.

    Args:
        nx: Tamanho no eixo X.
        ny: Tamanho no eixo Y.
        nz: Tamanho no eixo Z.
        obstacles: Obstaculos fixos.
        start: Celula inicial.
        goal: Celula de objetivo.

    Returns:
        `True` quando nao existe caminho 6-vizinho entre `start` e `goal`.
    """
    if start in obstacles or goal in obstacles:
        return True
    q = [start]
    seen = {start}
    head = 0
    while head < len(q):
        x, y, z = q[head]
        head += 1
        if (x, y, z) == goal:
            return False
        for dx, dy, dz in MOVES_6:
            nx_, ny_, nz_ = x + dx, y + dy, z + dz
            if not (0 <= nx_ < nx and 0 <= ny_ < ny and 0 <= nz_ < nz):
                continue
            nb = (nx_, ny_, nz_)
            if nb in obstacles or nb in seen:
                continue
            seen.add(nb)
            q.append(nb)
    return True


def manhattan(a: Cell, b: Cell) -> int:
    """Calcula distancia Manhattan entre duas celulas 3D.

    Args:
        a: Celula de origem.
        b: Celula de destino.

    Returns:
        Distancia Manhattan entre `a` e `b`.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])
