from typing import Protocol

from games.types import ProcessStatus


class ServiceError(RuntimeError):
    """Base class for expected service manager errors."""


class ServiceNotFound(ServiceError):
    pass


class ServiceTimeout(ServiceError):
    pass


class ServiceUnavailable(ServiceError):
    pass


class ServiceCommandRejected(ServiceError):
    pass


class ServiceProtocolError(ServiceError):
    pass


class ServiceConflict(ServiceCommandRejected):
    pass


class ServiceBackend(Protocol):
    def start(self, service: str) -> None: ...

    def stop(self, service: str) -> None: ...

    def restart(self, service: str) -> None: ...

    def status(self, service: str) -> ProcessStatus: ...
