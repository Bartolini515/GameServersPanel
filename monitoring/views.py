from django.conf import settings
from django.shortcuts import render
from django.views.decorators.http import require_GET

from accounts.access import panel_login_required
from monitoring.system import read_system_stats


def stats_context():
    return {
        "stats": read_system_stats(settings.MONITOR_DISK_PATH),
    }


@panel_login_required
@require_GET
def system_stats(request):
    return render(request, "monitoring/_system_stats.html", stats_context())
