# Diagnostyka panelu

Kontrole poniżej dotyczą kodu i lokalnego podglądu. Nie opisują instalowania serwerów gier ani konfiguracji infrastruktury.

## `SECRET_KEY must be set in the environment or .env`

**Potwierdzenie:** polecenie Django kończy się `ImproperlyConfigured` przed uruchomieniem. **Działanie:** skopiuj `.env.example` do `.env`, ustaw w nim niepusty, losowy `SECRET_KEY` i ponów polecenie. Możesz też ustawić klucz w środowisku procesu; ma ono pierwszeństwo przed `.env`. Nie zapisuj prawdziwego klucza w repozytorium. Dla samej weryfikacji użyj `pipenv run python scripts/check.py`, który ustawia testową wartość tylko w procesach kontroli.

## `games.E001` lub brak kart

**Potwierdzenie:** `pipenv run python manage.py check` zwraca `games.E001` albo aplikacja nie może odczytać `games.yaml`. **Działanie:** sprawdź ścieżkę `GAME_CONFIG_PATH` i porównaj strukturę z [`games.example.yaml`](../games.example.yaml). Loader wymaga niepustej mapy `games`, poprawnych slugów i jednostek `.service`, bez duplikatów i nieznanych pól. Po edycji YAML uruchom proces Django ponownie, bo menedżer jest cache'owany. **Weryfikacja:** ponów `manage.py check` i odśwież dashboard.

## Przyciski zmieniają stan tylko w podglądzie

**Potwierdzenie:** `DEBUG=true` i backend `fake`; zmiana znika po restarcie procesu. **Wyjaśnienie:** atrapa przechowuje stan w pamięci i nie uruchamia gry. Dla realnego działania aplikacja musi używać backendu `systemd` w środowisku z istniejącymi jednostkami użytkownika. **Weryfikacja:** po zmianie konfiguracji backendu stan karty powinien odpowiadać stanowi jednostki; nie testuj tego na produkcyjnych usługach w ramach zwykłych testów kodu.

## `Nie można odczytać stanu procesu` lub błąd akcji

**Potwierdzenie:** karta pokazuje ogólny komunikat; log aplikacji zawiera błąd `games` lub `games.actions`. **Działanie:** sprawdź, czy nazwa usługi w YAML jest poprawna i czy istniejący menedżer `systemd --user` jest dostępny dla procesu panelu. Kod rozróżnia brak jednostki, odmowę, konflikt, timeout i błędną odpowiedź. Nie umieszczaj surowego błędu systemowego w HTML. **Weryfikacja:** ponów odczyt statusu po usunięciu przyczyny; testy `tests/test_systemd.py` sprawdzają mapowanie błędów bez prawdziwych jednostek.

### Status działa, ale akcja `systemd_system` jest odrzucana

**Potwierdzenie:** status jednostki `game-vintagestory.service` jest widoczny, ale START, STOP albo RESTART pokazuje ogólny błąd. **Działanie:** upewnij się, że proces panelu może odczytać jednostkę przez systemowy menedżer systemd i że wdrożeniowa reguła `sudoers` dopuszcza dokładnie trzy polecenia backendu przez `sudo -n`. Ścieżki (`/usr/bin/sudo`, `/usr/bin/systemctl`), flagi, ich kolejność i nazwa jednostki muszą być zgodne z kodem. Sprawdź składnię lokalnej reguły przez `visudo -c`; nie rozszerzaj jej do ogólnego `sudo` ani innych jednostek. **Weryfikacja:** jako konto panelu sprawdź odczyt `systemctl --system show game-vintagestory.service` i wykonaj akcje z panelu. Backend odrzuca inne nazwy jednostek; stan `active/running` wymaga dodatniego `MainPID`, więc jednostka musi uruchamiać grę na pierwszym planie.

## Proces działa, a status gry jest `Nieznany`

**Potwierdzenie:** proces ma `RUNNING`, ale adapter zwraca `UNKNOWN`. **Działanie:** sprawdź `type`, `host`, `port` i `timeout_s` w YAML oraz czy gra zdążyła otworzyć protokół. Timeout i błąd protokołu celowo dają `UNKNOWN`; nie oznacza to automatycznie zatrzymania procesu. Bez sekcji `status` karta pokazuje `Niedostępny`. **Weryfikacja:** kolejny odczyt HTMX po odpowiedzi protokołu pokaże `ONLINE`; testy adaptera znajdują się w `tests/test_status_adapters.py`.

## Fragmenty nie odświeżają się

**Potwierdzenie:** w narzędziach przeglądarki brak żądań GET do `/servers/<slug>/status/` lub `/system/stats/` co 5 s. **Działanie:** sprawdź załadowanie lokalnego `static/vendor/htmx-2.0.11.min.js`, stan sesji i odpowiedź sieciową. Wygasła sesja HTMX powinna odesłać `HX-Redirect` do `/login/`. Przy opóźnieniach uwzględnij, że przeglądarka może spowalniać karty w tle. **Weryfikacja:** po powrocie do aktywnej karty żądania i fragmenty powinny wrócić.
