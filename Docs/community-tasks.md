# Community task packs (`community/`)

Optional Robot task sets contributed by external authors. They are **not** bundled in [`robot/tasks/`](../robot/tasks/). The static website now shows them in a separate **Community tasks** section after the bundled themes, but the desktop module still loads them only when the user places the files into their own task directory (for example `robot/tasks/` in a local unpacked copy, or another folder selected via `ROBOT_TASKS_DIR`).

## Directory layout

Each pack lives in its own subdirectory under [`community/`](../community/). The folder name (`pack1`, `pack2`, …) is an internal identifier; release archives are named from the pack `prefix` (see below).

Example:

```
community/
  pack1/
    readme.md
    rintro1.env
    rintro2.env
    ...
```

- All task files and `readme.md` sit **directly** in the pack folder. Do not use nested subdirectories inside a pack.
- Task file format: [`Docs/task-env-format.md`](task-env-format.md). Follow [`Docs/localization-style.md`](localization-style.md) for `todoText` when writing or editing conditions.

## `readme.md`

Each pack must include a `readme.md` with YAML front matter:

| Field | Type | Purpose |
| ----- | ---- | ------- |
| `author` | string | Author name |
| `prefix` | string | Task id prefix and release zip name component (must be unique across packs) |

Example ([`community/pack1/readme.md`](../community/pack1/readme.md)):

```yaml
---
author: "Александр Родюшкин"
prefix: "r"
---
```

Rules:

- **`prefix`** must be unique among all packs under `community/`.
- Task ids should start with the pack prefix, e.g. `rintro1`, `rw3` for prefix `r`.

## Task file names

Use `{prefix}{theme}{number}.env`, where `{theme}` is a short topic slug and `{number}` is a numeric suffix (same convention as bundled tasks). The catalog groups tasks by theme before trailing digits (see [`robot/task_catalog.py`](../robot/task_catalog.py)).

## Using a community pack

1. Download [`{prefix}tasks.zip`](https://github.com/step-in-dev/robot/releases/latest/download/{prefix}tasks.zip) (e.g. [`rtasks.zip`](https://github.com/step-in-dev/robot/releases/latest/download/rtasks.zip) for prefix `r`).
2. Unpack the archive into a folder that contains only the `.env` files (and optionally `readme.md`).
3. Point the simulator at that folder:
   - Set the `ROBOT_TASKS_DIR` environment variable to the unpacked directory, **or**
   - Copy the `.env` files into a directory your workflow already uses for custom tasks, including `robot/tasks/` in your local unpacked module copy if that is more convenient.
4. Run student solutions with `task("rintro1")` (use the actual task id), or browse tasks with `python viewer/viewer.py` when `ROBOT_TASKS_DIR` is set.

Bundled tasks in `robot/tasks/` remain available when `ROBOT_TASKS_DIR` is not set. When it is set, the loader and viewer use only that directory.

## On the static website

The generated site keeps community tasks separate from bundled tasks:

- The main catalog page shows bundled themes first, then **Community tasks**.
- Each pack gets one catalog card with its heading, for example `Task set 1. Prepared by: …`, a direct download link to `{prefix}tasks.zip`, and a compact list of theme links inside the card.
- Themes inside a pack are grouped from task ids **after removing the pack prefix**, so `rintro1` and `rintro2` appear under the `intro` theme inside the `r` pack.
- Community theme hubs use URLs such as `tasks/community/r/intro/index.html`.
- Individual community task pages still use the task id at the root of `tasks/`, for example `tasks/rintro1.html`.

## Adding a new pack

1. Create `community/packN/` with a new unique `prefix` in `readme.md`.
2. Add `.env` task files in the pack root (no subfolders).
3. Ensure task ids match the prefix and theme numbering used in the pack.
4. On the next tagged release, CI builds `{prefix}tasks.zip` and attaches it to the GitHub Release.

## Building release archives

Implementation: [`tools/build_community_packs.py`](../tools/build_community_packs.py), invoked from [`.github/workflows/ci-release.yml`](../.github/workflows/ci-release.yml) when a version tag is published.

For each `community/pack*/` directory the builder:

1. Reads `prefix` from `readme.md` front matter.
2. Zips **only regular files** in the pack root (no subdirectories) into `{prefix}tasks.zip`.
3. Publishes the zip alongside `robot-vX.zip` on GitHub Releases.

Local build (from the repository root, with build dependencies installed):

```bash
python tools/build_community_packs.py --output-dir .
```

This writes `rtasks.zip` (and any other pack archives) into the chosen output directory.
