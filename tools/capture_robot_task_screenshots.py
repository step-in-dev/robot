"""Capture Robot window screenshots (Linux)."""

from __future__ import annotations

from typing import Callable, List, Optional, Set, Tuple
import argparse
import os
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# robot imports follow sys.path setup so this tool runs without package install.
# pylint: disable=wrong-import-position
from robot.gui_constraints import task_has_any_constraints
from robot.i18n import SUPPORTED_LANGUAGES, t
from robot.loader import TaskLoadError, load_task_definition
# pylint: enable=wrong-import-position


def _lossless_png_to_webp(png_path: Path, webp_path: Path) -> None:
    """Convert ``png_path`` to lossless WebP at ``webp_path``."""
    proc = subprocess.run(
        ["cwebp", "-lossless", str(png_path), "-o", str(webp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(
            f"cwebp failed with code {proc.returncode}"
            + (f": {detail}" if detail else "")
        )


def _field_canvas_png_path(output_path: Path) -> Path:
    """Return the temporary PNG path used while exporting a WebP field screenshot."""
    if output_path.suffix.lower() == ".webp":
        return output_path.with_suffix(".png")
    return output_path


def _require_command(cmd: str) -> None:
    """Raise when ``cmd`` is not available on ``PATH``."""
    if subprocess.run(
        ["bash", "-lc", f"command -v {cmd}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode != 0:
        raise RuntimeError(f"Required command not found: {cmd}")


def _wmctrl_list_windows() -> List[Tuple[str, str]]:
    """Return ``(window_id, title)`` entries from ``wmctrl -l``."""
    proc = subprocess.run(
        ["wmctrl", "-l"],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return []

    rows: List[Tuple[str, str]] = []
    for line in proc.stdout.splitlines():
        parts = line.split(None, 3)
        if len(parts) < 4:
            continue
        win_id, _desk, _host, title = parts
        rows.append((win_id, title))
    return rows


def _all_window_ids() -> Set[str]:
    """Return window ids reported by ``wmctrl -l``."""
    return {win_id for win_id, _title in _wmctrl_list_windows()}


def _find_new_window_id(
    *,
    before_ids: Set[str],
    proc: subprocess.Popen[bytes],
    timeout_seconds: float = 10.0,
) -> str:
    """Wait for a new window opened by ``proc`` and return its id."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        current_ids = _all_window_ids()
        new_ids = current_ids - before_ids
        if new_ids:
            return min(new_ids)
        if proc.poll() is not None:
            raise RuntimeError(
                f"Robot process exited before opening window (code={proc.returncode})"
            )
        time.sleep(0.1)
    raise TimeoutError("Robot window was not found")


def _constraints_dialog_title_for_language(language: str) -> str:
    """Localized ``constraints.title`` for *language* (matches WM window title)."""
    previous = os.environ.get("ROBOT_LANGUAGE")
    os.environ["ROBOT_LANGUAGE"] = language
    try:
        return t("constraints.title")
    finally:
        if previous is None:
            os.environ.pop("ROBOT_LANGUAGE", None)
        else:
            os.environ["ROBOT_LANGUAGE"] = previous


def _find_constraints_window_id(
    *,
    exclude_ids: Set[str],
    expected_title: str,
    proc: subprocess.Popen[bytes],
    timeout_seconds: float = 12.0,
) -> str:
    """Wait for the constraints dialog window and return its id."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        for win_id, title in _wmctrl_list_windows():
            if win_id in exclude_ids:
                continue
            if title == expected_title:
                return win_id
        if proc.poll() is not None:
            raise RuntimeError(
                "Robot process exited before the constraints window appeared "
                f"(code={proc.returncode})"
            )
        time.sleep(0.1)
    raise TimeoutError(
        f"Constraints window with title {expected_title!r} was not found "
        "(does this task define any limits?)"
    )


def _stop_process(proc: subprocess.Popen[bytes]) -> None:
    """Terminate ``proc``, escalating to SIGKILL when needed."""
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=2.0)
        return
    except subprocess.TimeoutExpired:
        pass
    proc.send_signal(signal.SIGKILL)
    proc.wait(timeout=2.0)


def _field_export_footer() -> str:
    return """import os
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

export_path = os.environ.get("ROBOT_FIELD_SCREENSHOT_PATH")
if not export_path:
    print("ROBOT_FIELD_SCREENSHOT_PATH is not set", file=sys.stderr)
    sys.exit(3)

from tools.field_canvas_export import write_robot_window_field_canvas

write_robot_window_field_canvas(window, Path(export_path))
window.close()
"""


def _env_index_prelude() -> str:
    return """td = load_task_definition(task_id)
if env_index is not None:
    if env_index < 0 or env_index >= len(td.envs):
        print(
            f"env_index must be in 0..{len(td.envs) - 1}, got {env_index}",
            file=sys.stderr,
        )
        sys.exit(2)
    initial_index = env_index
else:
    initial_index = 0
"""


def _script_body_for_capture(
    *,
    task_id: str,
    env_index: Optional[int],
    viewer_mode: bool,
    open_constraints_on_startup: bool,
    field_canvas_only: bool,
) -> Tuple[str, str]:
    """Return subprocess script source and a tempfile prefix for the capture mode."""
    env_index_literal = "None" if env_index is None else str(env_index)
    tail = _field_export_footer() if field_canvas_only else "window.run()\n"
    prelude = _env_index_prelude()

    if viewer_mode:
        prefix = "tmp_robot_viewer_"
        body = f"""import sys

from robot.gui import RobotWindow, RobotWindowOptions
from robot.loader import load_task_definition
from robot.task_catalog import TaskCatalog

task_id = {task_id!r}
env_index = {env_index_literal}

{prelude}
catalog = TaskCatalog.discover()

window = RobotWindow(
    task_id,
    td,
    None,
    RobotWindowOptions(
        initial_index=initial_index,
        viewer_catalog=catalog,
    ),
)
{tail}"""
    else:
        oc = "True" if open_constraints_on_startup else "False"
        prefix = "tmp_robot_task_"
        if field_canvas_only:
            body = f"""import sys

from robot.gui import RobotWindow, RobotWindowOptions
from robot.loader import load_task_definition

task_id = {task_id!r}
env_index = {env_index_literal}

{prelude}
window = RobotWindow(
    task_id,
    td,
    None,
    RobotWindowOptions(
        initial_index=initial_index,
        open_constraints_on_startup={oc},
    ),
)
{tail}"""
        else:
            body = f"""import sys

from robot.loader import load_task_definition
from robot.runtime import _launch_student_robot_window

task_id = {task_id!r}
env_index = {env_index_literal}
open_constraints_on_startup = {oc}

{prelude}
_launch_student_robot_window(
    task_id=task_id,
    task_definition=td,
    initial_index=initial_index,
    open_constraints_on_startup=open_constraints_on_startup,
)
"""

    return body, prefix


def _default_settle_seconds(*, viewer_mode: bool, override: Optional[float]) -> float:
    """Return screenshot settle time for viewer or student mode."""
    if override is not None:
        return override
    if viewer_mode:
        return 0.85
    return 0.25


def _effective_output_prefix(output_prefix: str, viewer_mode: bool) -> str:
    """Apply default ``viewer_`` prefix in viewer mode when unset."""
    if viewer_mode and not output_prefix:
        return "viewer_"
    return output_prefix


def _screenshot_stem(
    *,
    output_prefix: str,
    task_id: str,
    language: str,
    env_index: Optional[int],
) -> str:
    """Build output filename stem for one language capture."""
    if env_index is None:
        return f"{output_prefix}{task_id}_{language}"
    return f"{output_prefix}{task_id}_env{env_index}_{language}"


@dataclass(frozen=True)
class LanguageCaptureJob:  # pylint: disable=too-many-instance-attributes
    """Flat parameter bundle for one language screenshot capture run."""

    python_executable: str
    task_id: str
    language: str
    output_path: Path
    workdir: Path
    env_index: Optional[int]
    capture_constraints_window: bool
    viewer_mode: bool
    field_canvas_only: bool
    settle_seconds: float


@dataclass(frozen=True)
class _ScreenshotCaptureFlags:
    """Viewer, constraints, and canvas options for one language capture."""

    capture_constraints_window: bool
    viewer_mode: bool
    field_canvas_only: bool


@dataclass(frozen=True)
class _CaptureBatchContext:
    """Shared parameters for all language/env captures in one CLI run."""

    task_id: str
    workdir: Path
    env_index: Optional[int]
    settle_seconds: float

    def language_job(
        self,
        language: str,
        output_path: Path,
        flags: _ScreenshotCaptureFlags,
    ) -> LanguageCaptureJob:
        """Build a capture job for one language using shared batch parameters."""
        return LanguageCaptureJob(
            python_executable=sys.executable,
            task_id=self.task_id,
            language=language,
            output_path=output_path,
            workdir=self.workdir,
            env_index=self.env_index,
            capture_constraints_window=flags.capture_constraints_window,
            viewer_mode=flags.viewer_mode,
            field_canvas_only=flags.field_canvas_only,
            settle_seconds=self.settle_seconds,
        )


def _require_field_canvas_converter() -> None:
    """Raise when field canvas export tools are missing."""
    for cmd in ("import", "convert", "magick", "gs"):
        if subprocess.run(
            ["bash", "-lc", f"command -v {cmd}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode == 0:
            return
    raise RuntimeError(
        "Field canvas export requires ImageMagick (`import` for sharp captures, "
        "or `convert`/`magick`/`gs` for PostScript fallback) on PATH"
    )


def capture_for_language(job: LanguageCaptureJob) -> None:
    """Launch Robot for one language and save a screenshot to ``output_path``."""
    if job.viewer_mode and job.capture_constraints_window:
        raise RuntimeError("Constraints capture is not supported in --viewer mode")
    if job.field_canvas_only and job.capture_constraints_window:
        raise RuntimeError(
            "Field canvas capture cannot be combined with --constraints"
        )

    script_body, script_prefix = _script_body_for_capture(
        task_id=job.task_id,
        env_index=job.env_index,
        viewer_mode=job.viewer_mode,
        open_constraints_on_startup=job.capture_constraints_window,
        field_canvas_only=job.field_canvas_only,
    )

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".py",
        prefix=script_prefix,
        delete=False,
        dir=job.workdir,
    ) as f:
        f.write(script_body)
        script_path = Path(f.name)

    env = os.environ.copy()
    env["ROBOT_LANGUAGE"] = job.language
    env["PYTHONUNBUFFERED"] = "1"
    field_png_path = _field_canvas_png_path(job.output_path)
    if job.field_canvas_only:
        env["ROBOT_FIELD_SCREENSHOT_PATH"] = str(field_png_path)

    if job.field_canvas_only:
        proc = subprocess.run(
            [job.python_executable, str(script_path)],
            cwd=str(job.workdir),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        script_path.unlink(missing_ok=True)
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip()
            raise RuntimeError(
                f"Robot field export exited with code {proc.returncode}"
                + (f": {detail}" if detail else "")
            )
        if not field_png_path.is_file():
            raise RuntimeError("Field canvas PNG was not written")
        if job.output_path != field_png_path:
            _lossless_png_to_webp(field_png_path, job.output_path)
            field_png_path.unlink(missing_ok=True)
        return

    before_ids = _all_window_ids()
    try:
        with subprocess.Popen(
            [job.python_executable, str(script_path)],
            cwd=str(job.workdir),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ) as proc:
            try:
                main_window_id = _find_new_window_id(
                    before_ids=before_ids, proc=proc, timeout_seconds=12.0
                )
                subprocess.run(["wmctrl", "-ia", main_window_id], check=True)
                time.sleep(job.settle_seconds)

                if job.capture_constraints_window:
                    time.sleep(0.55)
                    expected_title = _constraints_dialog_title_for_language(
                        job.language
                    )
                    constraints_id = _find_constraints_window_id(
                        exclude_ids=before_ids | {main_window_id},
                        expected_title=expected_title,
                        proc=proc,
                        timeout_seconds=12.0,
                    )
                    subprocess.run(["wmctrl", "-ia", constraints_id], check=True)
                    time.sleep(0.2)

                subprocess.run(
                    ["gnome-screenshot", "-w", "-f", str(job.output_path)],
                    check=True,
                )
            finally:
                _stop_process(proc)
    finally:
        script_path.unlink(missing_ok=True)


def parse_args() -> argparse.Namespace:
    """Parse command-line options for the screenshot capture tool."""
    parser = argparse.ArgumentParser(
        description=(
            "Run robot task for each supported language and save screenshots. "
            "By default captures the whole window (with OS title bar); "
            "use --field-canvas for the field grid canvas only."
        )
    )
    parser.add_argument(
        "--task",
        default="fun17",
        help="Task id for task('<id>'). Default: fun17",
    )
    parser.add_argument(
        "--env-index",
        type=int,
        default=None,
        metavar="N",
        help=(
            "If set, capture with environment N (0-based index in the task's "
            "envDtos) initially selected. All environments stay loaded so "
            "environment switcher tabs remain visible. If omitted, opens the "
            "task with the default initial environment (usually 0)."
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="screenshots_by_language",
        help="Directory where PNG files are written.",
    )
    parser.add_argument(
        "--languages",
        nargs="*",
        default=list(SUPPORTED_LANGUAGES),
        help=(
            "Optional language codes. If omitted, uses all supported languages "
            "from robot.i18n.SUPPORTED_LANGUAGES."
        ),
    )
    parser.add_argument(
        "--constraints",
        action="store_true",
        help=(
            "Also save <stem>_constraints.png per language: opens the "
            "Constraints dialog (same as the Constraints button) and captures "
            "that window. Requires the task to define at least one limit "
            "(operators, function calls, if/while, keywords)."
        ),
    )
    parser.add_argument(
        "--viewer",
        action="store_true",
        help=(
            "Open teacher task viewer mode (viewer_catalog) instead of a "
            "student solution window."
        ),
    )
    parser.add_argument(
        "--output-prefix",
        default="",
        help=(
            "Optional prefix for PNG filenames (e.g. viewer_ yields "
            "viewer_if3_ru.webp)."
        ),
    )
    parser.add_argument(
        "--settle-seconds",
        type=float,
        default=None,
        metavar="SEC",
        help=(
            "Seconds to wait after focusing the window before capture. "
            "Default: 0.85 for --viewer, 0.25 otherwise. Ignored with --field-canvas."
        ),
    )
    parser.add_argument(
        "--field-canvas",
        action="store_true",
        help=(
            "Export only the field grid canvas to PNG (no window chrome). "
            "Uses ImageMagick `import` for a 1:1 screen crop when available."
        ),
    )
    return parser.parse_args()


def _validate_env_index_for_task(task_id: str, env_index: int) -> Optional[int]:
    """Return 0 on success, 1 if the task cannot be loaded or *env_index* is invalid."""
    try:
        td = load_task_definition(task_id)
    except TaskLoadError as exc:
        print(f"Cannot load task {task_id!r}: {exc}", file=sys.stderr)
        return 1
    n = len(td.envs)
    if env_index < 0 or env_index >= n:
        print(
            f"--env-index must be between 0 and {n - 1} "
            f"({n} environment(s) in this task); got {env_index}",
            file=sys.stderr,
        )
        return 1
    return 0


def _validate_task_has_constraints_for_flag(task_id: str) -> int:
    """Return 0 if *task_id* has limits usable with ``--constraints``, else 1."""
    try:
        td = load_task_definition(task_id)
    except TaskLoadError as exc:
        print(f"Cannot load task {task_id!r}: {exc}", file=sys.stderr)
        return 1
    if not task_has_any_constraints(td.script_constraints):
        print(
            f"Task {task_id!r} has no constraints (--constraints needs "
            "operatorsLimit, customFunctionCallCount, if/while limits, or "
            "required/banned keywords).",
            file=sys.stderr,
        )
        return 1
    return 0


def _try_capture(
    *,
    label: str,
    intro_line: str,
    ok_prefix: str,
    failed: List[Tuple[str, str]],
    capture: Callable[[], None],
) -> None:
    """Run ``capture()`` and record failures for the summary report."""
    print(intro_line)
    try:
        capture()
    except Exception as exc:  # noqa: BLE001  # pylint: disable=broad-exception-caught
        # Batch runner records any capture failure and continues other languages.
        failed.append((label, str(exc)))
        print(f"{ok_prefix}FAILED: {exc}")
    else:
        print(f"{ok_prefix}OK")


def main() -> int:
    """Capture Robot window screenshots for each requested language."""
    args = parse_args()

    if args.field_canvas:
        _require_field_canvas_converter()
    else:
        _require_command("wmctrl")
        _require_command("gnome-screenshot")

    workdir = PROJECT_ROOT
    output_dir = (workdir / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.env_index is not None:
        if _validate_env_index_for_task(args.task, args.env_index) != 0:
            return 1

    if args.constraints and args.viewer:
        print("--constraints cannot be used with --viewer", file=sys.stderr)
        return 1

    if args.field_canvas and args.constraints:
        print("--field-canvas cannot be used with --constraints", file=sys.stderr)
        return 1

    if args.constraints and _validate_task_has_constraints_for_flag(args.task) != 0:
        return 1

    settle_seconds = _default_settle_seconds(
        viewer_mode=args.viewer,
        override=args.settle_seconds,
    )
    output_prefix = _effective_output_prefix(args.output_prefix, args.viewer)

    batch = _CaptureBatchContext(
        task_id=args.task,
        workdir=workdir,
        env_index=args.env_index,
        settle_seconds=settle_seconds,
    )

    failed: List[Tuple[str, str]] = []
    for language in args.languages:
        stem = _screenshot_stem(
            output_prefix=output_prefix,
            task_id=args.task,
            language=language,
            env_index=args.env_index,
        )
        output_path = output_dir / f"{stem}.png"
        _try_capture(
            label=language,
            intro_line=f"[{language}] capturing -> {output_path}",
            ok_prefix=f"[{language}] ",
            failed=failed,
            capture=lambda lang=language, path=output_path: capture_for_language(
                batch.language_job(
                    lang,
                    path,
                    _ScreenshotCaptureFlags(
                        capture_constraints_window=False,
                        viewer_mode=args.viewer,
                        field_canvas_only=args.field_canvas,
                    ),
                )
            ),
        )

        if args.constraints:
            constraints_path = output_dir / f"{stem}_constraints.png"
            _try_capture(
                label=f"{language}_constraints",
                intro_line=f"[{language}] constraints -> {constraints_path}",
                ok_prefix=f"[{language}] constraints ",
                failed=failed,
                capture=lambda lang=language, path=constraints_path: capture_for_language(
                    batch.language_job(
                        lang,
                        path,
                        _ScreenshotCaptureFlags(
                            capture_constraints_window=True,
                            viewer_mode=False,
                            field_canvas_only=False,
                        ),
                    )
                ),
            )

    if failed:
        print("\nSome languages failed:")
        for lang, reason in failed:
            print(f" - {lang}: {reason}")
        return 1

    print("\nAll screenshots captured successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
