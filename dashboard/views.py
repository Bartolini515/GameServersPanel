import logging

from django.conf import settings
from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from accounts.access import panel_login_required
from games.factory import get_game_manager
from games.manager import UnknownServer
from games.services.base import ServiceError
from games.types import GameStatusState, ProcessStatus
from monitoring.system import read_system_stats

logger = logging.getLogger("games.actions")

PROCESS_PRESENTATION = {
    ProcessStatus.STOPPED: ("STOPPED", "secondary"),
    ProcessStatus.STARTING: ("STARTING", "info"),
    ProcessStatus.RUNNING: ("RUNNING", "success"),
    ProcessStatus.STOPPING: ("STOPPING", "warning"),
    ProcessStatus.FAILED: ("FAILED", "danger"),
}

GAME_PRESENTATION = {
    GameStatusState.ONLINE: ("ONLINE", "success"),
    GameStatusState.OFFLINE: ("OFFLINE", "secondary"),
    GameStatusState.UNKNOWN: ("Nieznany", "warning"),
    GameStatusState.UNAVAILABLE: ("Niedostępny", "secondary"),
}


def server_card_context(manager, server):
    process_status = None
    process_label = "Nieznany"
    process_badge = "warning"
    process_error = None
    try:
        process_status = manager.process_status(server.slug)
        process_label, process_badge = PROCESS_PRESENTATION[process_status]
    except ServiceError:
        process_error = "Nie można odczytać stanu procesu."

    game_status = None
    if process_status in {ProcessStatus.STOPPED, ProcessStatus.FAILED}:
        game_label, game_badge = "Nie sprawdzano", "secondary"
    else:
        status = manager.game_status(server.slug)
        game_label, game_badge = GAME_PRESENTATION[status.state]
        game_status = status

    icon_path = settings.BASE_DIR / "static" / "games" / "icons" / (server.icon or "")
    icon_available = bool(server.icon and icon_path.is_file())

    return {
        "server": server,
        "process_status": process_status,
        "process_label": process_label,
        "process_badge": process_badge,
        "process_error": process_error,
        "game_status": game_status,
        "game_label": game_label,
        "game_badge": game_badge,
        "icon_available": icon_available,
        "icon_initial": server.name[:1].upper(),
        "action_message": None,
        "action_error": False,
    }


@panel_login_required
@require_GET
def index(request):
    manager = get_game_manager()
    cards = [
        server_card_context(manager, server)
        for server in manager.get_servers()
    ]
    return render(
        request,
        "dashboard/index.html",
        {
            "server_cards": cards,
            "stats": read_system_stats(settings.MONITOR_DISK_PATH),
        },
    )


@panel_login_required
@require_GET
def server_list(request):
    return redirect("dashboard:index")


@panel_login_required
@require_GET
def server_status(request, slug):
    manager = get_game_manager()
    try:
        server = manager.get_server(slug)
    except UnknownServer as exc:
        raise Http404 from exc
    card = server_card_context(manager, server)
    return render(request, "dashboard/_server_card.html", {"card": card})


def _server_action(request, slug, action):
    manager = get_game_manager()
    try:
        server = manager.get_server(slug)
    except UnknownServer as exc:
        raise Http404 from exc

    action_messages = {
        "start": "Zlecono uruchomienie serwera.",
        "stop": "Zlecono zatrzymanie serwera.",
        "restart": "Zlecono restart serwera.",
    }
    error = False
    try:
        getattr(manager, action)(slug)
        action_message = action_messages[action]
        logger.info(
            "User %s requested %s for game server %s (%s)",
            request.user.get_username(), action, slug, server.service,
        )
    except ServiceError:
        error = True
        action_message = "Nie udało się wykonać operacji. Sprawdź stan serwera i spróbuj ponownie."
        logger.exception(
            "User %s could not %s game server %s (%s)",
            request.user.get_username(), action, slug, server.service,
        )

    card = server_card_context(manager, server)
    card["action_message"] = action_message
    card["action_error"] = error
    if request.headers.get("HX-Request") == "true":
        return render(request, "dashboard/_server_card.html", {"card": card})
    if error:
        messages.error(request, action_message)
    else:
        messages.success(request, action_message)
    return redirect("dashboard:index")


@panel_login_required
@require_POST
def start_server(request, slug):
    return _server_action(request, slug, "start")


@panel_login_required
@require_POST
def stop_server(request, slug):
    return _server_action(request, slug, "stop")


@panel_login_required
@require_POST
def restart_server(request, slug):
    return _server_action(request, slug, "restart")
