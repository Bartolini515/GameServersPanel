# Instrukcje dla agentów

## Cel i mapa repozytorium

To prywatny panel Django do zarządzania serwerami gier wpisanymi w YAML. `accounts/` obsługuje wspólne hasło i sesję, `games/` konfigurację, sterowanie usługami i status protokołu, `dashboard/` widoki kart, `monitoring/` metryki hosta, `templates/` HTML, `tests/` testy. Aktualny przepływ i granice modułów opisuje [architektura](docs/architecture.md).

## Praca i weryfikacja

- Używaj Pythona 3.12 i Pipenv. Instalacja: `pipenv install --dev`. Kontrola całości: `pipenv run python scripts/check.py`.
- Przed zmianą sprawdź `git status` i powiązany kod oraz testy. Zachowaj zastane zmiany i lokalne pliki ignorowane przez Git.
- Nowe zachowanie obejmij testem na właściwej granicy. Testy nie wywołują prawdziwego `systemctl`, nie uruchamiają gier i nie odpytują zewnętrznych serwerów.
- Po zmianie uruchom kontrolę całości. Jeśli jej nie można uruchomić, opisz dokładnie przyczynę i zakres wykonanych sprawdzeń.

## Granice implementacji i bezpieczeństwa

- Zachowaj prosty stos: Django Templates, HTMX, Bootstrap, SQLite, `psutil`, YAML i `systemd --user`. Nie dodawaj nowej technologii bez potrzeby wynikającej z zadania.
- Żądanie HTTP podaje tylko slug. Usługę wybiera wyłącznie zwalidowany YAML przez `GameManager`; polecenia w `SystemdService` mają listę argumentów, `shell=False` i timeout. Nie uruchamiaj procesu gry z Django.
- Akcje zmieniające stan wymagają POST, sesji i CSRF. Fragmenty HTMX też wymagają sesji. Status procesu i status gry są osobne; błąd protokołu daje `UNKNOWN`.
- `games.yaml`, `.env`, baza i sekrety są lokalne. Nie ujawniaj ich zawartości ani nie nadpisuj. `games.example.yaml` i `.env.example` są szablonami; `SECRET_KEY` pochodzi ze środowiska procesu lub lokalnego `.env`.
- Atrapa usług jest tylko dla `DEBUG=True`. Zmiany w istniejącej infrastrukturze systemd lub wdrożeniu nie są częścią zwykłej pracy nad kodem panelu.

## Definition of Done

- Zmiana spełnia wymaganie i ma adekwatne testy lub uzasadnienie ich braku.
- Komenda kontroli przechodzi, a wynik jest podany w raporcie.
- Gdy zmienia się kontrakt, aktualizuj odpowiedni dokument: [architekturę](docs/architecture.md), [decyzje](docs/decisions/), [diagnostykę](docs/troubleshooting.md) lub [workflow](docs/agentic-workflow.md).
- Raport końcowy wymienia zmienione pliki, wykonane kontrole i istotne ograniczenia.
