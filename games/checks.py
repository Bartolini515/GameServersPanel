from django.conf import settings
from django.core.checks import Error, register

from games.config import GameConfigError, GameConfigRepository


@register
def check_game_configuration(app_configs, **kwargs):
    try:
        GameConfigRepository.from_path(settings.GAME_CONFIG_PATH)
    except GameConfigError as exc:
        return [
            Error(
                str(exc),
                hint="Create a valid local games.yaml using games.example.yaml as a template.",
                id="games.E001",
            )
        ]
    return []
