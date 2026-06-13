"""Tests for field grid rendering on Canvas."""

from typing import Dict, List

import unittest

import tkinter as tk
import tkinter.font as tkfont

from robot import field_renderer as field_renderer_mod
from robot.field_renderer import (
    FieldColors,
    FieldRenderer,
    TEXT_OUTLINE_COLOR,
    TEXT_OUTLINE_OFFSET,
    cell_text_font_size,
    format_printable_value,
    print_line_gap,
)
from robot.model import ValuedCell
from robot.tk_util import destroy_tk_root
from tests.env_fixtures import env_dict, make_env
from tests.tk_display import GuiTestCase, requires_tk_display


def _collect_text_items(canvas: tk.Canvas) -> List[Dict[str, object]]:
    out: List[Dict[str, object]] = []
    for iid in canvas.find_all():
        if canvas.type(iid) != "text":
            continue
        xy = canvas.coords(iid)
        out.append(
            {
                "coords": xy,
                "text": canvas.itemcget(iid, "text"),
                "anchor": canvas.itemcget(iid, "anchor"),
                "fill": canvas.itemcget(iid, "fill"),
            }
        )
    return out


def _outline_text_at(
    items: List[Dict[str, object]],
    *,
    text: str,
    anchor: str,
    ox: float,
    oy: float,
) -> bool:
    for t in items:
        if t["text"] != text or t["anchor"] != anchor:
            continue
        cx, cy = t["coords"]  # type: ignore[misc]
        if abs(float(cx) - ox) < 0.001 and abs(float(cy) - oy) < 0.001:
            return True
    return False


def _text_width(text: str, font_size: int) -> float:
    f = tkfont.Font(family="Arial", size=font_size, weight="bold")
    return float(f.measure(text))


def _default_field_colors() -> FieldColors:
    return FieldColors(
        grid_color="#428bca",
        wall_color="#428bca",
        robot_color="#428bca",
        robot_outline="#ffffff",
        cell_to_paint_color="#f0ad4e",
        cell_to_paint_when_painted_color="#ffffff",
        home_color="#a93b20",
        pollution_color="#404C51",
        print_color="#712903",
        cell_background_color="#ffffff",
    )


def _render_env_on_canvas(
    root: tk.Tk,
    env: object,
    *,
    cell_size: int = 80,
    wall_width: int = 4,
) -> tuple:
    half = wall_width // 2
    canvas_w = 2 * cell_size + wall_width
    canvas_h = 2 * cell_size + wall_width
    canvas = tk.Canvas(root, width=canvas_w, height=canvas_h)
    FieldRenderer(canvas, cell_size, wall_width).draw_field(
        env, canvas_w, canvas_h, _default_field_colors()
    )
    return canvas, cell_size, wall_width, half


def _colored_and_outline_texts(
    texts: List[Dict[str, object]],
) -> tuple:
    colored = [
        t
        for t in texts
        if t["fill"] in ("#404C51", "#712903")
    ]
    outlines = [t for t in texts if t["fill"] == TEXT_OUTLINE_COLOR]
    return colored, outlines


def _assert_pollution_bottom_left(
    testcase: unittest.TestCase,
    pollution: Dict[str, object],
    *,
    cell_size: int,
    wall_width: int,
    half: int,
) -> None:
    testcase.assertEqual(pollution["text"], "7")
    testcase.assertEqual(pollution["anchor"], "sw")
    px, py = pollution["coords"]  # type: ignore[misc]
    testcase.assertEqual(px, 0 * cell_size + wall_width + half)
    testcase.assertEqual(py, (1 + 1) * cell_size - half)


def _assert_print_lines_stacked(
    testcase: unittest.TestCase,
    prints: List[Dict[str, object]],
    *,
    cell_size: int,
    half: int,
) -> None:
    testcase.assertEqual(len(prints), 2)
    for t in prints:
        testcase.assertEqual(t["anchor"], "nw")
        testcase.assertEqual(t["text"], "42")

    font_size = cell_text_font_size(cell_size)
    gap = print_line_gap(font_size)
    y_expected = 0 * cell_size + half
    y_printed = 0 * cell_size + font_size + gap + half
    ys = sorted(float(t["coords"][1]) for t in prints)  # type: ignore[index]
    testcase.assertAlmostEqual(ys[0], y_expected, delta=0.001)
    testcase.assertAlmostEqual(ys[1], y_printed, delta=0.001)
    testcase.assertLess(ys[0], ys[1])

    right_edge = (0 + 1) * cell_size - half
    for t in prints:
        text = str(t["text"])
        xr = float(t["coords"][0]) + _text_width(text, font_size)  # type: ignore[index]
        testcase.assertAlmostEqual(xr, right_edge, delta=0.001)


def _assert_text_outlines(
    testcase: unittest.TestCase,
    outlines: List[Dict[str, object]],
    items: List[Dict[str, object]],
) -> None:
    for item in items:
        text = str(item["text"])
        anchor = str(item["anchor"])
        px, py = item["coords"]  # type: ignore[misc]
        for dx, dy in field_renderer_mod._TEXT_OUTLINE_OFFSETS:
            testcase.assertTrue(
                _outline_text_at(
                    outlines,
                    text=text,
                    anchor=anchor,
                    ox=float(px) + dx * TEXT_OUTLINE_OFFSET,
                    oy=float(py) + dy * TEXT_OUTLINE_OFFSET,
                ),
                msg=f"missing outline for {text} at offset ({dx}, {dy})",
            )


class FormatPrintableValueTest(unittest.TestCase):
    def test_inclusive_range_minus_100_to_100(self) -> None:
        self.assertEqual(format_printable_value(0), "0")
        self.assertEqual(format_printable_value(-99), "-99")
        self.assertEqual(format_printable_value(99), "99")

    def test_outside_range_truncates_to_two_chars_plus_dots(self) -> None:
        self.assertEqual(format_printable_value(100), "10..")
        self.assertEqual(format_printable_value(-100), "-1..")
        self.assertEqual(format_printable_value(12345), "12..")
        self.assertEqual(format_printable_value(-123), "-1..")


class CellTextFontSizeTest(unittest.TestCase):
    def test_tkinter_tuned_formula(self) -> None:
        self.assertEqual(cell_text_font_size(80), 23)
        self.assertEqual(cell_text_font_size(28), 10)


class PrintLineGapTest(unittest.TestCase):
    def test_gap_scales_with_font(self) -> None:
        self.assertEqual(print_line_gap(25), 5)
        self.assertEqual(print_line_gap(10), 2)


@requires_tk_display
class FieldRendererTextPlacementTest(GuiTestCase):
    """Layout matches SidWebUi intent; tkinter uses anchor nw for print lines (top y)."""

    def setUp(self) -> None:
        self.root = tk.Tk()
        self.root.withdraw()

    def tearDown(self) -> None:
        destroy_tk_root(self.root)
        self.root = None  # type: ignore[assignment]
        super().tearDown()

    def test_pollution_bottom_left_expected_top_printed_second_line(self) -> None:
        env = make_env(
            env_dict(
                2,
                2,
                pollutedCells=[{"r": 1, "c": 0, "value": 7}],
                cellsToPrint=[{"r": 0, "c": 0, "value": 42}],
            )
        )
        env.print_number(ValuedCell(0, 0, 42))

        canvas, cell_size, wall_width, half = _render_env_on_canvas(self.root, env)
        colored, outlines = _colored_and_outline_texts(_collect_text_items(canvas))
        self.assertEqual(len(colored), 3)
        self.assertEqual(len(outlines), 3 * len(field_renderer_mod._TEXT_OUTLINE_OFFSETS))

        pollution = next(t for t in colored if t["fill"] == "#404C51")
        prints = [t for t in colored if t["fill"] == "#712903"]

        _assert_pollution_bottom_left(
            self, pollution, cell_size=cell_size, wall_width=wall_width, half=half
        )
        _assert_print_lines_stacked(
            self, prints, cell_size=cell_size, half=half
        )
        _assert_text_outlines(self, outlines, [pollution])
        _assert_text_outlines(self, outlines, prints)
