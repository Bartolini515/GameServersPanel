"""Run the repository's safe, repeatable checks from a Pipenv environment."""

import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    if sys.version_info[:2] != (3, 12):
        print("Wymagany Python 3.12.", file=sys.stderr)
        return 2

    pipenv = shutil.which("pipenv")
    if pipenv is None:
        print("Nie znaleziono Pipenv w PATH.", file=sys.stderr)
        return 2

    env = os.environ.copy()
    env["SECRET_KEY"] = "check-only-django-secret-key-never-use-in-running-panel"
    env["DEBUG"] = "true"
    env["GAME_SERVICE_BACKEND"] = "fake"
    env["GAME_CONFIG_PATH"] = str(ROOT / "games.example.yaml")

    checks = (
        [pipenv, "verify"],
        [sys.executable, "manage.py", "check"],
        [sys.executable, "manage.py", "test"],
    )
    for command in checks:
        print(f"\n> {' '.join(command)}", flush=True)
        result = subprocess.run(command, cwd=ROOT, env=env, check=False)
        if result.returncode:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
