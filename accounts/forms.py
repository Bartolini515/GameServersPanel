from django import forms


class PasswordOnlyLoginForm(forms.Form):
    password = forms.CharField(
        label="Hasło",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "autocomplete": "current-password",
            }
        ),
        error_messages={"required": "Wpisz hasło."},
    )
