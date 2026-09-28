import os
import re
from collections.abc import Mapping, MutableMapping
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

ENV_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def load_local_env(
    path: Path,
    environ: MutableMapping[str, str] | None = None,
) -> None:
    """Load simple KEY=value entries; process environment always wins."""
    source = os.environ if environ is None else environ
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except FileNotFoundError:
        return
    except OSError as exc:
        raise ImproperlyConfigured("The local .env file cannot be read.") from exc

    for number, line in enumerate(lines, start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        name, separator, value = line.partition("=")
        name = name.strip()
        if not separator or not ENV_NAME_PATTERN.fullmatch(name):
            raise ImproperlyConfigured(f"Invalid .env entry on line {number}.")
        value = value.strip()
        if value.startswith(("'", '"')):
            if len(value) < 2 or value[-1] != value[0]:
                raise ImproperlyConfigured(f"Invalid .env entry on line {number}.")
            value = value[1:-1]
        source.setdefault(name, value)


def require_secret_key(environ: Mapping[str, str] | None = None) -> str:
    """Return the configured Django signing key or fail closed."""
    source = os.environ if environ is None else environ
    secret_key = source.get("SECRET_KEY", "").strip()
    if not secret_key:
        raise ImproperlyConfigured("SECRET_KEY must be set in the environment or .env.")
    return secret_key


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off", ""}:
        return False
    raise ImproperlyConfigured(f"{name} must be a boolean value.")
