"""Grid environment, robot movement, painting, and validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, List, Set, Tuple

from .i18n import t

MAX_FIELD_WIDTH = 20
MAX_FIELD_HEIGHT = 15

Direction = str


class RobotError(Exception):
    """Base exception for robot runtime errors."""


class RobotPathError(RobotError):
    """Raised when the robot tries to move through a wall or field border."""


def _is_plain_int(value: object) -> bool:
    """Return whether *value* is an ``int`` but not ``bool``."""
    return isinstance(value, int) and not isinstance(value, bool)


@dataclass(frozen=True)
class Cell:
    """Grid coordinates as row and column indices."""

    r: int
    c: int


@dataclass(frozen=True)
class ValuedCell(Cell):
    """Grid cell with an integer value (pollution or print)."""

    value: int


@dataclass
class RobotEnvDto:  # pylint: disable=too-many-instance-attributes
    """Validated environment layout loaded from a task file (flat ``.env`` JSON)."""

    width: int
    height: int
    start_row: int
    start_col: int
    final_row: int
    final_col: int
    walls: List[Tuple[Cell, Cell]] = field(default_factory=list)
    painted_cells: List[Cell] = field(default_factory=list)
    cells_to_paint: List[Cell] = field(default_factory=list)
    polluted_cells: List[ValuedCell] = field(default_factory=list)
    cells_to_print: List[ValuedCell] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "RobotEnvDto":
        """Build a DTO from a task JSON environment object."""
        try:
            width = int(data["width"])
            height = int(data["height"])
            start_row = int(data["startRow"])
            start_col = int(data["startCol"])
            final_row = int(data["finalRow"])
            final_col = int(data["finalCol"])
            walls = [
                (cell_from_dict(wall[0]), cell_from_dict(wall[1]))
                for wall in data.get("walls", [])
                if isinstance(wall, list) and len(wall) == 2
            ]
            painted_cells = [
                cell_from_dict(cell) for cell in data.get("paintedCells", [])
            ]
            cells_to_paint = [
                cell_from_dict(cell) for cell in data.get("cellsToPaint", [])
            ]
            polluted_cells = [
                valued_cell_from_dict(cell)
                for cell in data.get("pollutedCells", [])
            ]
            cells_to_print = [
                valued_cell_from_dict(cell)
                for cell in data.get("cellsToPrint", [])
            ]
        except KeyError as exc:
            raise ValueError(
                t("model.error.missing_env_field", field=exc.args[0])
            ) from exc
        except (TypeError, ValueError) as exc:
            raise ValueError(t("model.error.invalid_env_format")) from exc

        return cls(
            width=width,
            height=height,
            start_row=start_row,
            start_col=start_col,
            final_row=final_row,
            final_col=final_col,
            walls=walls,
            painted_cells=painted_cells,
            cells_to_paint=cells_to_paint,
            polluted_cells=polluted_cells,
            cells_to_print=cells_to_print,
        )

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        self._validate_dimensions()
        self._validate_start_and_final_in_bounds()
        self._validate_cell_collections_in_bounds()
        self._validate_painted_and_to_paint_disjoint()
        self._validate_walls()

    def _validate_dimensions(self) -> None:
        if self.width <= 0:
            raise ValueError(t("model.error.width_not_positive", width=self.width))
        if self.height <= 0:
            raise ValueError(t("model.error.height_not_positive", height=self.height))

    def _validate_start_and_final_in_bounds(self) -> None:
        if not (0 <= self.start_row < self.height and 0 <= self.start_col < self.width):
            raise ValueError(
                t(
                    "model.error.start_position_out_of_bounds",
                    row=self.start_row,
                    col=self.start_col,
                    height=self.height,
                    width=self.width,
                )
            )
        if not (0 <= self.final_row < self.height and 0 <= self.final_col < self.width):
            raise ValueError(
                t(
                    "model.error.final_position_out_of_bounds",
                    row=self.final_row,
                    col=self.final_col,
                    height=self.height,
                    width=self.width,
                )
            )

    def _validate_cell_collections_in_bounds(self) -> None:
        _validate_cell_positions(
            self.painted_cells, "paintedCells", self.width, self.height
        )
        _validate_cell_positions(
            self.cells_to_paint, "cellsToPaint", self.width, self.height
        )
        _validate_cell_positions(
            self.polluted_cells, "pollutedCells", self.width, self.height
        )
        _validate_cell_positions(
            self.cells_to_print, "cellsToPrint", self.width, self.height
        )

    def _validate_painted_and_to_paint_disjoint(self) -> None:
        painted_positions = {(c.r, c.c) for c in self.painted_cells}
        to_paint_positions = {(c.r, c.c) for c in self.cells_to_paint}
        overlap = painted_positions & to_paint_positions
        if overlap:
            r, c = next(iter(overlap))
            raise ValueError(
                t("model.error.painted_and_to_paint_overlap", r=r, c=c)
            )

    def _validate_walls(self) -> None:
        seen_walls: Set[Tuple[Tuple[int, int], Tuple[int, int]]] = set()
        for first, second in self.walls:
            for cell in (first, second):
                if not (0 <= cell.r < self.height and 0 <= cell.c < self.width):
                    raise ValueError(
                        t("model.error.wall_cell_out_of_bounds", r=cell.r, c=cell.c)
                    )
            if not is_valid_wall(first, second):
                raise ValueError(
                    t(
                        "model.error.wall_not_adjacent",
                        r1=first.r,
                        c1=first.c,
                        r2=second.r,
                        c2=second.c,
                    )
                )
            canonical = _canonical_wall(first, second)
            if canonical in seen_walls:
                raise ValueError(
                    t(
                        "model.error.duplicate_wall",
                        r1=first.r,
                        c1=first.c,
                        r2=second.r,
                        c2=second.c,
                    )
                )
            seen_walls.add(canonical)


class RobotEnv:  # pylint: disable=too-many-public-methods
    """Mutable task environment: grid state, robot, and change listeners.

    Public surface: DTO properties, mutations, and change listeners.
    """

    def __init__(self, dto: RobotEnvDto):
        """Create a mutable environment from a validated DTO."""
        self._dto = dto
        self._listeners: List[Callable[[], None]] = []
        self._newly_painted_cells: List[Cell] = []
        self._printed_cells: List[ValuedCell] = []
        self._robot = Robot(self, self._notify_listeners)

    @property
    def robot(self) -> "Robot":
        """Robot instance bound to this environment."""
        return self._robot

    @property
    def width(self) -> int:
        """Grid width in cells."""
        return self._dto.width

    @property
    def height(self) -> int:
        """Grid height in cells."""
        return self._dto.height

    @property
    def start_row(self) -> int:
        """Starting row of the robot."""
        return self._dto.start_row

    @property
    def start_col(self) -> int:
        """Starting column of the robot."""
        return self._dto.start_col

    @property
    def final_row(self) -> int:
        """Required final row of the robot."""
        return self._dto.final_row

    @property
    def final_col(self) -> int:
        """Required final column of the robot."""
        return self._dto.final_col

    @property
    def walls(self) -> Tuple[Tuple[Cell, Cell], ...]:
        """Wall segments as pairs of adjacent cells."""
        return tuple(self._dto.walls)

    @property
    def painted_cells(self) -> Tuple[Cell, ...]:
        """Cells painted in the initial state."""
        return tuple(self._dto.painted_cells)

    @property
    def cells_to_paint(self) -> Tuple[Cell, ...]:
        """Cells the solution must paint during the run."""
        return tuple(self._dto.cells_to_paint)

    @property
    def polluted_cells(self) -> Tuple[ValuedCell, ...]:
        """Cells with fixed pollution values."""
        return tuple(self._dto.polluted_cells)

    @property
    def cells_to_print(self) -> Tuple[ValuedCell, ...]:
        """Cells and values the solution must print."""
        return tuple(self._dto.cells_to_print)

    @property
    def printed_cells(self) -> Tuple[ValuedCell, ...]:
        """Values printed so far during the run."""
        return tuple(self._printed_cells)

    def add_listener(self, listener: Callable[[], None]) -> None:
        """Register a callback invoked when environment state changes."""
        self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[], None]) -> None:
        """Unregister a previously added change listener."""
        self._listeners.remove(listener)

    def extract_painted_cells(self) -> Tuple[Cell, ...]:
        """Return initial and newly painted cells."""
        return tuple(self._newly_painted_cells + self._dto.painted_cells)

    def paint(self, cell: Cell) -> None:
        """Record a cell as painted during the run."""
        self._newly_painted_cells.append(cell)

    def is_painted(self, cell: Cell) -> bool:
        """Return whether ``cell`` is painted initially or during the run."""
        return cell in self._newly_painted_cells or cell in self._dto.painted_cells

    def get_pollution_level(self, cell: Cell) -> int:
        """Return pollution at ``cell``, or ``0`` when the cell is not polluted."""
        for polluted_cell in self._dto.polluted_cells:
            if same_position(polluted_cell, cell):
                return polluted_cell.value
        return 0

    def print_number(self, cell: ValuedCell) -> None:
        """Store a printed value at ``cell``, replacing any prior print there."""
        self._printed_cells = [
            printed_cell
            for printed_cell in self._printed_cells
            if not same_position(printed_cell, cell)
        ]
        self._printed_cells.append(cell)

    def reset(self) -> None:
        """Clear run-time paint/print state and reset the robot to the start."""
        self._newly_painted_cells = []
        self._printed_cells = []
        self._robot.reset()

    def is_in_final_state(self) -> bool:
        """Return whether position, paint, and print goals are all satisfied."""
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
    """Robot actor that moves, paints, and reads sensors on the grid."""

    def __init__(self, env: RobotEnv, change_listener: Callable[[], None]):
        """Place the robot at the environment start and build wall lookup."""
        self._env = env
        self._change_listener = change_listener
        self._row = env.start_row
        self._col = env.start_col
        self._walls = self._create_wall_hash_table()

    @property
    def row(self) -> int:
        """Current row of the robot."""
        return self._row

    @property
    def col(self) -> int:
        """Current column of the robot."""
        return self._col

    def reset(self) -> None:
        """Move back to the start cell and notify listeners."""
        self._row = self._env.start_row
        self._col = self._env.start_col
        self._walls = self._create_wall_hash_table()
        self._change_listener()

    def move_right(self) -> None:
        """Move one cell right or raise ``RobotPathError``."""
        self._assert_there_is_way_to(self._row, self._col + 1)
        self._col += 1
        self._change_listener()

    def move_left(self) -> None:
        """Move one cell left or raise ``RobotPathError``."""
        self._assert_there_is_way_to(self._row, self._col - 1)
        self._col -= 1
        self._change_listener()

    def move_up(self) -> None:
        """Move one cell up or raise ``RobotPathError``."""
        self._assert_there_is_way_to(self._row - 1, self._col)
        self._row -= 1
        self._change_listener()

    def move_down(self) -> None:
        """Move one cell down or raise ``RobotPathError``."""
        self._assert_there_is_way_to(self._row + 1, self._col)
        self._row += 1
        self._change_listener()

    def paint(self) -> None:
        """Paint the cell under the robot."""
        self._env.paint(Cell(self._row, self._col))
        self._change_listener()

    def is_cell_painted(self) -> bool:
        """Return whether the current cell is painted."""
        return self._env.is_painted(Cell(self._row, self._col))

    def is_wall_from(self, direction: Direction) -> bool:
        """Return whether movement in ``direction`` is blocked."""
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
        """Return whether movement in ``direction`` is not blocked."""
        return not self.is_wall_from(direction)

    def get_pollution_level(self) -> int:
        """Return pollution at the cell under the robot."""
        return self._env.get_pollution_level(Cell(self._row, self._col))

    def print_number(self, value: object) -> None:
        """Print an integer at the current cell."""
        if not _is_plain_int(value):
            raise RobotError(t("model.error.printn_integers"))
        self._env.print_number(ValuedCell(self._row, self._col, value))
        self._change_listener()

    def _create_wall_hash_table(self) -> Set[Tuple[Cell, Cell]]:
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
    """Parse a ``{r, c}`` cell object from task JSON."""
    return Cell(r=int(data["r"]), c=int(data["c"]))


def valued_cell_from_dict(data: dict) -> ValuedCell:
    """Parse a ``{r, c, value}`` cell object from task JSON."""
    return ValuedCell(r=int(data["r"]), c=int(data["c"]), value=int(data["value"]))


def is_valid_wall(first: Cell, second: Cell) -> bool:
    """Return whether two cells form an orthogonal adjacent wall segment."""
    return abs(first.r - second.r) + abs(first.c - second.c) == 1


def same_position(first: Cell, second: Cell) -> bool:
    """Return whether two cells share the same coordinates."""
    return first.r == second.r and first.c == second.c


def count_positions(target: Cell, cells: Iterable[Cell]) -> int:
    """Count how many cells in ``cells`` match ``target``."""
    return sum(1 for cell in cells if same_position(target, cell))


def _validate_cell_positions(
    cells: Iterable[Cell], field_name: str, width: int, height: int
) -> None:
    seen: Set[Tuple[int, int]] = set()
    for cell in cells:
        if not (0 <= cell.r < height and 0 <= cell.c < width):
            raise ValueError(
                t(
                    "model.error.cell_out_of_bounds",
                    r=cell.r,
                    c=cell.c,
                    field=field_name,
                )
            )
        pos = (cell.r, cell.c)
        if pos in seen:
            raise ValueError(
                t(
                    "model.error.duplicate_cell",
                    r=cell.r,
                    c=cell.c,
                    field=field_name,
                )
            )
        seen.add(pos)


def _canonical_wall(
    first: Cell, second: Cell
) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    a = (first.r, first.c)
    b = (second.r, second.c)
    return (a, b) if a < b else (b, a)
