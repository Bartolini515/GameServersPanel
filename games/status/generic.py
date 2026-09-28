import socket
import time

from games.status.base import StatusAdapter
from games.types import GameStatus, GameStatusState, ServerConfig


class GenericStatusAdapter:
    def check(self, server: ServerConfig) -> GameStatus:
        if server.status is None:
            return GameStatus(state=GameStatusState.UNAVAILABLE)

        started = time.monotonic()
        with socket.create_connection(
            (server.status.host, server.status.port),
            timeout=server.status.timeout_s,
        ):
            elapsed_ms = (time.monotonic() - started) * 1000
        return GameStatus(
            state=GameStatusState.ONLINE,
            ping_ms=elapsed_ms,
        )
