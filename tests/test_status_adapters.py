from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from games.status.a2s import A2SStatusAdapter
from games.status.generic import GenericStatusAdapter
from games.status.minecraft import MinecraftStatusAdapter
from games.types import GameStatusState, ServerConfig, StatusConfig


class StatusAdapterTests(TestCase):
    def server(self, adapter_type, host, port, timeout=0.7):
        return ServerConfig(
            slug="test-server",
            name="Test Server",
            service="game-test.service",
            icon=None,
            status=StatusConfig(adapter_type, host, port, timeout),
        )

    @patch("games.status.generic.time.monotonic", side_effect=(1.0, 1.025))
    @patch("games.status.generic.socket.create_connection")
    def test_generic_adapter_checks_tcp_with_configured_timeout(self, create_connection, _clock):
        result = GenericStatusAdapter().check(
            self.server("generic", "localhost", 27015)
        )

        create_connection.assert_called_once_with(
            ("localhost", 27015), timeout=0.7
        )
        self.assertEqual(result.state, GameStatusState.ONLINE)
        self.assertAlmostEqual(result.ping_ms, 25.0)

    def test_generic_adapter_without_status_config_is_unavailable(self):
        server = ServerConfig(
            slug="test-server",
            name="Test Server",
            service="game-test.service",
            icon=None,
            status=None,
        )

        result = GenericStatusAdapter().check(server)

        self.assertEqual(result.state, GameStatusState.UNAVAILABLE)

    @patch("games.status.minecraft.JavaServer")
    def test_minecraft_adapter_queries_once_and_normalizes_players_and_ping(self, java_server):
        java_server.return_value.status.return_value = SimpleNamespace(
            players=SimpleNamespace(online=3, max=20),
            latency=42.6,
        )

        result = MinecraftStatusAdapter().check(
            self.server("minecraft", "127.0.0.1", 25565)
        )

        java_server.assert_called_once_with("127.0.0.1", 25565, timeout=0.7)
        java_server.return_value.status.assert_called_once_with(tries=1)
        self.assertEqual(result.state, GameStatusState.ONLINE)
        self.assertEqual((result.players, result.max_players), (3, 20))
        self.assertEqual(result.ping_ms, 42.6)

    @patch("games.status.a2s.a2s.info")
    def test_a2s_adapter_normalizes_player_map_name_and_ping(self, info):
        info.return_value = SimpleNamespace(
            player_count=5,
            max_players=32,
            ping=0.025,
            map_name="Altis",
            server_name="Coop server",
        )

        result = A2SStatusAdapter().check(self.server("a2s", "127.0.0.1", 2303))

        info.assert_called_once_with(("127.0.0.1", 2303), timeout=0.7)
        self.assertEqual(result.state, GameStatusState.ONLINE)
        self.assertEqual((result.players, result.max_players), (5, 32))
        self.assertEqual(result.ping_ms, 25.0)
        self.assertEqual(result.map_name, "Altis")
        self.assertEqual(result.server_name, "Coop server")

    @patch("games.status.minecraft.JavaServer")
    def test_minecraft_protocol_failure_is_normalized_by_game_manager(self, java_server):
        from games.manager import GameManager

        server = self.server("minecraft", "127.0.0.1", 25565)
        java_server.return_value.status.side_effect = TimeoutError
        repository = Mock()
        repository.get_server.return_value = server
        manager = GameManager(
            repository,
            Mock(),
            {"minecraft": MinecraftStatusAdapter()},
        )

        result = manager.game_status(server.slug)

        self.assertEqual(result.state, GameStatusState.UNKNOWN)
