from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from games.config import GameConfigError, GameConfigRepository


VALID_YAML = """
games:
  minecraft:
    name: Minecraft
    service: game-minecraft.service
    icon: minecraft.png
    status:
      type: minecraft
      host: 127.0.0.1
      port: 25565
  vintage-story:
    name: Vintage Story
    service: game-vintagestory.service
"""


class GameConfigTests(TestCase):
    def load_yaml(self, source):
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        path = Path(temp_dir.name) / "games.yaml"
        path.write_text(source, encoding="utf-8")
        return GameConfigRepository.from_path(path)

    def test_loads_servers_in_yaml_order_with_optional_status(self):
        repository = self.load_yaml(VALID_YAML)

        servers = repository.get_servers()
        self.assertEqual([server.slug for server in servers], ["minecraft", "vintage-story"])
        self.assertEqual(repository.get_server("minecraft").status.port, 25565)
        self.assertIsNone(repository.get_server("vintage-story").status)

    def test_rejects_duplicate_yaml_keys(self):
        source = VALID_YAML + "\n  minecraft:\n    name: Duplicate\n"
        with self.assertRaises(GameConfigError):
            self.load_yaml(source)

    def test_rejects_bad_slug_and_service_command_text(self):
        for source in (
            VALID_YAML.replace("vintage-story:", "vintage_story:"),
            VALID_YAML.replace("game-vintagestory.service", "game-vintagestory.service; whoami"),
            VALID_YAML.replace("game-vintagestory.service", "--help.service"),
        ):
            with self.subTest(source=source):
                with self.assertRaises(GameConfigError):
                    self.load_yaml(source)

    def test_rejects_invalid_status_type_host_and_port(self):
        invalid_values = (
            ("type: minecraft", "type: arbitrary"),
            ("host: 127.0.0.1", "host: http://127.0.0.1/path"),
            ("port: 25565", "port: 70000"),
        )
        for original, replacement in invalid_values:
            with self.subTest(replacement=replacement):
                with self.assertRaises(GameConfigError):
                    self.load_yaml(VALID_YAML.replace(original, replacement))

    def test_rejects_unknown_fields_and_empty_document(self):
        with self.assertRaises(GameConfigError):
            self.load_yaml(VALID_YAML.replace("name: Vintage Story", "name: Vintage Story\n    command: echo pwned"))
        with self.assertRaises(GameConfigError):
            self.load_yaml("")

    def test_missing_config_file_has_domain_error(self):
        with TemporaryDirectory() as temp_dir:
            with self.assertRaises(GameConfigError):
                GameConfigRepository.from_path(Path(temp_dir) / "missing.yaml")
