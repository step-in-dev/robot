import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import call, patch

from robot.loader import load_task
from robot.model import RobotEnv, RobotEnvDto
from robot.runtime import run_solution_on_env


class LoaderRuntimeTest(unittest.TestCase):
    def test_loader_reads_web_environment_format(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            task_file = Path(temp_dir) / "line.json"
            task_file.write_text(
                json.dumps(
                    {
                        "environments": [
                            {
                                "width": 2,
                                "height": 1,
                                "startRow": 0,
                                "startCol": 0,
                                "finalRow": 0,
                                "finalCol": 1,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with patch.dict("os.environ", {"ROBOT_TASKS_DIR": temp_dir}):
                envs = load_task("line")

        self.assertEqual(len(envs), 1)
        self.assertEqual(envs[0].width, 2)
        self.assertEqual(envs[0].final_col, 1)

    def test_runtime_executes_student_file_in_clean_robot_context(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "solution.py"
            script.write_text(
                "from robot import *\n"
                "task('while1')\n"
                "while is_free_right():\n"
                "    move_right()\n",
                encoding="utf-8",
            )
            env = RobotEnv(
                RobotEnvDto.from_dict(
                    {
                        "width": 4,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 3,
                    }
                )
            )

            result = run_solution_on_env(script, "while1", env)

        self.assertTrue(result.success)
        self.assertEqual((env.robot.row, env.robot.col), (0, 3))

    def test_runtime_delays_only_mutating_commands_when_enabled(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "solution.py"
            script.write_text(
                "from robot import *\n"
                "task('delay')\n"
                "is_free_right()\n"
                "pol()\n"
                "move_right()\n"
                "paint()\n"
                "printn(7)\n",
                encoding="utf-8",
            )
            env = RobotEnv(
                RobotEnvDto.from_dict(
                    {
                        "width": 2,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 1,
                        "cellsToPaint": [{"r": 0, "c": 1}],
                        "cellsToPrint": [{"r": 0, "c": 1, "value": 7}],
                    }
                )
            )

            with patch("robot.runtime.time.sleep") as sleep:
                result = run_solution_on_env(
                    script,
                    "delay",
                    env,
                    command_delay_seconds=0.05,
                )

        self.assertTrue(result.success)
        self.assertEqual(
            sleep.call_args_list,
            [call(0.05), call(0.05), call(0.05)],
        )

    def test_runtime_reports_wrong_solution(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "solution.py"
            script.write_text(
                "from robot import *\n"
                "task('while1')\n",
                encoding="utf-8",
            )
            env = RobotEnv(
                RobotEnvDto.from_dict(
                    {
                        "width": 2,
                        "height": 1,
                        "startRow": 0,
                        "startCol": 0,
                        "finalRow": 0,
                        "finalCol": 1,
                    }
                )
            )

            result = run_solution_on_env(script, "while1", env)

        self.assertFalse(result.success)
        self.assertEqual(result.status, "wrong")


if __name__ == "__main__":
    unittest.main()
