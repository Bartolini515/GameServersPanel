from functools import wraps

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse


def panel_login_required(view_func):
    """Protect a page or fragment and send expired HTMX sessions to login."""

    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if request.user.is_authenticated:
            return view_func(request, *args, **kwargs)

        if request.headers.get("HX-Request", "").lower() == "true":
            response = HttpResponse(status=200)
            response["HX-Redirect"] = reverse("accounts:login")
            return response

        return redirect(settings.LOGIN_URL)

    return wrapped
