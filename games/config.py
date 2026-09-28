import ipaddress
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml
from yaml.constructor import ConstructorError

from games.status.registry import SUPPORTED_STATUS_TYPES
from games.types import ServerConfig, StatusConfig

SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
SERVICE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.@-]{0,243}\.service$")
ICON_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}\.(?:png|webp)$")
HOST_LABEL_PATTERN = re.compile(
    r"^(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)(?:\.(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?))*\.?$"
)
SERVER_KEYS = {"name", "service", "icon", "status"}
STATUS_KEYS = {"type", "host", "port", "timeout_s"}


class GameConfigError(ValueError):
    pass


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(loader, node, deep=False):
    loader.flatten_mapping(node)
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in result
        except TypeError as exc:
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "found an unhashable key",
                key_node.start_mark,
            ) from exc
        if duplicate:
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def _require_mapping(value: Any, label: str) -> Mapping:
    if not isinstance(value, Mapping):
        raise GameConfigError(f"{label} must be a mapping.")
    return value


def _check_keys(value: Mapping, required: set[str], allowed: set[str], label: str):
    missing = required - value.keys()
    extra = value.keys() - allowed
    if missing:
        raise GameConfigError(f"{label} is missing required field(s): {', '.join(sorted(missing))}.")
    if extra:
        raise GameConfigError(f"{label} contains unsupported field(s): {', '.join(sorted(extra))}.")


def _valid_host(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return bool(HOST_LABEL_PATTERN.fullmatch(host))


def load_game_config(path: Path | str) -> tuple[ServerConfig, ...]:
    config_path = Path(path)
    try:
        source = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise GameConfigError("The game configuration file cannot be read.") from exc

    try:
        document = yaml.load(source, Loader=_UniqueKeyLoader)
    except yaml.YAMLError as exc:
        raise GameConfigError("The game configuration contains invalid YAML.") from exc

    root = _require_mapping(document, "Root configuration")
    _check_keys(root, {"games"}, {"games"}, "Root configuration")
    games = _require_mapping(root["games"], "games")
    if not games:
        raise GameConfigError("At least one game must be configured.")

    servers = []
    service_names = set()
    for slug, raw_server in games.items():
        if not isinstance(slug, str) or not SLUG_PATTERN.fullmatch(slug):
            raise GameConfigError(f"Invalid server slug: {slug!r}.")

        server = _require_mapping(raw_server, f"games.{slug}")
        _check_keys(server, {"name", "service"}, SERVER_KEYS, f"games.{slug}")

        name = server["name"]
        service = server["service"]
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 100:
            raise GameConfigError(f"games.{slug}.name must be non-empty and at most 100 characters.")
        if not isinstance(service, str) or not SERVICE_PATTERN.fullmatch(service):
            raise GameConfigError(f"games.{slug}.service must be a simple .service unit name.")
        if service in service_names:
            raise GameConfigError(f"Service {service!r} cannot be assigned to more than one game.")
        service_names.add(service)

        icon = server.get("icon")
        if icon is not None and (not isinstance(icon, str) or not ICON_PATTERN.fullmatch(icon)):
            raise GameConfigError(f"games.{slug}.icon must be a local PNG or WebP filename.")

        status = _parse_status(server.get("status"), slug)
        servers.append(
            ServerConfig(
                slug=slug,
                name=name.strip(),
                service=service,
                icon=icon,
                status=status,
            )
        )

    return tuple(servers)


def _parse_status(raw_status: Any, slug: str) -> StatusConfig | None:
    if raw_status is None:
        return None
    status = _require_mapping(raw_status, f"games.{slug}.status")
    _check_keys(
        status,
        {"type", "host", "port"},
        STATUS_KEYS,
        f"games.{slug}.status",
    )

    adapter_type = status["type"]
    host = status["host"]
    port = status["port"]
    timeout = status.get("timeout_s", 1.5)
    if not isinstance(adapter_type, str) or adapter_type not in SUPPORTED_STATUS_TYPES:
        raise GameConfigError(f"games.{slug}.status.type is not a registered adapter type.")
    if not isinstance(host, str) or not _valid_host(host):
        raise GameConfigError(f"games.{slug}.status.host must be an IP address or hostname, not a URL.")
    if type(port) is not int or not 1 <= port <= 65535:
        raise GameConfigError(f"games.{slug}.status.port must be an integer from 1 to 65535.")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0.1 <= timeout <= 2.0:
        raise GameConfigError(f"games.{slug}.status.timeout_s must be between 0.1 and 2.0 seconds.")

    return StatusConfig(
        type=adapter_type,
        host=host,
        port=port,
        timeout_s=float(timeout),
    )


class GameConfigRepository:
    def __init__(self, servers: tuple[ServerConfig, ...]):
        self._servers = servers
        self._by_slug = {server.slug: server for server in servers}

    @classmethod
    def from_path(cls, path: Path | str) -> "GameConfigRepository":
        return cls(load_game_config(path))

    def get_servers(self) -> tuple[ServerConfig, ...]:
        return self._servers

    def get_server(self, slug: str) -> ServerConfig:
        return self._by_slug[slug]
