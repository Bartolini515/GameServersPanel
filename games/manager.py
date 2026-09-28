import logging

from games.status.registry import STATUS_ADAPTERS
from games.types import GameStatus, GameStatusState, ProcessStatus

logger = logging.getLogger(__name__)


class UnknownServer(LookupError):
    pass


class GameManager:
    def __init__(self, repository, service_backend, status_adapters=None):
        self.repository = repository
        self.service_backend = service_backend
        self.status_adapters = (
            STATUS_ADAPTERS if status_adapters is None else status_adapters
        )

    def get_servers(self):
        return self.repository.get_servers()

    def get_server(self, slug):
        try:
            server = self.repository.get_server(slug)
        except KeyError as exc:
            raise UnknownServer(slug) from exc
        if server is None:
            raise UnknownServer(slug)
        return server

    def start(self, slug):
        self.service_backend.start(self.get_server(slug).service)

    def stop(self, slug):
        self.service_backend.stop(self.get_server(slug).service)

    def restart(self, slug):
        self.service_backend.restart(self.get_server(slug).service)

    def process_status(self, slug) -> ProcessStatus:
        return self.service_backend.status(self.get_server(slug).service)

    def game_status(self, slug) -> GameStatus:
        server = self.get_server(slug)
        if server.status is None:
            adapter = self.status_adapters.get("generic")
            if adapter is None:
                return GameStatus(state=GameStatusState.UNAVAILABLE)
        else:
            adapter = self.status_adapters.get(server.status.type)
        if adapter is None:
            logger.warning("No status adapter is registered for server slug %s", slug)
            return GameStatus(state=GameStatusState.UNKNOWN)
        try:
            return adapter.check(server)
        except Exception:
            logger.exception("Game status adapter failed for server slug %s", slug)
            return GameStatus(state=GameStatusState.UNKNOWN)
