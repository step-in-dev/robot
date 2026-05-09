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
        self.assertTrue(len(str(ctx.exception)) > 0)

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


class RobotEnvDtoNormalizationTest(unittest.TestCase):
    def test_normalization_matches_sidwebui_rules(self):
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
                    [{"r": 0, "c": 0}, {"r": 0, "c": 0}],
                ],
                "paintedCells": [{"r": 0, "c": 0}],
                "cellsToPaint": [{"r": 0, "c": 0}, {"r": 0, "c": 1}],
            }
        )

        self.assertEqual(len(dto.walls), 1)
        self.assertEqual(len(dto.cells_to_paint), 1)
        self.assertEqual((dto.cells_to_paint[0].r, dto.cells_to_paint[0].c), (0, 1))

    def test_normalized_deduplicates_painted_cells(self):
        dto = RobotEnvDto.from_dict(
            {
                "width": 2,
                "height": 1,
                "startRow": 0,
                "startCol": 0,
                "finalRow": 0,
                "finalCol": 1,
                "paintedCells": [{"r": 0, "c": 0}, {"r": 0, "c": 0}],
            }
        )
        self.assertEqual(len(dto.painted_cells), 1)
        self.assertEqual(dto.painted_cells[0], Cell(0, 0))

    def test_normalized_deduplicates_polluted_cells(self):
        dto = RobotEnvDto.from_dict(
            {
                "width": 2,
                "height": 1,
                "startRow": 0,
                "startCol": 0,
                "finalRow": 0,
                "finalCol": 1,
                "pollutedCells": [{"r": 0, "c": 0, "value": 3}, {"r": 0, "c": 0, "value": 5}],
            }
        )
        self.assertEqual(len(dto.polluted_cells), 1)
        self.assertEqual(dto.polluted_cells[0], ValuedCell(0, 0, 5))

    def test_normalized_deduplicates_cells_to_print(self):
        dto = RobotEnvDto.from_dict(
            {
                "width": 2,
                "height": 1,
                "startRow": 0,
                "startCol": 0,
                "finalRow": 0,
                "finalCol": 1,
                "cellsToPrint": [
                    {"r": 0, "c": 0, "value": 1},
                    {"r": 0, "c": 0, "value": 2},
                ],
            }
        )
        self.assertEqual(len(dto.cells_to_print), 1)
        self.assertEqual(dto.cells_to_print[0], ValuedCell(0, 0, 2))

    def test_normalized_filters_invalid_walls(self):
        dto = RobotEnvDto.from_dict(
            {
                "width": 3,
                "height": 1,
                "startRow": 0,
                "startCol": 0,
                "finalRow": 0,
                "finalCol": 2,
                "walls": [
                    [{"r": 0, "c": 0}, {"r": 0, "c": 1}],
                    [{"r": 0, "c": 0}, {"r": 0, "c": 0}],
                    [{"r": 0, "c": 0}, {"r": 0, "c": 2}],
                ],
            }
        )
        self.assertEqual(len(dto.walls), 1)
        self.assertEqual(dto.walls[0], (Cell(0, 0), Cell(0, 1)))

    def test_normalized_cells_to_paint_excludes_already_painted(self):
        dto = RobotEnvDto.from_dict(
            {
                "width": 2,
                "height": 1,
                "startRow": 0,
                "startCol": 0,
                "finalRow": 0,
                "finalCol": 1,
                "paintedCells": [{"r": 0, "c": 0}],
                "cellsToPaint": [{"r": 0, "c": 0}, {"r": 0, "c": 1}],
            }
        )
        self.assertEqual(len(dto.cells_to_paint), 1)
        self.assertEqual(dto.cells_to_paint[0], Cell(0, 1))
        self.assertEqual(len(dto.painted_cells), 1)
        self.assertEqual(dto.painted_cells[0], Cell(0, 0))

    def test_normalized_combined_paint_deduplication_and_filtering(self):
        dto = RobotEnvDto.from_dict(
            {
                "width": 3,
                "height": 1,
                "startRow": 0,
                "startCol": 0,
                "finalRow": 0,
                "finalCol": 2,
                "paintedCells": [{"r": 0, "c": 0}, {"r": 0, "c": 0}],
                "cellsToPaint": [{"r": 0, "c": 0}, {"r": 0, "c": 0}, {"r": 0, "c": 1}],
            }
        )
        self.assertEqual(len(dto.painted_cells), 1)
        self.assertEqual(len(dto.cells_to_paint), 1)
        self.assertEqual(dto.cells_to_paint[0], Cell(0, 1))

    def test_direct_dto_creation_and_normalization(self):
        dto = RobotEnvDto(
            width=2,
            height=1,
            start_row=0,
            start_col=0,
            final_row=0,
            final_col=1,
            walls=[(Cell(0, 0), Cell(0, 0))],
            painted_cells=[Cell(0, 0), Cell(0, 0)],
            cells_to_paint=[Cell(0, 0), Cell(0, 1)],
        )
        normalized = dto.normalized()
        self.assertEqual(len(normalized.walls), 0)
        self.assertEqual(len(normalized.painted_cells), 1)
        self.assertEqual(len(normalized.cells_to_paint), 1)
        self.assertEqual(normalized.cells_to_paint[0], Cell(0, 1))


if __name__ == "__main__":
    unittest.main()
