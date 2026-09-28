import a2s

from games.types import GameStatus, GameStatusState, ServerConfig


class A2SStatusAdapter:
    """Query servers that expose the Source A2S info protocol."""

    def check(self, server: ServerConfig) -> GameStatus:
        if server.status is None:
            return GameStatus(state=GameStatusState.UNAVAILABLE)

        response = a2s.info(
            (server.status.host, server.status.port),
            timeout=server.status.timeout_s,
        )
        return GameStatus(
            state=GameStatusState.ONLINE,
            players=int(response.player_count),
            max_players=int(response.max_players),
            ping_ms=float(response.ping) * 1000,
            map_name=response.map_name or None,
            server_name=response.server_name or None,
        )
