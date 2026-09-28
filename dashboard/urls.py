from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.index, name="index"),
    path("servers/", views.server_list, name="servers"),
    path("servers/<slug:slug>/status/", views.server_status, name="server-status"),
    path("servers/<slug:slug>/start/", views.start_server, name="server-start"),
    path("servers/<slug:slug>/stop/", views.stop_server, name="server-stop"),
    path("servers/<slug:slug>/restart/", views.restart_server, name="server-restart"),
]
