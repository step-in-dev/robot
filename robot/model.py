from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, Literal, TypeVar

from .i18n import t


Direction = Literal["up", "down", "left", "right"]
CellType = TypeVar("CellType", bound="Cell")


class RobotError(Exception):
    """Base exception for robot runtime errors."""


class RobotPathError(RobotError):
    """Raised when the robot tries to move through a wall or field border."""


@dataclass(frozen=True)
class Cell:
    r: int
    c: int


@dataclass(frozen=True)
class ValuedCell(Cell):
    value: int


@dataclass
class RobotEnvDto:
    width: int
    height: int
    start_row: int
    start_col: int
    final_row: int
    final_col: int
    walls: list[tuple[Cell, Cell]] = field(default_factory=list)
    painted_cells: list[Cell] = field(default_factory=list)
    cells_to_paint: list[Cell] = field(default_factory=list)
    polluted_cells: list[ValuedCell] = field(default_factory=list)
    cells_to_print: list[ValuedCell] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "RobotEnvDto":
        try:
            dto = cls(
                width=int(data["width"]),
                height=int(data["height"]),
                start_row=int(data["startRow"]),
                start_col=int(data["startCol"]),
                final_row=int(data["finalRow"]),
                final_col=int(data["finalCol"]),
                walls=[
                    (cell_from_dict(wall[0]), cell_from_dict(wall[1]))
                    for wall in data.get("walls", [])
                    if isinstance(wall, list) and len(wall) == 2
                ],
                painted_cells=[
                    cell_from_dict(cell) for cell in data.get("paintedCells", [])
                ],
                cells_to_paint=[
                    cell_from_dict(cell) for cell in data.get("cellsToPaint", [])
                ],
                polluted_cells=[
                    valued_cell_from_dict(cell)
                    for cell in data.get("pollutedCells", [])
                ],
                cells_to_print=[
                    valued_cell_from_dict(cell)
                    for cell in data.get("cellsToPrint", [])
                ],
            )
        except KeyError as exc:
            raise ValueError(
                t("model.error.missing_env_field", field=exc.args[0])
            ) from exc
        except (TypeError, ValueError) as exc:
            raise ValueError(t("model.error.invalid_env_format")) from exc

        return dto.normalized()

    def normalized(self) -> "RobotEnvDto":
        painted_cells = deduplicate_cells(self.painted_cells)
        cells_to_paint = [
            cell
            for cell in deduplicate_cells(self.cells_to_paint)
            if cell not in painted_cells
        ]

        return RobotEnvDto(
            width=self.width,
            height=self.height,
            start_row=self.start_row,
            start_col=self.start_col,
            final_row=self.final_row,
            final_col=self.final_col,
            walls=[
                (first, second)
                for first, second in self.walls
                if is_valid_wall(first, second)
            ],
            painted_cells=painted_cells,
            cells_to_paint=cells_to_paint,
            polluted_cells=deduplicate_cells(self.polluted_cells),
            cells_to_print=deduplicate_cells(self.cells_to_print),
        )


class RobotEnv:
    def __init__(self, dto: RobotEnvDto):
        self._dto = dto.normalized()
        self._listeners: list[Callable[[], None]] = []
        self._newly_painted_cells: list[Cell] = []
        self._printed_cells: list[ValuedCell] = []
        self._robot = Robot(self, self._notify_listeners)

    @property
    def robot(self) -> "Robot":
        return self._robot

    @property
    def width(self) -> int:
        return self._dto.width

    @property
    def height(self) -> int:
        return self._dto.height

    @property
    def start_row(self) -> int:
        return self._dto.start_row

    @property
    def start_col(self) -> int:
        return self._dto.start_col

    @property
    def final_row(self) -> int:
        return self._dto.final_row

    @property
    def final_col(self) -> int:
        return self._dto.final_col

    @property
    def walls(self) -> tuple[tuple[Cell, Cell], ...]:
        return tuple(self._dto.walls)

    @property
    def painted_cells(self) -> tuple[Cell, ...]:
        return tuple(self._dto.painted_cells)

    @property
    def cells_to_paint(self) -> tuple[Cell, ...]:
        return tuple(self._dto.cells_to_paint)

    @property
    def polluted_cells(self) -> tuple[ValuedCell, ...]:
        return tuple(self._dto.polluted_cells)

    @property
    def cells_to_print(self) -> tuple[ValuedCell, ...]:
        return tuple(self._dto.cells_to_print)

    @property
    def printed_cells(self) -> tuple[ValuedCell, ...]:
        return tuple(self._printed_cells)

    def add_listener(self, listener: Callable[[], None]) -> None:
        self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[], None]) -> None:
        self._listeners.remove(listener)

    def extract_painted_cells(self) -> tuple[Cell, ...]:
        return tuple(self._newly_painted_cells + self._dto.painted_cells)

    def paint(self, cell: Cell) -> None:
        self._newly_painted_cells.append(cell)

    def is_painted(self, cell: Cell) -> bool:
        return cell in self._newly_painted_cells or cell in self._dto.painted_cells

    def get_pollution_level(self, cell: Cell) -> int:
        for polluted_cell in self._dto.polluted_cells:
            if same_position(polluted_cell, cell):
                return polluted_cell.value
        return 0

    def print_number(self, cell: ValuedCell) -> None:
        self._printed_cells = [
            printed_cell
            for printed_cell in self._printed_cells
            if not same_position(printed_cell, cell)
        ]
        self._printed_cells.append(cell)

    def reset(self) -> None:
        self._newly_painted_cells = []
        self._printed_cells = []
        self._robot.reset()

    def is_in_final_state(self) -> bool:
        return (
            self._robot.row == self.final_row
            and self._robot.col == self.final_col
            and self._are_right_cells_painted()
            and self._is_every_number_printed_correctly()
        )

    def _are_right_cells_painted(self) -> bool:
        number_of_found = 0
        for cell in self.cells_to_paint:
            count = count_positions(cell, self._newly_painted_cells)
            number_of_found += count
            if count == 0:
                return False

        for cell in self.painted_cells:
            number_of_found += count_positions(cell, self._newly_painted_cells)

        return number_of_found == len(self._newly_painted_cells)

    def _is_every_number_printed_correctly(self) -> bool:
        if len(self.cells_to_print) != len(self._printed_cells):
            return False

        return all(
            any(
                same_position(printed_cell, expected_cell)
                and printed_cell.value == expected_cell.value
                for printed_cell in self._printed_cells
            )
            for expected_cell in self.cells_to_print
        )

    def _notify_listeners(self) -> None:
        for listener in self._listeners:
            listener()


class Robot:
    def __init__(self, env: RobotEnv, change_listener: Callable[[], None]):
        self._env = env
        self._change_listener = change_listener
        self._row = env.start_row
        self._col = env.start_col
        self._walls = self._create_wall_hash_table()

    @property
    def row(self) -> int:
        return self._row

    @property
    def col(self) -> int:
        return self._col

    def reset(self) -> None:
        self._row = self._env.start_row
        self._col = self._env.start_col
        self._walls = self._create_wall_hash_table()
        self._change_listener()

    def move_right(self) -> None:
        self._assert_there_is_way_to(self._row, self._col + 1)
        self._col += 1
        self._change_listener()

    def move_left(self) -> None:
        self._assert_there_is_way_to(self._row, self._col - 1)
        self._col -= 1
        self._change_listener()

    def move_up(self) -> None:
        self._assert_there_is_way_to(self._row - 1, self._col)
        self._row -= 1
        self._change_listener()

    def move_down(self) -> None:
        self._assert_there_is_way_to(self._row + 1, self._col)
        self._row += 1
        self._change_listener()

    def paint(self) -> None:
        self._env.paint(Cell(self._row, self._col))
        self._change_listener()

    def is_cell_painted(self) -> bool:
        return self._env.is_painted(Cell(self._row, self._col))

    def is_wall_from(self, direction: Direction) -> bool:
        if direction == "right":
            return self._is_there_way_to(self._row, self._col + 1)
        if direction == "left":
            return self._is_there_way_to(self._row, self._col - 1)
        if direction == "up":
            return self._is_there_way_to(self._row - 1, self._col)
        if direction == "down":
            return self._is_there_way_to(self._row + 1, self._col)
        raise RobotError(t("model.error.unknown_direction", direction=direction))

    def is_free_from(self, direction: Direction) -> bool:
        return not self.is_wall_from(direction)

    def get_pollution_level(self) -> int:
        return self._env.get_pollution_level(Cell(self._row, self._col))

    def print_number(self, value: object) -> None:
        if type(value) is not int:
            raise RobotError(t("model.error.printn_integers"))
        self._env.print_number(ValuedCell(self._row, self._col, value))
        self._change_listener()

    def _create_wall_hash_table(self) -> set[tuple[Cell, Cell]]:
        walls = set()
        for first, second in self._env.walls:
            walls.add((first, second))
            walls.add((second, first))
        return walls

    def _assert_there_is_way_to(self, row: int, col: int) -> None:
        if self._is_there_way_to(row, col):
            raise RobotPathError("robot.pathThroughWallError")

    def _is_there_way_to(self, row: int, col: int) -> bool:
        return (
            (Cell(self._row, self._col), Cell(row, col)) in self._walls
            or row < 0
            or row >= self._env.height
            or col < 0
            or col >= self._env.width
        )


def cell_from_dict(data: dict) -> Cell:
    return Cell(r=int(data["r"]), c=int(data["c"]))


def valued_cell_from_dict(data: dict) -> ValuedCell:
    return ValuedCell(r=int(data["r"]), c=int(data["c"]), value=int(data["value"]))


def is_valid_wall(first: Cell, second: Cell) -> bool:
    return abs(first.r - second.r) + abs(first.c - second.c) == 1


def same_position(first: Cell, second: Cell) -> bool:
    return first.r == second.r and first.c == second.c


def count_positions(target: Cell, cells: Iterable[Cell]) -> int:
    return sum(1 for cell in cells if same_position(target, cell))


def deduplicate_cells(cells: Iterable[CellType]) -> list[CellType]:
    unique_by_position: dict[tuple[int, int], CellType] = {}
    for cell in cells:
        unique_by_position[(cell.r, cell.c)] = cell
    return list(unique_by_position.values())
