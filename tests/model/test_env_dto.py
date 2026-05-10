import unittest

from robot.model import RobotEnvDto, Cell, ValuedCell


class RobotEnvDtoFromDictTest(unittest.TestCase):
    def test_from_dict_basic_parsing(self):
        dto = RobotEnvDto.from_dict(
            {
                "width": 2,
                "height": 1,
                "startRow": 0,
                "startCol": 0,
                "finalRow": 0,
                "finalCol": 1,
            }
        )
        self.assertEqual(dto.width, 2)
        self.assertEqual(dto.height, 1)
        self.assertEqual(dto.start_row, 0)
        self.assertEqual(dto.start_col, 0)
        self.assertEqual(dto.final_row, 0)
        self.assertEqual(dto.final_col, 1)
        self.assertEqual(dto.walls, [])
        self.assertEqual(dto.painted_cells, [])
        self.assertEqual(dto.cells_to_paint, [])
        self.assertEqual(dto.polluted_cells, [])
        self.assertEqual(dto.cells_to_print, [])

    def test_from_dict_with_all_optional_fields(self):
        dto = RobotEnvDto.from_dict(
            {
                "width": 3,
                "height": 2,
                "startRow": 0,
                "startCol": 0,
                "finalRow": 1,
                "finalCol": 2,
                "walls": [[{"r": 0, "c": 0}, {"r": 0, "c": 1}]],
                "paintedCells": [{"r": 0, "c": 0}],
                "cellsToPaint": [{"r": 0, "c": 1}],
                "pollutedCells": [{"r": 0, "c": 0, "value": 5}],
                "cellsToPrint": [{"r": 0, "c": 1, "value": 7}],
            }
        )
        self.assertEqual(len(dto.walls), 1)
        self.assertEqual(dto.walls[0], (Cell(0, 0), Cell(0, 1)))
        self.assertEqual(dto.painted_cells, [Cell(0, 0)])
        self.assertEqual(dto.cells_to_paint, [Cell(0, 1)])
        self.assertEqual(dto.polluted_cells, [ValuedCell(0, 0, 5)])
        self.assertEqual(dto.cells_to_print, [ValuedCell(0, 1, 7)])

    def test_from_dict_missing_required_field_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            RobotEnvDto.from_dict(
                {
                    "height": 1,
                    "startRow": 0,
                    "startCol": 0,
                    "finalRow": 0,
                    "finalCol": 1,
                }
            )
        self.assertIn("width", str(ctx.exception))

    def test_from_dict_invalid_type_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            RobotEnvDto.from_dict(
                {
                    "width": "abc",
                    "height": 1,
                    "startRow": 0,
                    "startCol": 0,
                    "finalRow": 0,
                    "finalCol": 1,
                }
            )
        self.assertGreater(len(str(ctx.exception)), 0)

    def test_from_dict_missing_optional_fields_default_to_empty(self):
        dto = RobotEnvDto.from_dict(
            {
                "width": 1,
                "height": 1,
                "startRow": 0,
                "startCol": 0,
                "finalRow": 0,
                "finalCol": 0,
            }
        )
        self.assertEqual(dto.walls, [])
        self.assertEqual(dto.painted_cells, [])
        self.assertEqual(dto.cells_to_paint, [])
        self.assertEqual(dto.polluted_cells, [])
        self.assertEqual(dto.cells_to_print, [])

    def test_from_dict_skips_malformed_walls(self):
        dto = RobotEnvDto.from_dict(
            {
                "width": 2,
                "height": 1,
                "startRow": 0,
                "startCol": 0,
                "finalRow": 0,
                "finalCol": 1,
                "walls": [
                    [{"r": 0, "c": 0}, {"r": 0, "c": 1}],
                    "not a list",
                    [{"r": 0, "c": 0}],
                    [{"r": 0, "c": 0}, {"r": 0, "c": 1}, {"r": 0, "c": 2}],
                ],
            }
        )
        self.assertEqual(len(dto.walls), 1)

    def test_from_dict_empty_walls(self):
        dto = RobotEnvDto.from_dict(
            {
                "width": 2,
                "height": 1,
                "startRow": 0,
                "startCol": 0,
                "finalRow": 0,
                "finalCol": 1,
                "walls": [],
            }
        )
        self.assertEqual(dto.walls, [])

    def test_from_dict_string_numbers_coerced(self):
        dto = RobotEnvDto.from_dict(
            {
                "width": "5",
                "height": "3",
                "startRow": "0",
                "startCol": "0",
                "finalRow": "2",
                "finalCol": "4",
            }
        )
        self.assertEqual(dto.width, 5)
        self.assertEqual(dto.height, 3)

    def test_from_dict_float_numbers_coerced(self):
        dto = RobotEnvDto.from_dict(
            {
                "width": 5.7,
                "height": 3.2,
                "startRow": 0,
                "startCol": 0,
                "finalRow": 0,
                "finalCol": 1,
            }
        )
        self.assertEqual(dto.width, 5)
        self.assertEqual(dto.height, 3)


class RobotEnvDtoValidationTest(unittest.TestCase):
    def _minimal_valid(self, **overrides):
        data = {
            "width": 2,
            "height": 1,
            "startRow": 0,
            "startCol": 0,
            "finalRow": 0,
            "finalCol": 1,
        }
        data.update(overrides)
        return data

    def test_width_not_positive(self):
        with self.assertRaises(ValueError) as ctx:
            RobotEnvDto.from_dict(self._minimal_valid(width=0))
        self.assertIn("width", str(ctx.exception).lower())

    def test_height_not_positive(self):
        with self.assertRaises(ValueError) as ctx:
            RobotEnvDto.from_dict(self._minimal_valid(height=0))
        self.assertIn("height", str(ctx.exception).lower())

    def test_start_row_negative(self):
        with self.assertRaises(ValueError) as ctx:
            RobotEnvDto.from_dict(self._minimal_valid(startRow=-1))
        self.assertIn("start", str(ctx.exception).lower())

    def test_start_row_gte_height(self):
        with self.assertRaises(ValueError) as ctx:
            RobotEnvDto.from_dict(self._minimal_valid(height=1, startRow=1))
        self.assertIn("start", str(ctx.exception).lower())

    def test_start_col_negative(self):
        with self.assertRaises(ValueError) as ctx:
            RobotEnvDto.from_dict(self._minimal_valid(startCol=-1))
        self.assertIn("start", str(ctx.exception).lower())

    def test_start_col_gte_width(self):
        with self.assertRaises(ValueError) as ctx:
            RobotEnvDto.from_dict(self._minimal_valid(width=1, startCol=1))
        self.assertIn("start", str(ctx.exception).lower())

    def test_final_row_out_of_bounds(self):
        with self.assertRaises(ValueError) as ctx:
            RobotEnvDto.from_dict(self._minimal_valid(finalRow=5))
        self.assertIn("outside", str(ctx.exception).lower())

    def test_final_col_out_of_bounds(self):
        with self.assertRaises(ValueError) as ctx:
            RobotEnvDto.from_dict(self._minimal_valid(finalCol=5))
        self.assertIn("outside", str(ctx.exception).lower())

    def test_painted_cell_out_of_bounds(self):
        with self.assertRaises(ValueError) as ctx:
            RobotEnvDto.from_dict(
                self._minimal_valid(paintedCells=[{"r": 0, "c": 5}])
            )
        self.assertIn("paintedCells", str(ctx.exception))

    def test_duplicate_painted_cell(self):
        with self.assertRaises(ValueError) as ctx:
            RobotEnvDto.from_dict(
                self._minimal_valid(
                    paintedCells=[{"r": 0, "c": 0}, {"r": 0, "c": 0}]
                )
            )
        self.assertIn("paintedCells", str(ctx.exception))

    def test_cells_to_paint_out_of_bounds(self):
        with self.assertRaises(ValueError) as ctx:
            RobotEnvDto.from_dict(
                self._minimal_valid(cellsToPaint=[{"r": 0, "c": 5}])
            )
        self.assertIn("cellsToPaint", str(ctx.exception))

    def test_duplicate_cells_to_paint(self):
        with self.assertRaises(ValueError) as ctx:
            RobotEnvDto.from_dict(
                self._minimal_valid(
                    cellsToPaint=[{"r": 0, "c": 0}, {"r": 0, "c": 0}]
                )
            )
        self.assertIn("cellsToPaint", str(ctx.exception))

    def test_painted_and_to_paint_overlap(self):
        with self.assertRaises(ValueError) as ctx:
            RobotEnvDto.from_dict(
                self._minimal_valid(
                    paintedCells=[{"r": 0, "c": 0}],
                    cellsToPaint=[{"r": 0, "c": 0}],
                )
            )
        self.assertIn("painted", str(ctx.exception).lower())

    def test_polluted_cell_out_of_bounds(self):
        with self.assertRaises(ValueError) as ctx:
            RobotEnvDto.from_dict(
                self._minimal_valid(
                    pollutedCells=[{"r": 0, "c": 5, "value": 1}]
                )
            )
        self.assertIn("pollutedCells", str(ctx.exception))

    def test_duplicate_polluted_cell(self):
        with self.assertRaises(ValueError) as ctx:
            RobotEnvDto.from_dict(
                self._minimal_valid(
                    pollutedCells=[
                        {"r": 0, "c": 0, "value": 1},
                        {"r": 0, "c": 0, "value": 2},
                    ]
                )
            )
        self.assertIn("pollutedCells", str(ctx.exception))

    def test_cells_to_print_out_of_bounds(self):
        with self.assertRaises(ValueError) as ctx:
            RobotEnvDto.from_dict(
                self._minimal_valid(
                    cellsToPrint=[{"r": 0, "c": 5, "value": 1}]
                )
            )
        self.assertIn("cellsToPrint", str(ctx.exception))

    def test_duplicate_cells_to_print(self):
        with self.assertRaises(ValueError) as ctx:
            RobotEnvDto.from_dict(
                self._minimal_valid(
                    cellsToPrint=[
                        {"r": 0, "c": 0, "value": 1},
                        {"r": 0, "c": 0, "value": 2},
                    ]
                )
            )
        self.assertIn("cellsToPrint", str(ctx.exception))

    def test_wall_cell_out_of_bounds(self):
        with self.assertRaises(ValueError) as ctx:
            RobotEnvDto.from_dict(
                self._minimal_valid(
                    width=3,
                    walls=[[{"r": 0, "c": 0}, {"r": 0, "c": 5}]],
                )
            )
        self.assertIn("wall", str(ctx.exception).lower())

    def test_wall_not_adjacent(self):
        with self.assertRaises(ValueError) as ctx:
            RobotEnvDto.from_dict(
                self._minimal_valid(
                    width=3,
                    walls=[[{"r": 0, "c": 0}, {"r": 0, "c": 2}]],
                )
            )
        self.assertIn("adjacent", str(ctx.exception).lower())

    def test_duplicate_wall(self):
        with self.assertRaises(ValueError) as ctx:
            RobotEnvDto.from_dict(
                self._minimal_valid(
                    walls=[
                        [{"r": 0, "c": 0}, {"r": 0, "c": 1}],
                        [{"r": 0, "c": 1}, {"r": 0, "c": 0}],
                    ],
                )
            )
        self.assertIn("wall", str(ctx.exception).lower())

    def test_valid_boundary_values_pass(self):
        dto = RobotEnvDto.from_dict(
            {
                "width": 3,
                "height": 4,
                "startRow": 3,
                "startCol": 2,
                "finalRow": 0,
                "finalCol": 0,
            }
        )
        self.assertEqual(dto.width, 3)
        self.assertEqual(dto.height, 4)
        self.assertEqual(dto.start_row, 3)
        self.assertEqual(dto.start_col, 2)

    def test_direct_dto_creation_validates(self):
        with self.assertRaises(ValueError):
            RobotEnvDto(
                width=2,
                height=1,
                start_row=0,
                start_col=0,
                final_row=0,
                final_col=5,
            )


if __name__ == "__main__":
    unittest.main()
