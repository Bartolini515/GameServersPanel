import re
import subprocess
from collections.abc import Callable
from typing import Literal

from games.services.base import (
    ServiceCommandRejected,
    ServiceConflict,
    ServiceNotFound,
    ServiceProtocolError,
    ServiceTimeout,
    ServiceUnavailable,
)
from games.types import ProcessStatus

UNIT_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.@-]{0,243}\.service$")
STATUS_TIMEOUT_SECONDS = 2
ACTION_TIMEOUT_SECONDS = 3
SYSTEM_SYSTEMCTL_PATH = "/usr/bin/systemctl"
SYSTEM_SUDO_PATH = "/usr/bin/sudo"
SYSTEM_UNIT_NAME = "game-vintagestory.service"


class SystemdService:
    """Control configured user units or the fixed system unit."""

    def __init__(
        self,
        runner: Callable = subprocess.run,
        status_timeout: int = STATUS_TIMEOUT_SECONDS,
        action_timeout: int = ACTION_TIMEOUT_SECONDS,
        scope: Literal["user", "system"] = "user",
    ):
        if scope not in ("user", "system"):
            raise ValueError("Systemd scope must be 'user' or 'system'.")
        self._runner = runner
        self._status_timeout = status_timeout
        self._action_timeout = action_timeout
        self._scope = scope

    def _validate_unit(self, service: str) -> None:
        if not isinstance(service, str) or not UNIT_NAME_PATTERN.fullmatch(service):
            raise ServiceCommandRejected("Invalid configured systemd unit name.")
        if self._scope == "system" and service != SYSTEM_UNIT_NAME:
            raise ServiceCommandRejected("The system backend only supports its configured unit.")

    def _status_command(self) -> list[str]:
        if self._scope == "system":
            return [SYSTEM_SYSTEMCTL_PATH, "--system"]
        return ["systemctl", "--user"]

    def _action_command(self) -> list[str]:
        if self._scope == "system":
            return [SYSTEM_SUDO_PATH, "-n", SYSTEM_SYSTEMCTL_PATH, "--system"]
        return ["systemctl", "--user"]

    def _run(self, args: list[str], timeout: int):
        try:
            result = self._runner(
                args,
                timeout=timeout,
                check=False,
                shell=False,
                capture_output=True,
                text=True,
            )
        except subprocess.TimeoutExpired as exc:
            raise ServiceTimeout("The systemd request timed out.") from exc
        except OSError as exc:
            raise ServiceUnavailable(
                "The configured service command could not be reached."
            ) from exc
        return result

    @staticmethod
    def _parse_properties(output: str) -> dict[str, str]:
        properties = {}
        for line in output.splitlines():
            if not line:
                continue
            key, separator, value = line.partition("=")
            if not separator or not key or key in properties:
                raise ServiceProtocolError("systemd returned malformed unit properties.")
            properties[key] = value
        return properties

    def status(self, service: str) -> ProcessStatus:
        self._validate_unit(service)
        result = self._run(
            [
                *self._status_command(),
                "--no-pager",
                "show",
                "--property=LoadState",
                "--property=ActiveState",
                "--property=SubState",
                "--property=MainPID",
                service,
            ],
            timeout=self._status_timeout,
        )
        properties = self._parse_properties(result.stdout or "")
        load_state = properties.get("LoadState")
        if load_state == "not-found":
            raise ServiceNotFound("The configured systemd unit does not exist.")
        if load_state == "masked":
            raise ServiceCommandRejected("The configured systemd unit cannot be operated.")
        if result.returncode != 0:
            raise ServiceCommandRejected("systemd could not read the configured unit.")

        active_state = properties.get("ActiveState")
        sub_state = properties.get("SubState")
        main_pid_text = properties.get("MainPID")
        if load_state != "loaded" or not active_state or not sub_state or main_pid_text is None:
            raise ServiceProtocolError("systemd returned incomplete unit properties.")
        try:
            main_pid = int(main_pid_text)
        except ValueError as exc:
            raise ServiceProtocolError("systemd returned an invalid MainPID value.") from exc

        if active_state == "inactive":
            return ProcessStatus.STOPPED
        if active_state == "activating":
            return ProcessStatus.STARTING
        if active_state == "deactivating":
            return ProcessStatus.STOPPING
        if active_state == "failed":
            return ProcessStatus.FAILED
        if active_state == "active" and sub_state == "running" and main_pid > 0:
            return ProcessStatus.RUNNING
        raise ServiceProtocolError("systemd returned an unsupported process state.")

    def _queue(self, action: str, service: str) -> None:
        self._validate_unit(service)
        self.status(service)
        result = self._run(
            [
                *self._action_command(),
                "--no-ask-password",
                "--no-block",
                "--job-mode=fail",
                action,
                service,
            ],
            timeout=self._action_timeout,
        )
        if result.returncode == 0:
            return
        stderr = (result.stderr or "").lower()
        if "conflict" in stderr or "transaction" in stderr or "job mode" in stderr:
            raise ServiceConflict("A conflicting systemd job is already queued.")
        raise ServiceCommandRejected("systemd rejected the requested operation.")

    def start(self, service: str) -> None:
        self._queue("start", service)

    def stop(self, service: str) -> None:
        self._queue("stop", service)

    def restart(self, service: str) -> None:
        self._queue("restart", service)
