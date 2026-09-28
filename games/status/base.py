from typing import Protocol

from games.types import GameStatus, ServerConfig


class StatusAdapter(Protocol):
    def check(self, server: ServerConfig) -> GameStatus: ...
