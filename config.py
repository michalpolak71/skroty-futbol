"""Ustawienia bota. Większość da się nadpisać zmiennymi środowiskowymi na Railway."""
import os

NY_TZ = "America/New_York"
WARSAW_TZ = "Europe/Warsaw"

# prywatna / niepubliczna / publiczna  ->  private / unlisted / public
PLAYLIST_PRIVACY = os.getenv("PLAYLIST_PRIVACY", "unlisted")

# Ile wyszukiwań awaryjnych (search.list kosztuje 100 jednostek limitu z 10 000 dziennie)
MAX_FALLBACK_SEARCHES = int(os.getenv("MAX_FALLBACK_SEARCHES", "10"))

# Oficjalne kanały, z których brane są skróty (kolejność = priorytet przy duplikatach).
# Jeśli któryś uchwyt (@...) się nie odnajdzie, bot tylko wypisze ostrzeżenie w logach.
LEAGUES = {
    "ncaa": {
        "name": "NCAA",
        "espn_path": "college-football",
        "espn_params": {"groups": "80", "limit": "300"},  # 80 = FBS (najwyższa dywizja)
        "channels": [
            "@ESPNCFB",
            "@ESPN",
            "@CBSSports",
            "@FOXSports",
            "@ACCDigitalNetwork",
            "@Big12Conference",
            "@NBCSports",
        ],
        "use_nickname": False,  # w NCAA przydomki się powtarzają (Tigers, Wildcats...)
        "max_videos": int(os.getenv("NCAA_MAX_VIDEOS", "30")),
        "latest_title": "NCAA – najnowszy weekend",
    },
    "nfl": {
        "name": "NFL",
        "espn_path": "nfl",
        "espn_params": {},
        "channels": ["@NFL"],
        "use_nickname": True,  # w NFL przydomki są unikalne (Bills, Chiefs...)
        "max_videos": int(os.getenv("NFL_MAX_VIDEOS", "20")),
        "latest_title": "NFL – najnowsza kolejka",
    },
}

# Kanały, którym ufamy przy wyszukiwaniu awaryjnym (porównanie po nazwie kanału).
TRUSTED_CHANNEL_TITLES = {
    "espn", "espn college football", "cbs sports", "cbs sports college football",
    "fox sports", "fox college football", "nfl", "big ten network", "sec network",
    "acc digital network", "big 12 conference", "nbc sports", "the cw sports",
}

# Jednorazowe dodatkowe przebiegi: (data w Polsce, liga, "dzień uruchomienia" w USA).
# 2.11.2026: przebudowa playlisty NCAA za 25–31.10 według nowej kolejności
# (sensacje → niespodzianki → wygrane faworytów). Aktualizuje tylko stałą playlistę.
EXTRA_RUNS = [
    ("2026-11-02", "ncaa", "2026-11-01"),
]
