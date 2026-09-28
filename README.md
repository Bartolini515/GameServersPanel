# Game Servers Panel

Panel WWW do sterowania serwerami gier zdefiniowanymi w YAML i podglądu obciążenia hosta. Aplikacja używa Django, Django Templates, HTMX, Bootstrap, SQLite i `psutil`; istniejące usługi `systemd --user` uruchamiają gry poza procesem panelu.

## Funkcje

- Logowanie jednym hasłem technicznego konta `panel` przez sesję Django i wylogowanie.
- Lista gier, uruchamianie, zatrzymywanie i restartowanie usług.
- Oddzielny status procesu i opcjonalny status gry (`generic` TCP, Minecraft Java, A2S).
- CPU, RAM, dysk, load average i uptime hosta. Karty i metryki odświeżają się przez HTMX co 5 sekund bez przeładowania strony.

## Wymagania i instalacja lokalna

Wymagane są Python 3.12 i Pipenv. Linux z istniejącymi usługami `systemd --user` jest potrzebny do rzeczywistego sterowania grami. Lokalny podgląd może działać na Windows/macOS/Linux z atrapą usług w trybie debug.

```text
pipenv --python 3.12
pipenv install --dev
```

Skopiuj `games.example.yaml` do `games.yaml` oraz [`.env.example`](.env.example) do `.env`. Oba pliki docelowe są ignorowane przez Git. W `.env` ustaw własny, długi losowy `SECRET_KEY`; bez niego aplikacja nie wystartuje. Django wczytuje `.env` z katalogu projektu przy starcie. Zmienne ustawione już w środowisku procesu mają pierwszeństwo.

```powershell
if (-not (Test-Path -LiteralPath .\games.yaml)) { Copy-Item .\games.example.yaml .\games.yaml }
if (-not (Test-Path -LiteralPath .\.env)) { Copy-Item .\.env.example .\.env }
```

Plik `.env` obsługuje proste linie `NAZWA=wartość`, opcjonalne pojedyncze lub podwójne cudzysłowy wokół całej wartości, puste linie i komentarze zaczynające się od `#`. Nie używa interpolacji ani komentarzy na końcu linii. Dostępne ustawienia:

| Zmienna | Cel | Domyślna wartość |
|---|---|---|
| `SECRET_KEY` | Klucz sesji i podpisów Django; wymagany w `.env` lub środowisku procesu | brak |
| `DEBUG` | Lokalny podgląd i domyślna atrapa przy wartości `true` | `false` |
| `GAME_SERVICE_BACKEND` | `fake` albo `systemd`; `fake` wymaga `DEBUG=true` | `fake` przy debug, inaczej `systemd` |
| `GAME_CONFIG_PATH` | Ścieżka do YAML gier | `games.yaml` w katalogu projektu |
| `MONITOR_DISK_PATH` | Ścieżka systemu plików do pomiaru dysku | katalog główny bieżącego dysku/systemu |
| `ALLOWED_HOSTS` | Lista hostów Django rozdzielona przecinkami | `localhost,127.0.0.1` |

Przy `DEBUG=true` domyślny `FakeSystemdService` zmienia stany tylko w pamięci procesu panelu. Nie uruchamia serwerów gier; status protokołu może nadal pokazywać `Nieznany`, jeśli żaden serwer nie odpowiada.

Przygotuj standardowe tabele Django i wcześniej ustaw hasło zwykłego użytkownika o nazwie `panel`. Aplikacja nie oferuje przepływu tworzenia ani zmiany hasła. Jeśli to pierwsze uruchomienie lokalne, konto można utworzyć w interaktywnym shellu:

```text
pipenv run python manage.py migrate
pipenv run python manage.py shell
```

```python
from getpass import getpass
from django.contrib.auth import get_user_model
get_user_model().objects.create_user(username="panel", password=getpass("Wspólne hasło: "))
```

Jeżeli konto `panel` już istnieje, ustaw lub zmień jego hasło przez `pipenv run python manage.py changepassword panel`. Polecenie pyta o hasło interaktywnie; hasła panelu nie zapisuj w `.env`.

Uruchom `pipenv run python manage.py runserver`, otwórz `http://127.0.0.1:8000/` i zaloguj się hasłem konta `panel`.

## Konfiguracja gier

`games.yaml` określa slug, nazwę, istniejącą jednostkę `.service`, opcjonalną ikonę i opcjonalne `status` z `type`, `host`, `port`, `timeout_s`. Format pokazuje [szablon](games.example.yaml). Zmiany YAML są odczytywane przy budowie menedżera procesu; po ich edycji uruchom proces Django ponownie. Dodanie prostej gry nie wymaga zmiany kodu, jeśli jej usługa już istnieje.

Bez wpisu `status` panel pokazuje status gry jako niedostępny przy działającym procesie. Timeout lub błąd adaptera daje `Nieznany`. Widok nie używa nazwy usługi pochodzącej z URL ani formularza.

## Testy i kontrola jakości

Jedna komenda uruchamia weryfikację `Pipfile.lock`, systemowe kontrole Django i wszystkie testy:

```text
pipenv run python scripts/check.py
```

Komenda wykorzystuje `games.example.yaml`, atrapę usług i testowy klucz tylko w procesach kontroli. Nie wymaga lokalnego `.env`, `games.yaml`, prawdziwego systemd ani uruchomionych gier. Dla pojedynczego testu użyj `pipenv run python manage.py test tests.test_game_manager`, zapewniając `SECRET_KEY` w `.env` lub środowisku procesu.

## Architektura i dokumentacja

Widoki Django renderują pełną stronę i fragmenty HTML. `GameManager` wiąże zwalidowany YAML z backendem usług i adapterami protokołów, a monitoring pobiera bieżący odczyt przez `psutil`. SQLite służy do wbudowanych tabel Django, głównie auth i sesji; historii metryk nie ma.

- [Aktualna architektura i przepływy](docs/architecture.md)
- [Decyzje architektoniczne](docs/decisions/README.md)
- [Diagnostyka](docs/troubleshooting.md)
- [Przewodnik pracy agentów](docs/agentic-workflow.md) i [reguły repozytorium](AGENTS.md)
- [Historyczny plan implementacji](docs/superpowers/plans/2026-09-27-game-servers-panel.md)

Zmiany kodu warto zaczynać od powiązanych testów i kończyć komendą kontroli. Bieżący opis architektury znajduje się w `docs/architecture.md`; plan implementacji dokumentuje wcześniejsze etapy projektu.
