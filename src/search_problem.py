"""Define o problema de busca do drone urbano para o `simpleai`."""

from __future__ import annotations

import math

from simpleai.search import SearchProblem

from src.environment import MOVES_6, UrbanInstance, manhattan

State = tuple[int, int, int, int, int]


class DroneUrbanSearchProblem(SearchProblem):
    """Implementa o `SearchProblem` para navegacao do drone.

    O estado e modelado como `(x, y, z, battery, t)` e o objetivo consiste em
    atingir a celula final com bateria suficiente para permanecer operacional.
    """

    def __init__(self, instance: UrbanInstance):
        """Inicializa o problema para uma instancia de ambiente.

        Args:
            instance: Instancia urbana com parametros de dinamica e mapa.
        """
        self.instance = instance
        x, y, z = instance.start
        self.initial_state = (x, y, z, instance.initial_battery, 0)
        self.goal_cell = instance.goal
        self._c_min_move = _compute_min_move_cost(instance)
        super().__init__(self.initial_state)

    def is_goal(self, state: State) -> bool:
        """Determina se o estado atende a condicao de objetivo.

        Args:
            state: Estado atual da busca.

        Returns:
            `True` quando a posicao coincide com o objetivo e bateria >= 1.
        """
        x, y, z, b, _t = state
        return (x, y, z) == self.goal_cell and b >= 1

    def heuristic(self, state: State) -> float:
        """Estima custo restante com Manhattan e custo minimo por movimento.

        Args:
            state: Estado avaliado pela heuristica.

        Returns:
            Estimativa admissivel de custo ate o objetivo.
        """
        x, y, z, _b, _t = state
        dist = manhattan((x, y, z), self.goal_cell)
        return float(dist) * self._c_min_move

    def actions(self, state: State):
        """Lista acoes validas no estado atual.

        Args:
            state: Estado atual da busca.

        Returns:
            Lista de acoes possiveis (`wait`, `move`, `recharge`) respeitando
            limites de tempo, bateria e restricoes do ambiente.
        """
        inst = self.instance
        x, y, z, b, t = state
        acts = []

        if t + 1 <= inst.time_horizon:
            if not inst.is_forbidden(x, y, z, t + 1):
                nb = b - inst.hover_battery
                if nb >= 1:
                    acts.append(("wait",))

        if t + 1 <= inst.time_horizon:
            for dx, dy, dz in MOVES_6:
                nx, ny, nz = x + dx, y + dy, z + dz
                if not inst.in_bounds(nx, ny, nz) or inst.is_obstacle(nx, ny, nz):
                    continue
                if inst.is_forbidden(nx, ny, nz, t + 1):
                    continue
                drain = _move_battery_drain(inst, dx, dy, dz, nx, ny, nz)
                if b - drain >= 1:
                    acts.append(("move", dx, dy, dz))

        if (x, y, z) in inst.stations:
            rt = inst.recharge_duration
            if t + rt <= inst.time_horizon:
                if not any(
                    inst.is_forbidden(x, y, z, tau) for tau in range(t + 1, t + rt + 1)
                ):
                    acts.append(("recharge",))

        return acts

    def result(self, state: State, action) -> State:
        """Aplica uma acao ao estado e retorna o estado sucessor.

        Args:
            state: Estado atual.
            action: Acao retornada por `actions`.

        Returns:
            Novo estado apos executar a acao.

        Raises:
            ValueError: Quando a acao informada e desconhecida.
        """
        inst = self.instance
        x, y, z, b, t = state
        kind = action[0]
        if kind == "wait":
            return (x, y, z, b - inst.hover_battery, t + 1)
        if kind == "move":
            _k, dx, dy, dz = action
            nx, ny, nz = x + dx, y + dy, z + dz
            drain = _move_battery_drain(inst, dx, dy, dz, nx, ny, nz)
            return (nx, ny, nz, b - drain, t + 1)
        if kind == "recharge":
            rt = inst.recharge_duration
            return (x, y, z, inst.battery_max, t + rt)
        raise ValueError(f"Acao desconhecida: {action}")

    def cost(self, state: State, action, state2: State) -> float:
        """Calcula custo ponderado de transicao tempo + energia.

        Args:
            state: Estado de origem.
            action: Acao executada.
            state2: Estado resultante.

        Returns:
            Custo escalar da transicao.

        Raises:
            ValueError: Quando a acao informada e desconhecida.
        """
        inst = self.instance
        kind = action[0]
        if kind == "wait":
            dt = 1.0
            de = float(inst.hover_battery)
            return inst.w_time * dt + inst.w_energy * de
        if kind == "move":
            _k, dx, dy, dz = action
            x, y, z, _b, _t = state
            nx, ny, nz = x + dx, y + dy, z + dz
            dt, de = _move_time_energy(inst, dx, dy, dz, nx, ny, nz)
            return inst.w_time * dt + inst.w_energy * de
        if kind == "recharge":
            rt = inst.recharge_duration
            dt = float(rt)
            de = float(inst.recharge_idle_battery * rt)
            return inst.w_time * dt + inst.w_energy * de
        raise ValueError(f"Acao desconhecida: {action}")

    def value(self, state: State) -> float:
        """Retorna valor neutro para compatibilidade com API do simpleai.

        Args:
            state: Estado atual.

        Returns:
            Sempre `0.0`.
        """
        return 0.0


def _wind_opposing(
    inst: UrbanInstance, dx: int, dy: int, dz: int, nx: int, ny: int, nz: int
) -> float:
    """Calcula oposicao do vento ao vetor de movimento.

    Args:
        inst: Instancia com campo de vento.
        dx: Delta de movimento no eixo X.
        dy: Delta de movimento no eixo Y.
        dz: Delta de movimento no eixo Z.
        nx: Coordenada X de destino.
        ny: Coordenada Y de destino.
        nz: Coordenada Z de destino.

    Returns:
        Intensidade escalar nao negativa de oposicao ao movimento.
    """
    w = inst.wind.get((nx, ny, nz), (0, 0, 0))
    dot = w[0] * dx + w[1] * dy + w[2] * dz
    return float(max(0, -dot))


def _move_time_energy(
    inst: UrbanInstance, dx: int, dy: int, dz: int, nx: int, ny: int, nz: int
) -> tuple[float, float]:
    """Calcula tempo e energia de um movimento.

    Para movimento horizontal com vento contrário (``opp > 0``), soma-se
    ``inst.wind_cost`` à energia — equivalente numérico a ``WIND_COST`` em
    ``legacy/astas3d.py`` (penalidade fixa extra além de ``wind_energy_scale``).

    Args:
        inst: Instancia com parametros de custo.
        dx: Delta de movimento no eixo X.
        dy: Delta de movimento no eixo Y.
        dz: Delta de movimento no eixo Z.
        nx: Coordenada X de destino.
        ny: Coordenada Y de destino.
        nz: Coordenada Z de destino.

    Returns:
        Tupla `(dt, de)` com tempo e energia consumidos.
    """
    opp = _wind_opposing(inst, dx, dy, dz, nx, ny, nz)
    dt = 1.0 + inst.wind_time_scale * opp
    de = float(inst.move_battery_base) + inst.wind_energy_scale * opp
    if dz == 0 and (dx != 0 or dy != 0) and opp > 0:
        de += inst.wind_cost
    return dt, de


def _move_battery_drain(
    inst: UrbanInstance, dx: int, dy: int, dz: int, nx: int, ny: int, nz: int
) -> int:
    """Converte o custo energetico de movimento em consumo inteiro de bateria.

    Args:
        inst: Instancia com parametros de custo.
        dx: Delta de movimento no eixo X.
        dy: Delta de movimento no eixo Y.
        dz: Delta de movimento no eixo Z.
        nx: Coordenada X de destino.
        ny: Coordenada Y de destino.
        nz: Coordenada Z de destino.

    Returns:
        Consumo inteiro de bateria para o movimento.
    """
    _dt, de = _move_time_energy(inst, dx, dy, dz, nx, ny, nz)
    return int(math.ceil(de))


def _compute_min_move_cost(inst: UrbanInstance) -> float:
    """Computa o menor custo de movimento unitario possivel na instancia.

    Args:
        inst: Instancia urbana usada para varrer movimentos validos.

    Returns:
        Menor custo observado para um passo. Usa `1.0` como fallback quando
        nao houver movimentos disponiveis.
    """
    best = None
    for x in range(inst.nx):
        for y in range(inst.ny):
            for z in range(inst.nz):
                if inst.is_obstacle(x, y, z):
                    continue
                for dx, dy, dz in MOVES_6:
                    nx, ny, nz = x + dx, y + dy, z + dz
                    if not inst.in_bounds(nx, ny, nz) or inst.is_obstacle(nx, ny, nz):
                        continue
                    dt, de = _move_time_energy(inst, dx, dy, dz, nx, ny, nz)
                    c = inst.w_time * dt + inst.w_energy * de
                    if best is None or c < best:
                        best = c
    return float(best if best is not None else 1.0)
