from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from robot.i18n import SUPPORTED_LANGUAGES
from robot.loader import TaskLoadError, load_task_definition


def _require_command(cmd: str) -> None:
    if subprocess.run(
        ["bash", "-lc", f"command -v {cmd}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode != 0:
        raise RuntimeError(f"Required command not found: {cmd}")


def _all_window_ids() -> set[str]:
    proc = subprocess.run(
        ["wmctrl", "-l"],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return set()

    ids: set[str] = set()
    for line in proc.stdout.splitlines():
        parts = line.split(None, 1)
        if not parts:
            continue
        ids.add(parts[0])
    return ids


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
) -> str:
    """Code run in a subprocess to open the Robot window for *task_id*."""
    if env_index is None:
        return textwrap.dedent(
            f"""
            from robot import *

            task({task_id!r})
            """
        )
    return textwrap.dedent(
        f"""
        import sys

        from robot.loader import load_task_definition
        from robot.runtime import _launch_student_robot_window

        task_id = {task_id!r}
        env_index = {env_index}

        td = load_task_definition(task_id)
        if env_index < 0 or env_index >= len(td.envs):
            print(
                f"env_index must be in 0..{{len(td.envs) - 1}}, got {{env_index}}",
                file=sys.stderr,
            )
            sys.exit(2)

        _launch_student_robot_window(
            task_id=task_id,
            envs=td.envs,
            initial_index=env_index,
            todo_text=td.todo_text,
            operators_limit=td.operators_limit,
            custom_function_call_count=td.custom_function_call_count,
            if_limit=td.if_limit,
            while_limit=td.while_limit,
            required_keywords=td.required_keywords,
            banned_keywords=td.banned_keywords,
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
) -> None:
    script_body = _script_body_for_task(task_id=task_id, env_index=env_index)

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
        window_id = _find_new_window_id(
            before_ids=before_ids, proc=proc, timeout_seconds=12.0
        )
        subprocess.run(["wmctrl", "-ia", window_id], check=True)
        time.sleep(0.25)
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

    failed: list[tuple[str, str]] = []
    for language in args.languages:
        if args.env_index is None:
            stem = f"{args.task}_{language}"
        else:
            stem = f"{args.task}_env{args.env_index}_{language}"
        output_path = output_dir / f"{stem}.png"
        print(f"[{language}] capturing -> {output_path}")
        try:
            capture_for_language(
                python_executable=sys.executable,
                task_id=args.task,
                language=language,
                output_path=output_path,
                workdir=workdir,
                env_index=args.env_index,
            )
        except Exception as exc:  # noqa: BLE001
            failed.append((language, str(exc)))
            print(f"[{language}] FAILED: {exc}")
        else:
            print(f"[{language}] OK")

    if failed:
        print("\nSome languages failed:")
        for lang, reason in failed:
            print(f" - {lang}: {reason}")
        return 1

    print("\nAll screenshots captured successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
