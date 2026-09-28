from dataclasses import dataclass
from enum import Enum


class ProcessStatus(str, Enum):
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    FAILED = "FAILED"


class GameStatusState(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    UNKNOWN = "UNKNOWN"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class StatusConfig:
    type: str
    host: str
    port: int
    timeout_s: float = 1.5


@dataclass(frozen=True, slots=True)
class ServerConfig:
    slug: str
    name: str
    service: str
    icon: str | None
    status: StatusConfig | None


@dataclass(frozen=True, slots=True)
class GameStatus:
    state: GameStatusState
    players: int | None = None
    max_players: int | None = None
    ping_ms: float | None = None
    map_name: str | None = None
    mission: str | None = None
    server_name: str | None = None
