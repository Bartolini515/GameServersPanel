# 0002 — HTML i polling HTMX co 5 sekund

## Status

Zaakceptowana.

## Kontekst

Panel ma mieć proste, responsywne karty z bieżącym stanem i działaniem przycisków bez pełnego przeładowania strony. Historia metryk i strumieniowanie zdarzeń nie są wymagane.

## Decyzja

Django Templates renderują stronę i fragmenty HTML. HTMX pobiera status każdej karty oraz metryki hosta z `hx-trigger="every 5s"`; akcje używają POST i podmieniają odpowiednią kartę po odpowiedzi. Bootstrap dostarcza komponenty wizualne. Dane monitoringu są próbkowane przez `psutil` na żądanie i nie są utrwalane.

## Rozważane alternatywy

- SPA i osobne API JSON: zwiększyłyby liczbę warstw dla małego panelu.
- WebSockety: wymagałyby dodatkowego mechanizmu połączeń i zarządzania stanem.
- Historia metryk w bazie: nie wynika z wymagań bieżącego podglądu.

## Konsekwencje

Widoki i szablony stanowią prostą całość, a każda karta może odświeżać się niezależnie. Interwał 5 s jest ustawieniem klienta, nie gwarancją czasu dostarczenia; przeglądarka może opóźnić żądanie. Liczba żądań rośnie wraz z liczbą kart i otwartych przeglądarek, co należy ocenić przed dużą rozbudową.
