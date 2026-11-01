"""Bot skrótów futbolu amerykańskiego.

Niedziela rano (czas polski): NCAA z ostatniego tygodnia.
Poniedziałek rano: NFL z ostatniego tygodnia (MNF z poprzedniego tygodnia + TNF + niedziela).

Uruchomienie:
  python main.py                 # liga wybierana wg dnia tygodnia
  python main.py --league nfl    # wymuszenie ligi
  python main.py --dry-run       # tylko wypisz ranking, nic nie twórz na YouTube
  python main.py --date 2026-11-02 --league nfl   # symulacja innego dnia
"""
import argparse
import sys
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import config
import espn
import notify
from matching import norm
from matching import assign_videos
from scoring import excitement, order_key, with_views
from youtube import QuotaError, YouTube


def pick_league(arg):
    if arg != "auto":
        return arg
    wd = datetime.now(ZoneInfo(config.WARSAW_TZ)).weekday()
    return {6: "ncaa", 0: "nfl"}.get(wd)


def playlist_title(cfg, games, last_day):
    season_type = Counter(g["season_type"] for g in games).most_common(1)[0][0]
    week = Counter(g["week"] for g in games).most_common(1)[0][0]
    year = games[0]["season_year"]
    label = f"tydzień {week}" if season_type == 2 and week else "faza posezonowa"
    return f"{cfg['name']} {year} – {label} ({last_day:%d.%m.%Y})"


def describe(cfg, ranked, channels):
    lines = [
        ("Oficjalne skróty meczów ułożone od drużyn najwyżej notowanych w rankingu AP Top 25, "
         "a pozostałe od najciekawszego meczu. Bez wyników – bez spoilerów."
         if cfg["name"] == "NCAA" else
         "Oficjalne skróty meczów ułożone od drużyn z najlepszym bilansem. Bez wyników – bez spoilerów."),
        "",
    ]
    for i, g in enumerate(ranked, 1):
        lines.append(f"{i}. {g['away']['display']} – {g['home']['display']}")
    owners = set()
    for g in ranked:
        cid = g["video"]["channel_id"]
        owners.add(channels[cid]["title"] if cid in channels else g["video"].get("channel_title", ""))
    owners = sorted(o for o in owners if o)
    lines += ["", "Wszystkie filmy należą do ich autorów"
              + (f" ({', '.join(owners)})" if owners else "")
              + ". Playlista jedynie porządkuje oficjalne skróty."]
    return "\n".join(lines)


def run(league, today_us, dry_run):
    cfg = config.LEAGUES[league]
    dates = [today_us - timedelta(days=i) for i in range(7, 0, -1)]
    since = datetime.combine(dates[0], time(0), ZoneInfo(config.NY_TZ)).astimezone(timezone.utc)
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"== {cfg['name']}: mecze {dates[0]} – {dates[-1]} (czas USA)")

    games = espn.fetch_games(cfg["espn_path"], cfg["espn_params"], dates)
    print(f"Zakończonych meczów: {len(games)}")
    if not games:
        notify.send(f"{cfg['name']}: brak meczów", "W tym tygodniu nie znaleziono zakończonych meczów.")
        return 0
    for g in games:
        g["excitement"], g["why"] = excitement(g, league)
    games.sort(key=lambda g: g["excitement"], reverse=True)

    yt = YouTube()
    channels = yt.resolve_channels(cfg["channels"])
    uploads = []
    for cid, ch in channels.items():
        got = yt.recent_uploads(ch["uploads"], since_iso, cid)
        print(f"  {ch['title']}: {len(got)} filmów z ostatniego tygodnia")
        uploads += got
    candidates = [v for v in uploads if " highlight" in norm(v["title"])]
    candidates = yt.enrich(candidates)
    priority = {cid: ch["priority"] for cid, ch in channels.items()}
    found = assign_videos(games, candidates, priority, cfg["use_nickname"])

    # Wyszukiwanie awaryjne dla najciekawszych meczów bez dopasowania
    searches = 0
    for g in games:
        if len(found) >= cfg["max_videos"] or searches >= config.MAX_FALLBACK_SEARCHES:
            break
        if g["id"] in found:
            continue
        q = f"{g['away']['display']} vs {g['home']['display']} highlights"
        res = yt.search(q, since_iso)
        searches += 1
        trusted = [v for v in res if v["channel_id"] in channels
                   or norm(v["channel_title"]).strip() in config.TRUSTED_CHANNEL_TITLES]
        trusted = yt.enrich(trusted)
        hit = assign_videos([g], trusted, priority, cfg["use_nickname"])
        if g["id"] in hit:
            found[g["id"]] = hit[g["id"]]

    ranked = []
    for g in games:
        v = found.get(g["id"])
        if v:
            g["video"] = v
            g["final"] = with_views(g["excitement"], v.get("views"))
            ranked.append(g)
    ranked.sort(key=lambda g: order_key(g, league))
    ranked = ranked[:cfg["max_videos"]]

    print(f"\nRanking ({len(ranked)} skrótów, {len(games) - len(found)} meczów bez skrótu):")
    for i, g in enumerate(ranked, 1):
        rk = lambda t: f"#{t['rank']} " if t.get('rank') else ""
        print(f"{i:>2}. [{g['final']:>5}] {rk(g['away'])}{g['away']['display']} {g['away']['score']} – "
              f"{g['home']['score']} {rk(g['home'])}{g['home']['display']}  ({', '.join(g['why']) or '-'})\n"
              f"      https://youtu.be/{g['video']['id']}  {g['video']['title']}")
    print(f"Zużyty limit YouTube API: ~{yt.units} jednostek")

    if dry_run or not ranked:
        return 0

    ids = [g["video"]["id"] for g in ranked]
    title = playlist_title(cfg, ranked, dates[-1])
    desc = describe(cfg, ranked, channels)
    try:
        yt.sync_playlist(title, desc, config.PLAYLIST_PRIVACY, ids)
        latest = yt.sync_playlist(cfg["latest_title"], desc, config.PLAYLIST_PRIVACY, ids)
    except QuotaError as e:
        print(f"!! {e}")
        notify.send(f"{cfg['name']}: limit API", str(e))
        return 1
    link = f"https://www.youtube.com/playlist?list={latest}"
    print(f"\nGotowe: {link}  (limit: ~{yt.units} jednostek)")
    notify.send(f"{cfg['name']}: {len(ranked)} skrótów gotowe",
                "Playlista ze skrótami czeka.", link)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--league", choices=["auto", "ncaa", "nfl"], default="auto")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--date", help="dzień uruchomienia (data USA), np. 2026-11-02")
    args = ap.parse_args()

    league = pick_league(args.league)
    if not league:
        print("Dziś nie niedziela ani poniedziałek – nic do zrobienia (użyj --league).")
        return 0
    today_us = date.fromisoformat(args.date) if args.date else datetime.now(ZoneInfo(config.NY_TZ)).date()
    return run(league, today_us, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
