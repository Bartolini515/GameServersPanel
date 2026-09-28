from functools import lru_cache

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from games.config import GameConfigRepository
from games.manager import GameManager
from games.services.fake import FakeSystemdService
from games.services.systemd import SystemdService
from games.status.registry import STATUS_ADAPTERS


def build_game_manager() -> GameManager:
    repository = GameConfigRepository.from_path(settings.GAME_CONFIG_PATH)
    backend_name = settings.GAME_SERVICE_BACKEND

    if backend_name == "systemd":
        service_backend = SystemdService()
    elif backend_name == "systemd_system":
        service_backend = SystemdService(scope="system")
    elif backend_name == "fake":
        if not settings.DEBUG:
            raise ImproperlyConfigured(
                "The fake game service backend is only available when DEBUG=True."
            )
        service_backend = FakeSystemdService(
            server.service for server in repository.get_servers()
        )
    else:
        raise ImproperlyConfigured(
            "GAME_SERVICE_BACKEND must be 'systemd', 'systemd_system' or 'fake'."
        )

    return GameManager(repository, service_backend, STATUS_ADAPTERS)


@lru_cache(maxsize=1)
def get_game_manager() -> GameManager:
    """Share the manager per process so the debug fake keeps its state."""
    return build_game_manager()
