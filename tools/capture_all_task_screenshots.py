"""Capture field-canvas PNGs for every task environment (one file per env)."""

from __future__ import annotations

from typing import List, Tuple
import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# pylint: disable=wrong-import-position
from robot.loader import TaskLoadError, load_task_definition
from robot.task_catalog import TaskCatalog

_TOOLS_DIR = Path(__file__).resolve().parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from capture_robot_task_screenshots import (  # noqa: E402
    LanguageCaptureJob,
    _CaptureBatchContext,
    _try_capture,
    capture_for_language,
)

# pylint: enable=wrong-import-position

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "website" / "img" / "tasks"
SITE_CAPTURE_LANGUAGE = "en"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for PNG files (default: website/img/tasks).",
    )
    parser.add_argument(
        "--task",
        action="append",
        metavar="ID",
        help="Capture only these task ids (repeatable). Default: all catalog tasks.",
    )
    parser.add_argument(
        "--theme",
        action="append",
        metavar="PREFIX",
        help="Capture all tasks in these theme prefixes (repeatable), e.g. intro, if.",
    )
    parser.add_argument(
        "--settle-seconds",
        type=float,
        default=0.85,
        help="Seconds to wait before each screenshot (default: 0.85).",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip captures when the output PNG already exists.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print expected output paths without launching the GUI.",
    )
    return parser.parse_args()


def resolve_task_ids(catalog: TaskCatalog, args: argparse.Namespace) -> List[str]:
    """Build ordered task id list from --task, --theme, or full catalog."""
    if args.task or args.theme:
        seen: set[str] = set()
        ordered: List[str] = []
        for task_id in args.task or []:
            if task_id not in seen:
                seen.add(task_id)
                ordered.append(task_id)
        for prefix in args.theme or []:
            for task_id in catalog.task_ids_for(prefix):
                if task_id not in seen:
                    seen.add(task_id)
                    ordered.append(task_id)
        return ordered
    return [
        task_id
        for theme in catalog.themes
        for task_id in catalog.task_ids_for(theme)
    ]


def expected_output_paths(task_ids: List[str], output_dir: Path) -> List[Path]:
    """Return every PNG path the batch would attempt for *task_ids*."""
    paths: List[Path] = []
    for task_id in task_ids:
        try:
            task_def = load_task_definition(task_id)
        except TaskLoadError:
            continue
        for env_index in range(len(task_def.envs)):
            paths.append(output_dir / f"{task_id}_env{env_index}.png")
    return paths


def capture_task_envs(
    *,
    task_id: str,
    output_dir: Path,
    settle_seconds: float,
    skip_existing: bool,
    failed: List[Tuple[str, str]],
) -> None:
    """Capture one PNG per environment for *task_id* in viewer mode."""
    try:
        task_def = load_task_definition(task_id)
    except TaskLoadError as exc:
        failed.append((task_id, str(exc)))
        print(f"SKIP {task_id}: {exc}", file=sys.stderr)
        return

    for env_index in range(len(task_def.envs)):
        batch = _CaptureBatchContext(
            task_id=task_id,
            workdir=PROJECT_ROOT,
            env_index=env_index,
            settle_seconds=settle_seconds,
        )
        output_path = output_dir / f"{task_id}_env{env_index}.png"
        label = f"{task_id}/env{env_index}"
        if skip_existing and output_path.is_file():
            print(f"[{label}] skip (exists)")
            continue
        _try_capture(
            label=label,
            intro_line=f"[{label}] -> {output_path}",
            ok_prefix=f"[{label}] ",
            failed=failed,
            capture=lambda path=output_path, b=batch: capture_for_language(
                LanguageCaptureJob(
                    python_executable=sys.executable,
                    task_id=b.task_id,
                    language=SITE_CAPTURE_LANGUAGE,
                    output_path=path,
                    workdir=b.workdir,
                    env_index=b.env_index,
                    capture_constraints_window=False,
                    viewer_mode=True,
                    field_canvas_only=True,
                    settle_seconds=b.settle_seconds,
                )
            ),
        )


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.resolve()

    catalog = TaskCatalog.discover()
    task_ids = resolve_task_ids(catalog, args)

    if args.dry_run:
        paths = expected_output_paths(task_ids, output_dir)
        for path in paths:
            print(path)
        print(f"\n{len(paths)} PNG(s) for {len(task_ids)} task(s)")
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)

    failed: List[Tuple[str, str]] = []
    for index, task_id in enumerate(task_ids, start=1):
        print(f"\n=== [{index}/{len(task_ids)}] {task_id} ===")
        capture_task_envs(
            task_id=task_id,
            output_dir=output_dir,
            settle_seconds=args.settle_seconds,
            skip_existing=args.skip_existing,
            failed=failed,
        )

    if failed:
        print("\nSome captures failed:")
        for label, reason in failed:
            print(f" - {label}: {reason}")
        return 1

    print(f"\nFinished. Screenshots in {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
