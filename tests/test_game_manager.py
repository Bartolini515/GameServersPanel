from unittest import TestCase
from unittest.mock import Mock

from games.manager import GameManager, UnknownServer
from games.types import GameStatus, GameStatusState, ProcessStatus, ServerConfig


class GameManagerTests(TestCase):
    def setUp(self):
        self.minecraft = ServerConfig(
            slug="minecraft",
            name="Minecraft",
            service="game-minecraft.service",
            icon=None,
            status=None,
        )
        self.repository = Mock()
        self.repository.get_servers.return_value = (self.minecraft,)
        self.repository.get_server.side_effect = (
            lambda slug: self.minecraft if slug == self.minecraft.slug else None
        )
        self.service = Mock()
        self.service.status.return_value = ProcessStatus.RUNNING
        self.manager = GameManager(self.repository, self.service, {})

    def test_get_servers_and_get_server_delegate_to_config_repository(self):
        self.assertEqual(self.manager.get_servers(), (self.minecraft,))
        self.assertEqual(self.manager.get_server("minecraft"), self.minecraft)

    def test_all_actions_resolve_configured_service_name(self):
        self.manager.start("minecraft")
        self.manager.stop("minecraft")
        self.manager.restart("minecraft")

        self.service.start.assert_called_once_with("game-minecraft.service")
        self.service.stop.assert_called_once_with("game-minecraft.service")
        self.service.restart.assert_called_once_with("game-minecraft.service")

    def test_status_methods_return_domain_types(self):
        self.assertEqual(self.manager.process_status("minecraft"), ProcessStatus.RUNNING)
        self.assertEqual(
            self.manager.game_status("minecraft"),
            GameStatus(state=GameStatusState.UNAVAILABLE),
        )

    def test_unknown_slug_never_reaches_service_backend(self):
        with self.assertRaises(UnknownServer):
            self.manager.start("not-configured")
        self.service.start.assert_not_called()

    def test_unknown_adapter_does_not_disable_process_management(self):
        configured = ServerConfig(
            slug="minecraft",
            name="Minecraft",
            service="game-minecraft.service",
            icon=None,
            status=None,
        )
        self.repository.get_server.return_value = configured

        self.manager.start("minecraft")

        self.service.start.assert_called_once_with("game-minecraft.service")
