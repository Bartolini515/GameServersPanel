from unittest import TestCase
from pathlib import Path
from tempfile import TemporaryDirectory

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
