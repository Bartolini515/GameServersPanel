from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from games.factory import get_game_manager
from games.services.base import ServiceCommandRejected
from games.types import GameStatus, GameStatusState


@override_settings(DEBUG=True, GAME_SERVICE_BACKEND="fake")
class DashboardPageTests(TestCase):
    def setUp(self):
        get_game_manager.cache_clear()
        self.addCleanup(get_game_manager.cache_clear)
        self.user = get_user_model().objects.create_user(
            username="panel", password="a-long-test-password"
        )

    def test_dashboard_lists_yaml_games_with_process_and_game_status(self):
        self.client.force_login(self.user)

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Minecraft")
        self.assertContains(response, "Arma 3")
        self.assertContains(response, "Vintage Story")
        self.assertContains(response, "Proces:")
        self.assertContains(response, "STOPPED")
        self.assertContains(response, "Status gry:")
        self.assertContains(response, "Nie sprawdzano")
        self.assertContains(response, "START")
        self.assertContains(response, "STOP")
        self.assertContains(response, "RESTART")

    def test_dashboard_uses_bootstrap_and_local_htmx_assets(self):
        self.client.force_login(self.user)

        response = self.client.get("/")

        self.assertContains(response, "vendor/bootstrap-5.3.8.min.css")
        self.assertContains(response, "vendor/htmx-2.0.11.min.js")
        self.assertContains(response, "css/panel.css")
        self.assertContains(response, 'data-bs-theme="dark"')
        self.assertNotContains(response, 'class="brand-mark"')
        self.assertContains(response, 'class="server-icon server-icon-fallback')

    @patch("monitoring.system.psutil.cpu_percent", return_value=12.5)
    def test_dashboard_includes_monitoring_and_polls_it_every_five_seconds(self, _cpu):
        self.client.force_login(self.user)

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'hx-get="/system/stats/"')
        self.assertContains(response, 'hx-trigger="every 5s"')
        self.assertContains(response, "CPU")
        self.assertContains(response, "12,5%")

    def test_servers_alias_redirects_and_requires_login(self):
        self.assertRedirects(self.client.get("/servers/"), "/login/", fetch_redirect_response=False)

        self.client.force_login(self.user)
        response = self.client.get("/servers/")
        self.assertRedirects(response, "/", fetch_redirect_response=False)

    def test_dashboard_get_does_not_mutate_service_state(self):
        self.client.force_login(self.user)

        self.client.get("/")

        self.assertEqual(
            get_game_manager().process_status("minecraft").value,
            "STOPPED",
        )

    @patch("games.status.minecraft.JavaServer")
    def test_start_stop_and_restart_are_post_only_and_update_a_fragment(self, java_server):
        java_server.return_value.status.return_value = SimpleNamespace(
            players=SimpleNamespace(online=2, max=20), latency=12.0
        )
        self.client.force_login(self.user)
        self.client.get("/")
        csrf_token = self.client.cookies["csrftoken"].value

        cases = (
            ("start", "RUNNING", "Zlecono uruchomienie"),
            ("stop", "STOPPED", "Zlecono zatrzymanie"),
            ("restart", "RUNNING", "Zlecono restart"),
        )
        for action, process_state, message in cases:
            with self.subTest(action=action):
                response = self.client.post(
                    f"/servers/minecraft/{action}/",
                    {"csrfmiddlewaretoken": csrf_token},
                    HTTP_HX_REQUEST="true",
                )
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, process_state)
                self.assertContains(response, message)
                self.assertNotContains(response, "<!doctype html>")

        self.assertEqual(
            self.client.get("/servers/minecraft/start/").status_code, 405
        )

    def test_failed_action_shows_generic_error_without_system_details(self):
        self.client.force_login(self.user)
        self.client.get("/")
        manager = get_game_manager()
        with patch.object(
            manager.service_backend,
            "start",
            side_effect=ServiceCommandRejected("private systemd response"),
        ) as start:
            response = self.client.post(
                "/servers/minecraft/start/", HTTP_HX_REQUEST="true"
            )

        start.assert_called_once_with("game-minecraft.service")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nie udało się wykonać operacji")
        self.assertNotContains(response, "private systemd response")

    def test_running_process_can_have_unknown_game_status(self):
        self.client.force_login(self.user)
        manager = get_game_manager()
        manager.start("minecraft")
        with patch.object(
            manager,
            "game_status",
            return_value=GameStatus(state=GameStatusState.UNKNOWN),
        ):
            response = self.client.get("/servers/minecraft/status/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "RUNNING")
        self.assertContains(response, "Nieznany")
        self.assertNotContains(response, "Nie sprawdzano")

    def test_protocol_text_is_autoescaped_in_status_fragment(self):
        self.client.force_login(self.user)
        manager = get_game_manager()
        manager.start("minecraft")
        with patch.object(
            manager,
            "game_status",
            return_value=GameStatus(
                state=GameStatusState.ONLINE,
                server_name="<script>alert(1)</script>",
            ),
        ):
            response = self.client.get("/servers/minecraft/status/")

        page = response.content.decode()
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)
        self.assertNotIn("<script>alert(1)</script>", page)

    def test_action_requires_csrf_and_rejects_unknown_slug(self):
        csrf_client = self.client_class(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        csrf_client.get("/")

        self.assertEqual(
            csrf_client.post("/servers/minecraft/start/").status_code, 403
        )

        response = csrf_client.post(
            "/servers/not-configured/start/",
            {"csrfmiddlewaretoken": csrf_client.cookies["csrftoken"].value},
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            get_game_manager().process_status("minecraft").value, "STOPPED"
        )

    def test_buttons_use_htmx_and_disable_the_card_while_an_action_runs(self):
        self.client.force_login(self.user)

        response = self.client.get("/")

        self.assertContains(response, 'hx-post="/servers/minecraft/start/"')
        self.assertContains(response, 'hx-target="#server-minecraft-content"')
        self.assertContains(response, 'hx-swap="outerHTML"')
        self.assertContains(response, 'hx-disabled-elt="closest fieldset"')
        self.assertContains(response, 'hx-trigger="every 5s"')
        self.assertContains(response, 'hx-confirm="Czy zatrzymać serwer Minecraft?"')
        self.assertContains(response, 'class="spinner-border spinner-border-sm htmx-indicator')
        self.assertContains(response, 'href="#main-content"')
