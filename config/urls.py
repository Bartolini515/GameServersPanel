from django.urls import include, path

urlpatterns = [
    path("", include("dashboard.urls")),
    path("", include("accounts.urls")),
    path("system/stats/", include("monitoring.urls")),
]
