# Website screenshots

The static site under `website/` uses PNG images for marketing shots and for the **Environments** section on generated task pages. Task catalog HTML is generated at GitHub Pages deploy (see [`.github/workflows/static.yml`](../.github/workflows/static.yml)) or locally with `python tools/build_website_content.py`; it is not stored in git. HTML is built separately from images: the generator does not launch the GUI; task pages reference PNG paths such as `img/tasks/<task_id>_env<index>.png` when the files exist. English and Russian task pages use the **same** field images (the canvas has no UI chrome or locale-specific labels). Theme hub pages (`website/tasks/<theme>/`) show the same PNG as the first available environment on the task page as a clickable list thumbnail linking to the task page; no separate capture is needed.

## Two capture modes

| Use case | Tool | Output | Capture method |
|----------|------|--------|----------------|
| Task page field (Environments) | [`tools/capture_all_task_screenshots.py`](../tools/capture_all_task_screenshots.py) | `website/img/tasks/` | Field grid **canvas only** (no toolbar, todo, buttons, title bar, status) via [`tools/field_canvas_export.py`](../tools/field_canvas_export.py) |
| Hero / viewer marketing | [`tools/capture_robot_task_screenshots.py`](../tools/capture_robot_task_screenshots.py) | e.g. `website/img/viewer/` | **Full window** including OS title bar (`gnome-screenshot -w`) |

Field exports open the task in **viewer mode** (`viewer_catalog`) so the correct environment is selected, but the saved PNG is cropped to the `tkinter` field canvas. The `robot` package is not modified for this; export logic lives under `tools/`. Capture uses `ROBOT_LANGUAGE=en` for the viewer session; grid content is the same for all site locales.

Low-level single-task capture (both modes):

```bash
# Field canvas (website task pages) — batch uses this automatically
python tools/capture_robot_task_screenshots.py --viewer --field-canvas \
  --task if3 --env-index 0 --output-dir website/img/tasks --languages en

# Full window (marketing)
python tools/capture_robot_task_screenshots.py --viewer --task if3 \
  --output-dir website/img/viewer --languages ru en
```

Use the **batch** script for all task environments; do not rely on the default `viewer_` filename prefix from the low-level tool when naming files for the site.

## Prerequisites (capture machine)

1. **OS**: Linux with a visible desktop (`DISPLAY` set). Not suitable for headless CI.
2. **Python**: project interpreter with working `tkinter`, run from the repository root.
3. **Field canvas (sharp PNGs)**: ImageMagick **`import`** for 1:1 screen crop of the canvas rectangle; fallback PostScript conversion via **`convert`** / **`magick`** / **`gs`** if `import` is missing (slightly softer).
4. **Full window**: **`wmctrl`** and **`gnome-screenshot`**.
5. **Session**: avoid using the machine during a long batch run (windows are focused for capture).

Regenerate HTML when tasks or copy change (optional before spot-checking pages):

```bash
python tools/build_website_content.py
```

## Batch workflow (task field images)

Rough scale: ~194 tasks, ~351 environments, **351** PNG files (`{task_id}_env{index}.png`). A full run often takes on the order of **30–60 minutes**.

1. **Pilot** — one task:

   ```bash
   python tools/capture_all_task_screenshots.py --task if3
   ```

   Expect `if3_env0.png`, `if3_env1.png`. Check `website/tasks/if3.html` and `if3_ru.html` via a local server (`python -m http.server` in `website/`): both pages should show the same `<img src="…/if3_envN.png">` with sharp field grids.

2. **Theme pilot** — stability and file sizes:

   ```bash
   python tools/capture_all_task_screenshots.py --theme intro
   ```

   Or several tasks: `--task intro1 --task intro2`.

3. **Full batch**:

   ```bash
   python tools/capture_all_task_screenshots.py
   ```

4. **Verification**:

   ```bash
   find website/img/tasks -name '*.png' | wc -l
   ```

   Expect **351** files. Spot-check a few tasks (e.g. `if3`, multi-env tasks, Russian pages). Re-running overwrites existing PNGs; use `--skip-existing` to resume after a partial failure.

### Batch options

| Flag | Purpose |
|------|---------|
| `--task ID` | Limit to specific task ids (repeatable) |
| `--theme PREFIX` | All tasks in a theme, e.g. `intro`, `if` (repeatable) |
| `--dry-run` | Print expected PNG paths without opening the GUI |
| `--skip-existing` | Skip files that already exist |
| `--output-dir PATH` | Default: `website/img/tasks` |

Exit code **1** if any capture failed; failures are listed at the end.

## Git and CI

- `website/img/tasks/` is **not** gitignored; commit PNGs in a **separate** commit (large diff).
- Do **not** run screenshot capture in CI: it requires a graphical session and is environment-dependent.

## Related

- [`AGENTS.md`](../AGENTS.md) — project overview and website directory layout.
- [`tools/build_website_content.py`](../tools/build_website_content.py) — task pages, commands reference, `sitemap.xml`.
- [`Docs/task-viewer.md`](task-viewer.md) — viewer mode used during capture.
