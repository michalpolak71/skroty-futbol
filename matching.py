"""Dopasowanie filmów z YouTube do meczów po tytułach."""
import re
import unicodedata

BAD_PHRASES = [
    "every touchdown", "every td", "top plays", "best plays", "press conference",
    "postgame", "post game", "reaction", "breakdown", "analysis", "film room",
    "interview", "mic d up", "shorts", "full game replay", "preview", "prediction",
    "picks", "fantasy", "sound fx", "inside the nfl", "betting",
]


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = s.replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return f" {s.strip()} "


_BAD = [norm(b) for b in BAD_PHRASES]


def team_aliases(team, use_nickname):
    names = {team["display"], team["location"], team["short"]}
    if use_nickname:
        names.add(team["nickname"])
    return [norm(n) for n in names if n and len(n.strip()) >= 3]


def mentions(title_norm, aliases):
    return any(a in title_norm for a in aliases)


def video_quality(video, channel_priority):
    """None = film odrzucony; liczba = jakość kandydata (wyżej lepiej)."""
    t = norm(video["title"])
    if " highlight" not in t:
        return None
    if any(b in t for b in _BAD):
        return None
    if video.get("live"):
        return None
    d = video.get("duration", 0)
    if d and (d < 90 or d > 2400):
        return None
    q = channel_priority
    if " game highlights " in t:
        q += 10
    if " full game highlights " in t:
        q += 5
    q += min(d / 60, 15) * 0.3
    return q


def assign_videos(games, videos, channel_priority, use_nickname):
    """Dla każdego meczu wybiera najlepszy film. Zwraca {game_id: video}."""
    aliases = {g["id"]: (team_aliases(g["home"], use_nickname),
                         team_aliases(g["away"], use_nickname)) for g in games}
    best = {}
    for v in videos:
        prio = channel_priority.get(v["channel_id"], 0)
        q = video_quality(v, prio)
        if q is None:
            continue
        t = norm(v["title"])
        hits = [gid for gid, (ha, aa) in aliases.items() if mentions(t, ha) and mentions(t, aa)]
        if len(hits) != 1:
            continue
        gid = hits[0]
        if gid not in best or q > best[gid][0]:
            best[gid] = (q, v)
    return {gid: v for gid, (q, v) in best.items()}
