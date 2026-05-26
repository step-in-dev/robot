from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
from collections.abc import Callable
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from robot.gui_constraints import task_has_any_constraints
from robot.i18n import SUPPORTED_LANGUAGES, t
from robot.loader import TaskLoadError, load_task_definition


def _require_command(cmd: str) -> None:
    if subprocess.run(
        ["bash", "-lc", f"command -v {cmd}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode != 0:
        raise RuntimeError(f"Required command not found: {cmd}")


def _wmctrl_list_windows() -> list[tuple[str, str]]:
    """Return ``(window_id, title)`` entries from ``wmctrl -l``."""
    proc = subprocess.run(
        ["wmctrl", "-l"],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return []

    rows: list[tuple[str, str]] = []
    for line in proc.stdout.splitlines():
        parts = line.split(None, 3)
        if len(parts) < 4:
            continue
        win_id, _desk, _host, title = parts
        rows.append((win_id, title))
    return rows


def _all_window_ids() -> set[str]:
    return {win_id for win_id, _title in _wmctrl_list_windows()}


def _find_new_window_id(
    *,
    before_ids: set[str],
    proc: subprocess.Popen[bytes],
    timeout_seconds: float = 10.0,
) -> str:
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
    exclude_ids: set[str],
    expected_title: str,
    proc: subprocess.Popen[bytes],
    timeout_seconds: float = 12.0,
) -> str:
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


def _script_body_for_task(
    *,
    task_id: str,
    env_index: int | None,
    open_constraints_on_startup: bool,
) -> str:
    """Code run in a subprocess to open the Robot window for *task_id*."""
    env_index_literal = "None" if env_index is None else str(env_index)
    oc = "True" if open_constraints_on_startup else "False"
    return textwrap.dedent(
        f"""
        import sys

        from robot.loader import load_task_definition
        from robot.runtime import _launch_student_robot_window

        task_id = {task_id!r}
        env_index = {env_index_literal}
        open_constraints_on_startup = {oc}

        td = load_task_definition(task_id)
        if env_index is not None:
            if env_index < 0 or env_index >= len(td.envs):
                print(
                    f"env_index must be in 0..{{len(td.envs) - 1}}, got {{env_index}}",
                    file=sys.stderr,
                )
                sys.exit(2)
            initial_index = env_index
        else:
            initial_index = 0

        _launch_student_robot_window(
            task_id=task_id,
            task_definition=td,
            initial_index=initial_index,
            open_constraints_on_startup=open_constraints_on_startup,
        )
        """
    )


def capture_for_language(
    *,
    python_executable: str,
    task_id: str,
    language: str,
    output_path: Path,
    workdir: Path,
    env_index: int | None,
    capture_constraints_window: bool,
) -> None:
    script_body = _script_body_for_task(
        task_id=task_id,
        env_index=env_index,
        open_constraints_on_startup=capture_constraints_window,
    )

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".py",
        prefix="tmp_robot_task_",
        delete=False,
        dir=workdir,
    ) as f:
        f.write(script_body)
        script_path = Path(f.name)

    env = os.environ.copy()
    env["ROBOT_LANGUAGE"] = language
    env["PYTHONUNBUFFERED"] = "1"

    proc: subprocess.Popen[bytes] | None = None
    try:
        before_ids = _all_window_ids()
        proc = subprocess.Popen(
            [python_executable, str(script_path)],
            cwd=str(workdir),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        main_window_id = _find_new_window_id(
            before_ids=before_ids, proc=proc, timeout_seconds=12.0
        )
        subprocess.run(["wmctrl", "-ia", main_window_id], check=True)
        time.sleep(0.25)

        if capture_constraints_window:
            time.sleep(0.55)
            expected_title = _constraints_dialog_title_for_language(language)
            constraints_id = _find_constraints_window_id(
                exclude_ids=before_ids | {main_window_id},
                expected_title=expected_title,
                proc=proc,
                timeout_seconds=12.0,
            )
            subprocess.run(["wmctrl", "-ia", constraints_id], check=True)
            time.sleep(0.2)

        subprocess.run(
            ["gnome-screenshot", "-w", "-f", str(output_path)],
            check=True,
        )
    finally:
        if proc is not None:
            _stop_process(proc)
        script_path.unlink(missing_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run robot task for each supported language and save "
            "window screenshots (with OS title bar)."
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
    return parser.parse_args()


def _validate_env_index_for_task(task_id: str, env_index: int) -> int | None:
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
    if not task_has_any_constraints(
        operators_limit=td.operators_limit,
        custom_function_call_count=td.custom_function_call_count,
        if_limit=td.if_limit,
        while_limit=td.while_limit,
        required_keywords=td.required_keywords,
        banned_keywords=td.banned_keywords,
    ):
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
    failed: list[tuple[str, str]],
    capture: Callable[[], None],
) -> None:
    print(intro_line)
    try:
        capture()
    except Exception as exc:  # noqa: BLE001
        failed.append((label, str(exc)))
        print(f"{ok_prefix}FAILED: {exc}")
    else:
        print(f"{ok_prefix}OK")


def main() -> int:
    args = parse_args()

    _require_command("wmctrl")
    _require_command("gnome-screenshot")

    workdir = PROJECT_ROOT
    output_dir = (workdir / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.env_index is not None:
        if _validate_env_index_for_task(args.task, args.env_index) != 0:
            return 1

    if args.constraints and _validate_task_has_constraints_for_flag(args.task) != 0:
        return 1

    failed: list[tuple[str, str]] = []
    for language in args.languages:
        if args.env_index is None:
            stem = f"{args.task}_{language}"
        else:
            stem = f"{args.task}_env{args.env_index}_{language}"
        output_path = output_dir / f"{stem}.png"
        _try_capture(
            label=language,
            intro_line=f"[{language}] capturing -> {output_path}",
            ok_prefix=f"[{language}] ",
            failed=failed,
            capture=lambda lang=language, path=output_path: capture_for_language(
                python_executable=sys.executable,
                task_id=args.task,
                language=lang,
                output_path=path,
                workdir=workdir,
                env_index=args.env_index,
                capture_constraints_window=False,
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
                    python_executable=sys.executable,
                    task_id=args.task,
                    language=lang,
                    output_path=path,
                    workdir=workdir,
                    env_index=args.env_index,
                    capture_constraints_window=True,
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
