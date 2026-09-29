import re

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import Client, RequestFactory, TestCase

from accounts.access import panel_login_required


class AuthenticationViewsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="panel", password="a-long-test-password"
        )

    def test_login_page_asks_only_for_password(self):
        response = self.client.get("/login/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="password"')
        self.assertNotContains(response, 'name="username"')

    def test_valid_shared_password_creates_session(self):
        response = self.client.post(
            "/login/", {"password": "a-long-test-password"}
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/")
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_invalid_password_shows_generic_error(self):
        response = self.client.post("/login/", {"password": "wrong"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hasło jest nieprawidłowe")
        self.assertContains(response, 'class="alert alert-danger text-center login-error"')
        self.assertNotContains(response, '<ul class="errorlist')
        page = response.content.decode()
        self.assertLess(page.index('name="password"'), page.index('class="alert alert-danger text-center login-error"'))
        self.assertLess(page.index('class="alert alert-danger text-center login-error"'), page.index('type="submit">Zaloguj się'))
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_account_with_other_username_cannot_log_in(self):
        get_user_model().objects.create_user(username="other", password="same")

        response = self.client.post("/login/", {"password": "same"})

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_logout_is_post_only_and_clears_session(self):
        self.client.force_login(self.user)

        self.assertEqual(self.client.get("/logout/").status_code, 405)
        response = self.client.post("/logout/")

        self.assertRedirects(response, "/login/")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_htmx_request_without_session_redirects_to_full_login(self):
        @panel_login_required
        def private_view(request):
            return HttpResponse("private")

        request = RequestFactory().get("/private/", HTTP_HX_REQUEST="true")
        request.user = AnonymousUser()
        response = private_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["HX-Redirect"], "/login/")

    def test_mutating_auth_views_require_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.get("/login/")
        self.assertEqual(
            client.post("/login/", {"password": "a-long-test-password"}).status_code,
            403,
        )

        client.force_login(self.user)
        self.assertEqual(client.post("/logout/").status_code, 403)

    def test_login_form_contains_csrf_token(self):
        response = self.client.get("/login/")

        self.assertRegex(
            response.content.decode(),
            re.compile(r'name="csrfmiddlewaretoken"'),
        )
