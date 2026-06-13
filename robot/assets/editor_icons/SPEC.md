# Environment editor toolbar icons

PNG icons for the desktop environment editor (`robot/gui_editor.py`), matching the web
embedded editor (`SidWebUi/.../embedded-env-editor`).

## PNG specification

| Property | Value |
|----------|-------|
| Base size | 24×24 px (`png/`) |
| HiDPI size | 48×48 px (`png@2x/`) |
| Format | PNG with alpha channel |
| Content | Pictogram only (no button chrome, shadow, or border) |

### Palette (tool icons)

| Role | Color |
|------|-------|
| Robot / wall accent | `#428bca` |
| Painted / mark | `#f0ad4e` |
| Final / print number | `#a93b20` |
| Pollution digit fill | `#000000` |
| Stroke / outline | `#ffffff` |
| Remove cross | `orange` (`#ffa500`) |

Utility icons (add/remove env, reset, todo, undo, redo) are original dark-gray
(`#374151`) glyphs drawn for this project. They are not derived from any
third-party icon set, so no external attribution is required.

### Numeric glyphs

Pollution and number tool icons show the digit `1` as a placeholder glyph (same as the
web editor). The SVG sources use `DejaVu Sans Bold` so PNG export does not depend on
Roboto being installed.

## File inventory

| PNG file | Source | Desktop control |
|----------|--------|-----------------|
| `editor_start.png` | Web inline SVG | `EnvEditTool.START` |
| `editor_final.png` | Web inline SVG | `EnvEditTool.FINAL` |
| `editor_wall.png` | Web inline SVG | `EnvEditTool.WALL` |
| `editor_painted.png` | Web inline SVG | `EnvEditTool.PAINTED` |
| `editor_to_paint.png` | Web inline SVG | `EnvEditTool.TO_PAINT` |
| `editor_pollution.png` | Web inline SVG | `EnvEditTool.POLLUTION` |
| `editor_number.png` | Web inline SVG | `EnvEditTool.NUMBER` |
| `editor_remove_pollution.png` | Web inline SVG | `EnvEditTool.REMOVE_POLLUTION` |
| `editor_remove_number.png` | Web inline SVG | `EnvEditTool.REMOVE_NUMBER` |
| `editor_add_env.png` | Original SVG (plus) | Add environment (`+`) |
| `editor_remove_env.png` | Original SVG (minus) | Remove environment (`-`) |
| `editor_reset_env.png` | Original SVG (eraser) | Reset environment |
| `editor_todo.png` | Original SVG (list) | Edit task condition |
| `editor_undo.png` | Original SVG (undo) | Undo |
| `editor_redo.png` | Original SVG (redo) | Redo |

## Runtime loading

The desktop editor loads icons from `png@2x/` (48×48) and displays them at ~24×24 via
`PhotoImage.subsample(2, 2)` in `robot/editor_icons.py`. The `png/` directory remains
the 24×24 reference output from the build script.

## Directory layout

```
robot/assets/editor_icons/
  SPEC.md           — this file
  svg/              — editable vector sources
  png/              — 24×24 PNG output (committed)
  png@2x/           — 48×48 PNG output (committed)
```

Regenerate PNGs after editing SVG sources:

```bash
python tools/build_editor_icons.py
```

Requires ImageMagick (`convert`).
