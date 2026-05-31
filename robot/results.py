"""Run outcome types and final-state checking."""

from __future__ import annotations

from dataclasses import dataclass

from .model import RobotEnv

RunStatus = str


@dataclass(frozen=True)
class RunResult:
    """Outcome of a solution run (status, message, details)."""

    status: RunStatus
    message: str
    details: str = ""

    @property
    def success(self) -> bool:
        """Return whether the run finished with status ``success``."""
        return self.status == "success"


def check_final_state(env: RobotEnv) -> RunResult:
    """Map environment final-state check to a ``RunResult``."""
    if env.is_in_final_state():
        return RunResult(status="success", message="")
    return RunResult(status="wrong", message="")
