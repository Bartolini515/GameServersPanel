import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from django.core.exceptions import ImproperlyConfigured

from config.environment import load_local_env, require_secret_key


class SecretKeySettingsTests(TestCase):
    def test_missing_secret_key_fails_closed(self):
        with self.assertRaises(ImproperlyConfigured):
            require_secret_key({})

    def test_blank_secret_key_fails_closed(self):
        with self.assertRaises(ImproperlyConfigured):
            require_secret_key({"SECRET_KEY": "  "})

    def test_secret_key_is_read_from_environment_mapping(self):
        self.assertEqual(
            require_secret_key({"SECRET_KEY": "test-secret"}),
            "test-secret",
        )


class LocalEnvTests(TestCase):
    def test_reads_values_and_preserves_existing_environment(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text(
                "# lokalny plik\nSECRET_KEY='file-secret'\nDEBUG=true\n",
                encoding="utf-8",
            )
            environ = {"DEBUG": "false"}

            load_local_env(path, environ)

        self.assertEqual(environ["SECRET_KEY"], "file-secret")
        self.assertEqual(environ["DEBUG"], "false")

    def test_missing_file_is_optional(self):
        with TemporaryDirectory() as directory:
            environ = {}
            load_local_env(Path(directory) / ".env", environ)
        self.assertEqual(environ, {})

    def test_malformed_line_fails_without_exposing_value(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("broken-secret-value\n", encoding="utf-8")
            with self.assertRaises(ImproperlyConfigured) as error:
                load_local_env(path, {})
        self.assertNotIn("broken-secret-value", str(error.exception))


class EnvironmentBackedSettingsTests(TestCase):
    def test_production_settings_support_https_proxy_and_system_backend(self):
        repository_root = Path(__file__).resolve().parents[1]
        environment = os.environ.copy()
        environment.update(
            {
                "SECRET_KEY": "settings-test-secret",
                "DEBUG": "false",
                "GAME_SERVICE_BACKEND": "systemd_system",
                "ALLOWED_HOSTS": "games.nogonoma.net",
                "GAME_CONFIG_PATH": str(repository_root / "games.example.yaml"),
            }
        )

        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import json; from config import settings; print(json.dumps({"
                "'DEBUG': settings.DEBUG, "
                "'GAME_SERVICE_BACKEND': settings.GAME_SERVICE_BACKEND, "
                "'ALLOWED_HOSTS': settings.ALLOWED_HOSTS, "
                "'SESSION_COOKIE_SECURE': settings.SESSION_COOKIE_SECURE, "
                "'CSRF_COOKIE_SECURE': settings.CSRF_COOKIE_SECURE, "
                "'SECURE_PROXY_SSL_HEADER': getattr(settings, 'SECURE_PROXY_SSL_HEADER', None), "
                "'SECURE_SSL_REDIRECT': getattr(settings, 'SECURE_SSL_REDIRECT', False), "
                "'SECURE_HSTS_SECONDS': getattr(settings, 'SECURE_HSTS_SECONDS', 0)"
                "}))",
            ],
            cwd=repository_root,
            env=environment,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        values = json.loads(result.stdout.strip().splitlines()[-1])
        self.assertEqual(
            values,
            {
                "DEBUG": False,
                "GAME_SERVICE_BACKEND": "systemd_system",
                "ALLOWED_HOSTS": ["games.nogonoma.net"],
                "SESSION_COOKIE_SECURE": True,
                "CSRF_COOKIE_SECURE": True,
                "SECURE_PROXY_SSL_HEADER": ["HTTP_X_FORWARDED_PROTO", "https"],
                "SECURE_SSL_REDIRECT": True,
                "SECURE_HSTS_SECONDS": 0,
            },
        )
