"""Pobieranie zakończonych meczów z publicznego scoreboardu ESPN."""
import requests

BASE = "https://site.api.espn.com/apis/site/v2/sports/football/{path}/scoreboard"


def _int(x, default=0):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return default


def _team(c):
    t = c.get("team") or {}
    rank = _int((c.get("curatedRank") or {}).get("current"), 99)
    record = None
    for r in c.get("records") or []:
        if r.get("type") == "total" or r.get("name") == "overall":
            record = r.get("summary")
            break
    return {
        "location": t.get("location") or "",
        "nickname": t.get("name") or "",
        "display": t.get("displayName") or "",
        "short": t.get("shortDisplayName") or "",
        "score": _int(c.get("score")),
        "rank": rank if 1 <= rank <= 25 else None,
        "record": record,
        "lines": [_int(ls.get("value")) for ls in (c.get("linescores") or [])],
        "home": c.get("homeAway") == "home",
    }


def _parse_event(ev, week, season_year, season_type):
    comps = ev.get("competitions") or []
    if not comps:
        return None
    comp = comps[0]
    status = comp.get("status") or ev.get("status") or {}
    stype = status.get("type") or {}
    competitors = comp.get("competitors") or []
    if len(competitors) != 2:
        return None
    a, b = (_team(c) for c in competitors)
    home, away = (a, b) if a["home"] else (b, a)
    return {
        "id": ev.get("id"),
        "date": ev.get("date"),
        "completed": bool(stype.get("completed")),
        "period": _int(status.get("period"), 4),
        "home": home,
        "away": away,
        "week": _int((ev.get("week") or {}).get("number"), week),
        "season_year": season_year,
        "season_type": season_type,
    }


def fetch_games(path, params, dates):
    """Zwraca listę zakończonych meczów z podanych dni (daty amerykańskie)."""
    games = {}
    for d in dates:
        p = dict(params)
        p["dates"] = d.strftime("%Y%m%d")
        r = requests.get(BASE.format(path=path), params=p, timeout=30,
                         headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        data = r.json()
        week = _int((data.get("week") or {}).get("number"), 0)
        season = data.get("season") or {}
        for ev in data.get("events") or []:
            g = _parse_event(ev, week, _int(season.get("year"), d.year), _int(season.get("type"), 2))
            if g and g["completed"] and g["id"]:
                games[g["id"]] = g
    return list(games.values())
