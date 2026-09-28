import subprocess
from unittest import TestCase
from unittest.mock import Mock

from games.services.base import (
    ServiceCommandRejected,
    ServiceConflict,
    ServiceNotFound,
    ServiceProtocolError,
    ServiceTimeout,
    ServiceUnavailable,
)
from games.services.systemd import SystemdService
from games.types import ProcessStatus


def completed(stdout="", returncode=0, stderr=""):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


def properties(active, sub, main_pid="0", load="loaded"):
    return completed(
        f"LoadState={load}\nActiveState={active}\nSubState={sub}\nMainPID={main_pid}\n"
    )


class SystemdServiceTests(TestCase):
    def setUp(self):
        self.runner = Mock()
        self.systemd = SystemdService(runner=self.runner)

    def test_maps_all_supported_systemd_states(self):
        cases = (
            (properties("inactive", "dead"), ProcessStatus.STOPPED),
            (properties("activating", "start"), ProcessStatus.STARTING),
            (properties("active", "running", "1234"), ProcessStatus.RUNNING),
            (properties("deactivating", "stop"), ProcessStatus.STOPPING),
            (properties("failed", "failed"), ProcessStatus.FAILED),
        )
        for result, expected in cases:
            with self.subTest(expected=expected):
                self.runner.reset_mock()
                self.runner.return_value = result
                self.assertEqual(self.systemd.status("game-minecraft.service"), expected)

    def test_status_uses_machine_readable_unit_properties(self):
        self.runner.return_value = properties("inactive", "dead")

        self.systemd.status("game-minecraft.service")

        args, kwargs = self.runner.call_args
        self.assertEqual(
            args[0],
            [
                "systemctl", "--user", "--no-pager", "show",
                "--property=LoadState", "--property=ActiveState",
                "--property=SubState", "--property=MainPID",
                "game-minecraft.service",
            ],
        )
        self.assertEqual(kwargs["timeout"], 2)
        self.assertIs(kwargs["shell"], False)
        self.assertIs(kwargs["capture_output"], True)
        self.assertIs(kwargs["text"], True)

    def test_missing_masked_and_malformed_units_raise_typed_errors(self):
        self.runner.return_value = properties("inactive", "dead", load="not-found")
        with self.assertRaises(ServiceNotFound):
            self.systemd.status("game-minecraft.service")

        self.runner.return_value = properties("inactive", "dead", load="masked")
        with self.assertRaises(ServiceCommandRejected):
            self.systemd.status("game-minecraft.service")

        self.runner.return_value = completed("LoadState=loaded\nActiveState=active\nSubState=exited\nMainPID=0\n")
        with self.assertRaises(ServiceProtocolError):
            self.systemd.status("game-minecraft.service")

    def test_status_timeout_and_missing_systemctl_are_reported(self):
        self.runner.side_effect = subprocess.TimeoutExpired("systemctl", 2)
        with self.assertRaises(ServiceTimeout):
            self.systemd.status("game-minecraft.service")

        self.runner.side_effect = FileNotFoundError("systemctl")
        with self.assertRaises(ServiceUnavailable):
            self.systemd.status("game-minecraft.service")

    def test_actions_preflight_unit_then_queue_nonblocking_job(self):
        for action in ("start", "stop", "restart"):
            with self.subTest(action=action):
                self.runner.reset_mock()
                self.runner.side_effect = [
                    properties("inactive", "dead"),
                    completed(),
                ]
                getattr(self.systemd, action)("game-minecraft.service")
                self.assertEqual(self.runner.call_count, 2)
                action_args = self.runner.call_args_list[1].args[0]
                self.assertEqual(
                    action_args,
                    [
                        "systemctl", "--user", "--no-ask-password",
                        "--no-block", "--job-mode=fail", action,
                        "game-minecraft.service",
                    ],
                )
                self.assertEqual(self.runner.call_args_list[1].kwargs["timeout"], 3)

    def test_failed_operation_does_not_expose_systemd_stderr(self):
        self.runner.side_effect = [
            properties("inactive", "dead"),
            completed(returncode=1, stderr="sensitive host details"),
        ]
        with self.assertRaises(ServiceCommandRejected) as raised:
            self.systemd.start("game-minecraft.service")
        self.assertNotIn("sensitive host details", str(raised.exception))

    def test_conflicting_job_is_typed_and_unsafe_unit_is_rejected(self):
        self.runner.side_effect = [
            properties("inactive", "dead"),
            completed(returncode=1, stderr="Transaction conflicts with existing job"),
        ]
        with self.assertRaises(ServiceConflict):
            self.systemd.start("game-minecraft.service")

        self.runner.reset_mock()
        with self.assertRaises(ServiceCommandRejected):
            self.systemd.start("game-minecraft.service; whoami")
        self.runner.assert_not_called()
