from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from monitoring.system import SystemStats, format_bytes, format_uptime, read_system_stats


class SystemStatsTests(TestCase):
    @patch("monitoring.system.time.time", return_value=1_700_100)
    @patch("monitoring.system.psutil.boot_time", return_value=1_700_000)
    @patch("monitoring.system.psutil.getloadavg", return_value=(0.12, 0.34, 0.56))
    @patch("monitoring.system.psutil.disk_usage", return_value=SimpleNamespace(used=2048, total=4096, percent=50.0))
    @patch("monitoring.system.psutil.virtual_memory", return_value=SimpleNamespace(used=1024, total=8192, percent=12.5))
    @patch("monitoring.system.psutil.cpu_percent", return_value=23.4)
    def test_read_system_stats_normalizes_psutil_values(self, *_mocks):
        stats = read_system_stats("/test-disk")
        _mocks[0].assert_called_once_with(interval=0.1)

        self.assertEqual(stats.cpu_percent, 23.4)
        self.assertEqual((stats.ram_used_bytes, stats.ram_total_bytes, stats.ram_percent), (1024, 8192, 12.5))
        self.assertEqual((stats.disk_used_bytes, stats.disk_total_bytes, stats.disk_percent), (2048, 4096, 50.0))
        self.assertEqual(stats.load_average, (0.12, 0.34, 0.56))
        self.assertEqual(stats.uptime_seconds, 100)

    @patch("monitoring.system.psutil.boot_time", side_effect=NotImplementedError)
    @patch("monitoring.system.psutil.getloadavg", side_effect=AttributeError)
    @patch("monitoring.system.psutil.disk_usage", side_effect=OSError)
    @patch("monitoring.system.psutil.virtual_memory", side_effect=OSError)
    @patch("monitoring.system.psutil.cpu_percent", side_effect=OSError)
    def test_unavailable_platform_metrics_are_none(self, *_mocks):
        stats = read_system_stats("Z:\\")

        self.assertIsNone(stats.cpu_percent)
        self.assertIsNone(stats.ram_total_bytes)
        self.assertIsNone(stats.disk_total_bytes)
        self.assertIsNone(stats.load_average)
        self.assertIsNone(stats.uptime_seconds)

    def test_formatters_handle_values_and_unavailable_metrics(self):
        self.assertEqual(format_bytes(0), "0 B")
        self.assertEqual(format_bytes(1536), "1.5 KiB")
        self.assertEqual(format_bytes(None), "niedostępne")
        self.assertEqual(format_uptime(90061), "1 d 1 godz.")
        self.assertEqual(format_uptime(None), "niedostępne")


class SystemStatsViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="panel", password="a-long-test-password"
        )

    def test_stats_endpoint_requires_login_and_returns_fragment(self):
        self.assertRedirects(
            self.client.get("/system/stats/"),
            "/login/",
            fetch_redirect_response=False,
        )

        self.client.force_login(self.user)
        response = self.client.get("/system/stats/", HTTP_HX_REQUEST="true")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="host-stats-content"')
        self.assertNotContains(response, "<!doctype html>")

    @patch(
        "monitoring.views.read_system_stats",
        return_value=SystemStats(None, None, None, None, None, None, None, None, None),
    )
    def test_stats_fragment_marks_missing_metrics_unavailable(self, _read_stats):
        self.client.force_login(self.user)

        response = self.client.get("/system/stats/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CPU")
        self.assertContains(response, "RAM")
        self.assertContains(response, "Dysk")
        self.assertContains(response, "Load average")
        self.assertContains(response, "Uptime")
        self.assertContains(response, "niedostępne")
