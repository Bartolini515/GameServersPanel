# 0001 — YAML, GameManager i istniejące usługi systemd

## Status

Zaakceptowana.

## Kontekst

Panel ma obsługiwać wiele gier bez zmiany kodu dla każdego prostego serwera. Proces gry musi działać niezależnie od Django, a użytkownik może sterować wyłącznie dozwolonymi usługami.

## Decyzja

Definicje serwerów są w lokalnym, ignorowanym przez Git `games.yaml`, z wersjonowanym `games.example.yaml` jako szablonem. `GameManager` rozwiązuje slug na zwalidowaną definicję i przekazuje jej nazwę usługi do `ServiceBackend`. Realny backend używa istniejących usług `systemd --user`; lokalny backend pamięciowy działa wyłącznie przy `DEBUG=True`. Adaptery statusu gry są niezależne od backendu procesu.

## Rozważane alternatywy

- Definicje w tabeli SQLite: wymagałyby interfejsu edycji i migracji, których MVP nie potrzebuje.
- Uruchamianie procesów gier przez Django: wiązałoby ich żywotność z procesem panelu.
- Nazwa usługi z żądania HTTP: umożliwiałaby sterowanie usługami spoza katalogu.

## Konsekwencje

Prosty serwer dodaje się przez YAML, a kod nie zna konkretnych gier. Zmiana katalogu wymaga restartu procesu panelu ze względu na cache fabryki. Istniejąca infrastruktura musi udostępniać odpowiednie jednostki użytkownika; panel ich nie tworzy. Testy backendu używają atrap wywołania poleceń, a nie prawdziwego systemd.
