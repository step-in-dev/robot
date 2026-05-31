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

        cell_size = 80
        wall_width = 4
        half = wall_width // 2
        canvas_w = 2 * cell_size + wall_width
        canvas_h = 2 * cell_size + wall_width

        canvas = tk.Canvas(self.root, width=canvas_w, height=canvas_h)
        colors = FieldColors(
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
        FieldRenderer(canvas, cell_size, wall_width).draw_field(
            env, canvas_w, canvas_h, colors
        )

        texts = _collect_text_items(canvas)
        colored = [
            t
            for t in texts
            if t["fill"] in ("#404C51", "#712903")
        ]
        outlines = [t for t in texts if t["fill"] == TEXT_OUTLINE_COLOR]
        self.assertEqual(len(colored), 3)
        self.assertEqual(len(outlines), 3 * len(field_renderer_mod._TEXT_OUTLINE_OFFSETS))

        pollution = next(t for t in colored if t["fill"] == "#404C51")
        prints = [t for t in colored if t["fill"] == "#712903"]
        self.assertEqual(len(prints), 2)

        self.assertEqual(pollution["text"], "7")
        self.assertEqual(pollution["anchor"], "sw")
        px, py = pollution["coords"]  # type: ignore[misc]
        self.assertEqual(px, 0 * cell_size + wall_width + half)
        self.assertEqual(py, (1 + 1) * cell_size - half)

        for t in prints:
            self.assertEqual(t["anchor"], "nw")
            self.assertEqual(t["text"], "42")

        font_size = cell_text_font_size(cell_size)
        gap = print_line_gap(font_size)
        y_expected = 0 * cell_size + half
        y_printed = 0 * cell_size + font_size + gap + half
        ys = sorted(float(t["coords"][1]) for t in prints)  # type: ignore[index]
        self.assertAlmostEqual(ys[0], y_expected, delta=0.001)
        self.assertAlmostEqual(ys[1], y_printed, delta=0.001)
        self.assertLess(ys[0], ys[1])

        x_rights = [
            float(t["coords"][0]) + _text_width(t["text"], font_size)  # type: ignore[arg-type]
            for t in prints
        ]
        right_edge = (0 + 1) * cell_size - half
        for xr in x_rights:
            self.assertAlmostEqual(xr, right_edge, delta=0.001)

        for dx, dy in field_renderer_mod._TEXT_OUTLINE_OFFSETS:
            self.assertTrue(
                _outline_text_at(
                    outlines,
                    text="7",
                    anchor="sw",
                    ox=float(px) + dx * TEXT_OUTLINE_OFFSET,
                    oy=float(py) + dy * TEXT_OUTLINE_OFFSET,
                ),
                msg=f"missing outline for pollution at offset ({dx}, {dy})",
            )

        for t in prints:
            pxp, pyp = t["coords"]  # type: ignore[misc]
            for dx, dy in field_renderer_mod._TEXT_OUTLINE_OFFSETS:
                self.assertTrue(
                    _outline_text_at(
                        outlines,
                        text="42",
                        anchor="nw",
                        ox=float(pxp) + dx * TEXT_OUTLINE_OFFSET,
                        oy=float(pyp) + dy * TEXT_OUTLINE_OFFSET,
                    ),
                    msg=f"missing outline for print at offset ({dx}, {dy})",
                )


def _text_width(text: str, font_size: int) -> float:
    f = tkfont.Font(family="Arial", size=font_size, weight="bold")
    return float(f.measure(text))
