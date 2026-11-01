# Skróty futbolu – bot playlist

Co tydzień tworzy na Twoim kanale YouTube playlisty z **oficjalnymi** skrótami meczów, ułożone od najciekawszego:

- **niedziela ok. 9:30** (latem 10:30) – NCAA (najwyższa dywizja FBS) z ostatniego tygodnia
- **poniedziałek ok. 9:30** (latem 10:30) – NFL z ostatniego tygodnia (Monday Night z poprzedniego tygodnia + Thursday Night + niedziela)

Każde uruchomienie aktualizuje dwie playlisty:
1. **stałą** – „NCAA – najnowszy weekend…” / „NFL – najnowsza kolejka…” – zawsze ten sam link, zapisz go w zakładkach albo na ekranie telefonu,
2. **archiwalną** – np. „NFL 2026 – tydzień 9 – od najciekawszego (01.11.2026)”.

Domyślnie playlisty są **niepubliczne** (widzi je każdy, kto ma link; nie ma ich w wyszukiwarce). Opis playlisty nie zdradza wyników.

Ranking liczy: różnicę punktów, dogrywki, odrobione straty i comeback w 4. kwarcie, zmiany prowadzenia, niespodzianki (NCAA: ranking AP Top 25, NFL: bilans drużyn), dużo punktów, a lekko także liczbę wyświetleń skrótu.

---

## Krok 1 – Google Cloud (ok. 10 min, jednorazowo)

1. Wejdź na https://console.cloud.google.com, utwórz projekt, np. „skroty-futbol”.
2. **APIs & Services → Library** → wyszukaj **YouTube Data API v3** → **Enable**.
3. **APIs & Services → OAuth consent screen** (Google Auth Platform):
   - typ: **External**, nazwa aplikacji dowolna, Twój e-mail,
   - **Audience → Publish app → In production**. To ważne: w trybie „Testing” połączenie wygasa po 7 dniach i bot przestanie działać.
4. **Credentials → Create credentials → OAuth client ID** → typ **Desktop app** → pobierz JSON i zapisz jako `client_secret.json` w folderze projektu.
5. (Opcjonalnie, do testu) **Create credentials → API key** – przyda się do próby „na sucho”.

## Krok 2 – połączenie z Twoim kanałem (na Twoim komputerze)

```
pip install google-auth-oauthlib requests tzdata
python auth_setup.py
```

Otworzy się przeglądarka. Zaloguj się i **wybierz kanał**, na którym mają być playlisty. Google pokaże ostrzeżenie „aplikacja niezweryfikowana” – to normalne przy własnej aplikacji: **Zaawansowane → Przejdź do…**.
Skrypt wypisze 3 linijki `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`.

**Plików `client_secret.json` ani tych wartości nie wrzucaj do GitHuba.**

## Krok 3 – próba na sucho (nic nie tworzy na YouTube)

Windows (PowerShell):
```
$env:YOUTUBE_API_KEY="twój-klucz"
python main.py --league nfl --dry-run
```
Wypisze ranking z linkami do skrótów i zużycie limitu API. Sprawdź, czy kolejność ma sens i czy filmy pasują do meczów.
Jeśli w logu zobaczysz `! nie znaleziono kanału @...` – ten kanał po prostu zostanie pominięty (bot i tak dosłuży brakujące skróty wyszukiwaniem).

## Krok 4 – Railway

1. Wrzuć folder do nowego, **prywatnego** repo na GitHubie (bez `client_secret.json`).
2. Railway → **New Project → Deploy from GitHub repo**.
3. **Variables**: `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`.
4. Harmonogram jest już w `railway.json` (`30 8 * * 0,1` = niedziela i poniedziałek 8:30 UTC, czyli 9:30 zimą / 10:30 latem, zaraz po odnowieniu limitu YouTube). Sprawdź w **Settings → Cron Schedule**, że się pojawił.
5. Pierwszy test od razu: w Railway ustaw tymczasowo Start Command `python main.py --league nfl`, uruchom deploy, po udanym przebiegu przywróć `python main.py`.

## Zmienne opcjonalne

| Zmienna | Domyślnie | Co robi |
|---|---|---|
| `PLAYLIST_PRIVACY` | `unlisted` | `private` / `unlisted` / `public` |
| `NCAA_MAX_VIDEOS` | `30` | ile skrótów NCAA w playliście |
| `NFL_MAX_VIDEOS` | `20` | ile skrótów NFL |
| `MAX_FALLBACK_SEARCHES` | `10` | ile wyszukiwań awaryjnych (każde zużywa 100 z 10 000 jednostek dziennie) |
| `NTFY_TOPIC` | – | powiadomienie push na telefon: zainstaluj aplikację **ntfy**, zasubskrybuj wymyśloną, trudną do zgadnięcia nazwę (np. `skroty-michal-8k3x`) i wpisz ją tutaj |

## Limit YouTube API

Darmowe 10 000 jednostek dziennie. Typowe uruchomienie NFL zużywa ok. 2–3 tys., NCAA ok. 4–7 tys. (dodanie filmu do playlisty = 50 jednostek, a bot uzupełnia dwie playlisty). Niedziela i poniedziałek to różne dni, więc limity się nie sumują.

## Pliki

- `main.py` – przebieg całości
- `espn.py` – wyniki meczów (publiczny scoreboard ESPN)
- `scoring.py` – wskaźnik emocji
- `matching.py` – dopasowanie filmów do meczów, odrzucanie Shorts, konferencji, „top plays” itp.
- `youtube.py` – YouTube API (kanały, playlisty)
- `config.py` – lista kanałów i ustawienia
- `notify.py` – powiadomienie ntfy
- `auth_setup.py` – jednorazowe połączenie z kanałem
