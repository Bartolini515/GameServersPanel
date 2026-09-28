from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured

from games.factory import build_game_manager
from games.services.fake import FakeSystemdService
from games.services.systemd import SystemdService
from games.types import ProcessStatus


SAMPLE_YAML = """
games:
  minecraft:
    name: Minecraft
    service: game-minecraft.service
"""


class GameManagerFactoryTests(TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.config_path = Path(self.temp_dir.name) / "games.yaml"
        self.config_path.write_text(SAMPLE_YAML, encoding="utf-8")

    def build(self, *, debug, backend):
        with patch("games.factory.settings.DEBUG", debug), patch(
            "games.factory.settings.GAME_SERVICE_BACKEND", backend
        ), patch("games.factory.settings.GAME_CONFIG_PATH", self.config_path):
            return build_game_manager()

    def test_fake_backend_is_stateful_for_manual_debug_preview(self):
        manager = self.build(debug=True, backend="fake")

        self.assertIsInstance(manager.service_backend, FakeSystemdService)
        self.assertEqual(manager.process_status("minecraft"), ProcessStatus.STOPPED)
        manager.start("minecraft")
        self.assertEqual(manager.process_status("minecraft"), ProcessStatus.RUNNING)
        manager.stop("minecraft")
        self.assertEqual(manager.process_status("minecraft"), ProcessStatus.STOPPED)

    def test_fake_backend_is_rejected_outside_debug(self):
        with self.assertRaises(ImproperlyConfigured):
            self.build(debug=False, backend="fake")

    def test_production_backend_is_systemd(self):
        manager = self.build(debug=False, backend="systemd")
        self.assertIsInstance(manager.service_backend, SystemdService)
        self.assertEqual(manager.service_backend._scope, "user")

    def test_system_service_backend_selects_system_scope(self):
        manager = self.build(debug=False, backend="systemd_system")

        self.assertIsInstance(manager.service_backend, SystemdService)
        self.assertEqual(manager.service_backend._scope, "system")

    def test_unknown_backend_is_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            self.build(debug=True, backend="shell")
