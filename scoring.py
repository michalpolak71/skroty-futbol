"""Wskaźnik emocji meczu: im wyżej, tym ciekawszy skrót."""
import math


def _pre_game_pct(record, won):
    """Procent zwycięstw PRZED tym meczem (ESPN podaje bilans już po meczu)."""
    if not record:
        return None
    try:
        parts = [int(x) for x in record.split("-")]
    except ValueError:
        return None
    w, l = parts[0], parts[1]
    t = parts[2] if len(parts) > 2 else 0
    if won:
        w -= 1
    else:
        l -= 1
    n = w + l + t
    if n <= 0:
        return None
    return (w + 0.5 * t) / n


def _flow(w_lines, l_lines):
    """Przebieg meczu z wyników kwart: największa odrobiona strata, zmiany prowadzenia, comeback w 4Q."""
    n = min(len(w_lines), len(l_lines))
    cw = cl = 0
    diffs = []
    for i in range(n):
        cw += w_lines[i]
        cl += l_lines[i]
        diffs.append(cw - cl)
    max_deficit = max([-d for d in diffs[:-1]] + [0]) if n > 1 else 0
    signs = [1 if d > 0 else -1 for d in diffs if d != 0]
    lead_changes = sum(1 for i in range(1, len(signs)) if signs[i] != signs[i - 1])
    trailed_after_q3 = n >= 4 and diffs[2] < 0
    return max_deficit, lead_changes, trailed_after_q3


def excitement(game, league):
    h, a = game["home"], game["away"]
    margin = abs(h["score"] - a["score"])
    total = h["score"] + a["score"]
    winner, loser = (h, a) if h["score"] >= a["score"] else (a, h)
    s = 0.0
    why = []

    # 1. Wyrównany wynik
    s += max(0, 24 - margin) * 1.6
    if margin <= 3:
        why.append("rozstrzygnięty minimalnie")

    # 2. Dogrywka
    ot = max(0, game["period"] - 4)
    if ot:
        s += 18 + 8 * (ot - 1)
        why.append("dogrywka" if ot == 1 else f"{ot} dogrywki")

    # 3. Przebieg: odrabianie strat, zmiany prowadzenia
    deficit, changes, late = _flow(winner["lines"], loser["lines"])
    s += 1.4 * deficit + 4 * changes
    if deficit >= 10:
        why.append(f"odrobione {deficit} pkt straty")
    if late:
        s += 10
        why.append("comeback w 4. kwarcie")

    # 4. Niespodzianka i klasa drużyn
    if league == "ncaa":
        lr, wr = loser["rank"], winner["rank"]
        if lr and (not wr or wr > lr):
            s += 12 + (26 - lr) * 0.8
            why.append(f"niespodzianka (przegrał #{lr})")
        for r in (lr, wr):
            if r:
                s += (26 - r) * 0.25
    else:
        pw = _pre_game_pct(winner["record"], True)
        pl = _pre_game_pct(loser["record"], False)
        if pw is not None and pl is not None:
            if pl - pw > 0.2:
                s += 30 * (pl - pw)
                why.append("niespodzianka")
            s += 8 * (pw + pl) / 2

    # 5. Strzelanina / pogrom
    if total > 55:
        s += (total - 55) * 0.4
        why.append("dużo punktów")
    if margin > 28:
        s -= (margin - 28) * 0.5

    return round(s, 1), why


def with_views(score, views):
    """Lekki bonus za popularność skrótu."""
    return round(score + 1.5 * math.log10((views or 0) + 1), 1)



def _favorite(game, league):
    """Zwraca (faworyt, rywal, siła_faworyta, duża_różnica) albo None, gdy nie ma faworyta."""
    h, a = game["home"], game["away"]
    if league == "ncaa":
        hr, ar = h["rank"] or 99, a["rank"] or 99
        if hr == ar:  # obie poza rankingiem
            return None
        fav, dog = (h, a) if hr < ar else (a, h)
        fr, dr = min(hr, ar), max(hr, ar)
        return fav, dog, fr, (dr == 99 or dr - fr >= 10)
    h_won = h["score"] >= a["score"]
    hp = _pre_game_pct(h["record"], h_won)
    ap = _pre_game_pct(a["record"], not h_won)
    if hp is None or ap is None or abs(hp - ap) < 0.05:
        return None
    fav, dog = (h, a) if hp > ap else (a, h)
    return fav, dog, -max(hp, ap), abs(hp - ap) >= 0.3


def order_key(game, league):
    """1) faworyt przegrał z dużo słabszym, 2) faworyt przegrał, 3) faworyt wygrał,
    4) mecze bez faworyta. W grupie: od najmocniejszego faworyta, potem emocje."""
    f = _favorite(game, league)
    if not f:
        return (4, 0, -game.get("final", 0))
    fav, dog, strength, big_gap = f
    fav_lost = fav["score"] < dog["score"]
    tier = (1 if big_gap else 2) if fav_lost else 3
    return (tier, strength, -game.get("final", 0))
