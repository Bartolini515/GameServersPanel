from mcstatus import JavaServer

from games.types import GameStatus, GameStatusState, ServerConfig


class MinecraftStatusAdapter:
    """Query a Minecraft Java server's status protocol."""

    def check(self, server: ServerConfig) -> GameStatus:
        if server.status is None:
            return GameStatus(state=GameStatusState.UNAVAILABLE)

        response = JavaServer(
            server.status.host,
            server.status.port,
            timeout=server.status.timeout_s,
        ).status(tries=1)
        return GameStatus(
            state=GameStatusState.ONLINE,
            players=int(response.players.online),
            max_players=int(response.players.max),
            ping_ms=float(response.latency),
        )
