"""Capture field-canvas WebPs for bundled or community task environments."""

from __future__ import annotations

from typing import List, Tuple
import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
_TOOLS_DIR = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

# pylint: disable=wrong-import-position
from capture_robot_task_screenshots import (
    LanguageCaptureJob,
    _CaptureBatchContext,
    _try_capture,
    capture_for_language,
)
from robot.loader import TaskLoadError, load_task_definition
from tools.site_catalog import SiteTaskCatalog, discover_site_catalog
from tools.site_task_load import load_task_from_path
# pylint: enable=wrong-import-position

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "website" / "img" / "tasks"
SITE_CAPTURE_LANGUAGE = "en"


@dataclass(frozen=True)
class _CaptureOptions:
    """Shared batch options for one capture_all_task_screenshots run."""

    output_dir: Path
    settle_seconds: float
    skip_existing: bool


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for batch per-environment task screenshots."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for WebP files (default: website/img/tasks).",
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
        help="Skip captures when the output WebP already exists.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print expected output paths without launching the GUI.",
    )
    parser.add_argument(
        "--community-only",
        action="store_true",
        help="Capture only community pack tasks.",
    )
    parser.add_argument(
        "--pack-prefix",
        action="append",
        metavar="PREFIX",
        help=(
            "Limit community capture to these pack prefixes (repeatable). "
            "Requires --community-only."
        ),
    )
    return parser.parse_args()


def validate_capture_args(args: argparse.Namespace) -> None:
    """Raise ``ValueError`` when CLI flag combinations are invalid."""
    if args.pack_prefix and not args.community_only:
        raise ValueError("--pack-prefix requires --community-only")


def resolve_task_ids(catalog: SiteTaskCatalog, args: argparse.Namespace) -> List[str]:
    """Build ordered task ids from bundled/community selection flags."""
    bundled = catalog.bundled
    if args.task or args.theme or args.community_only:
        seen: set[str] = set()
        ordered: List[str] = []

        def add_task_id(task_id: str) -> None:
            if task_id not in seen:
                seen.add(task_id)
                ordered.append(task_id)

        for task_id in args.task or []:
            add_task_id(task_id)
        for prefix in args.theme or []:
            for task_id in bundled.task_ids_for(prefix):
                add_task_id(task_id)
        if args.community_only:
            selected_prefixes = set(args.pack_prefix or [])
            for pack in catalog.community_packs:
                if selected_prefixes and pack.prefix not in selected_prefixes:
                    continue
                for task_id in pack.all_task_ids():
                    add_task_id(task_id)
        return ordered
    return [
        task_id
        for theme in bundled.themes
        for task_id in bundled.task_ids_for(theme)
    ]


def _task_definition_and_tasks_dir(catalog: SiteTaskCatalog, task_id: str):
    """Return loaded task definition and optional source directory for ``task_id``."""
    location = catalog.locate_community_task(task_id)
    if location is None:
        return load_task_definition(task_id), None
    return load_task_from_path(location.path), location.pack.directory


def expected_output_paths(
    catalog: SiteTaskCatalog,
    task_ids: List[str],
    output_dir: Path,
) -> List[Path]:
    """Return every WebP path the batch would attempt for *task_ids*."""
    paths: List[Path] = []
    for task_id in task_ids:
        try:
            task_def, _tasks_dir = _task_definition_and_tasks_dir(catalog, task_id)
        except TaskLoadError:
            continue
        for env_index in range(len(task_def.envs)):
            paths.append(output_dir / f"{task_id}_env{env_index}.webp")
    return paths


def capture_task_envs(
    *,
    catalog: SiteTaskCatalog,
    task_id: str,
    options: _CaptureOptions,
    failed: List[Tuple[str, str]],
) -> None:
    """Capture one WebP per environment for *task_id* in viewer mode."""
    try:
        task_def, tasks_dir = _task_definition_and_tasks_dir(catalog, task_id)
    except TaskLoadError as exc:
        failed.append((task_id, str(exc)))
        print(f"SKIP {task_id}: {exc}", file=sys.stderr)
        return

    for env_index in range(len(task_def.envs)):
        batch = _CaptureBatchContext(
            task_id=task_id,
            workdir=PROJECT_ROOT,
            env_index=env_index,
            settle_seconds=options.settle_seconds,
        )
        output_path = options.output_dir / f"{task_id}_env{env_index}.webp"
        label = f"{task_id}/env{env_index}"
        if options.skip_existing and output_path.is_file():
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
                    tasks_dir=tasks_dir,
                )
            ),
        )


def main() -> int:
    """Capture field-canvas WebPs for selected catalog tasks and report failures."""
    args = parse_args()
    try:
        validate_capture_args(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    output_dir = args.output_dir.resolve()

    catalog = discover_site_catalog()
    task_ids = resolve_task_ids(catalog, args)

    if args.dry_run:
        paths = expected_output_paths(catalog, task_ids, output_dir)
        for path in paths:
            print(path)
        print(f"\n{len(paths)} WebP(s) for {len(task_ids)} task(s)")
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    options = _CaptureOptions(
        output_dir=output_dir,
        settle_seconds=args.settle_seconds,
        skip_existing=args.skip_existing,
    )

    failed: List[Tuple[str, str]] = []
    for index, task_id in enumerate(task_ids, start=1):
        print(f"\n=== [{index}/{len(task_ids)}] {task_id} ===")
        capture_task_envs(
            catalog=catalog,
            task_id=task_id,
            options=options,
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
