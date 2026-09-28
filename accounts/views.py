from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods, require_POST
from datetime import datetime

from .access import panel_login_required
from .forms import PasswordOnlyLoginForm

last_login_attempt: datetime | None = None
login_attempts_counter: int = 0

@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("/")

    form = PasswordOnlyLoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        # Anti brute-force mechanism: limit login attempts to 3 per second
        global last_login_attempt
        global login_attempts_counter
        login_attempts_counter += 1
        if last_login_attempt is not None:
            time_since_last_attempt = datetime.now() - last_login_attempt
            if time_since_last_attempt.total_seconds() > 1:
                login_attempts_counter = 0
                last_login_attempt = datetime.now()
                
            if login_attempts_counter > 3:
                form.add_error(None, "Zbyt wiele prób logowania. Spróbuj ponownie później.")
                return render(request, "accounts/login.html", {"form": form}, status=429)
        else:
            last_login_attempt = datetime.now()
                
        user = authenticate(
            request,
            username="panel",
            password=form.cleaned_data["password"],
        )
        if user is not None:
            login(request, user)
            login_attempts_counter = 0
            return redirect("/")
        form.add_error(None, "Hasło jest nieprawidłowe.")

    return render(request, "accounts/login.html", {"form": form})


@panel_login_required
@require_POST
def logout_view(request):
    logout(request)
    return redirect("/login/")
