from collections.abc import Iterable

from games.services.base import ServiceNotFound
from games.types import ProcessStatus


class FakeSystemdService:
    """Small in-memory service backend for a local DEBUG-only UI preview."""

    def __init__(self, services: Iterable[str]):
        self._states = {service: ProcessStatus.STOPPED for service in services}

    def _require_service(self, service: str) -> None:
        if service not in self._states:
            raise ServiceNotFound("Configured service does not exist in the fake backend.")

    def start(self, service: str) -> None:
        self._require_service(service)
        self._states[service] = ProcessStatus.RUNNING

    def stop(self, service: str) -> None:
        self._require_service(service)
        self._states[service] = ProcessStatus.STOPPED

    def restart(self, service: str) -> None:
        self._require_service(service)
        self._states[service] = ProcessStatus.RUNNING

    def status(self, service: str) -> ProcessStatus:
        self._require_service(service)
        return self._states[service]
