"""Minimalny klient YouTube Data API v3 (tylko requests)."""
import os
import re
import time

import requests

API = "https://www.googleapis.com/youtube/v3"
TOKEN_URL = "https://oauth2.googleapis.com/token"


class QuotaError(RuntimeError):
    pass


def _duration(iso):
    m = re.match(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return 0
    d, h, mi, s = (int(x or 0) for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


class YouTube:
    def __init__(self):
        self.api_key = os.getenv("YOUTUBE_API_KEY")
        self.client_id = os.getenv("YOUTUBE_CLIENT_ID")
        self.client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")
        self.refresh_token = os.getenv("YOUTUBE_REFRESH_TOKEN")
        self._token = None
        self.units = 0
        if not (self.refresh_token or self.api_key):
            raise RuntimeError("Brak YOUTUBE_REFRESH_TOKEN (lub YOUTUBE_API_KEY do trybu --dry-run).")

    @property
    def can_write(self):
        return bool(self.refresh_token and self.client_id and self.client_secret)

    def _access_token(self):
        if not self._token:
            r = requests.post(TOKEN_URL, data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token",
            }, timeout=30)
            if r.status_code != 200:
                raise RuntimeError(f"Nie udało się odświeżyć tokenu Google: {r.text}")
            self._token = r.json()["access_token"]
        return self._token

    def _call(self, method, path, params, body=None, cost=1, write=False):
        params = dict(params)
        headers = {}
        if self.can_write:
            headers["Authorization"] = "Bearer " + self._access_token()
        elif write:
            raise RuntimeError("Do tworzenia playlist potrzebne jest połączenie z kontem (refresh token).")
        else:
            params["key"] = self.api_key
        for attempt in range(6):
            r = requests.request(method, API + path, params=params, json=body, headers=headers, timeout=30)
            transient = r.status_code >= 500 or (r.status_code == 409 and
                                                 ("ABORTED" in r.text or "SERVICE_UNAVAILABLE" in r.text))
            if not transient:
                break
            time.sleep(3 * (attempt + 1))
        self.units += cost
        if r.status_code == 403 and "quota" in r.text.lower():
            reason = ""
            try:
                reason = r.json()["error"]["errors"][0].get("reason", "")
            except Exception:
                pass
            print(f"  ! 403 przy {method} {path}: {reason} | {r.text[:300]}")
            if reason in ("quotaExceeded", "dailyLimitExceeded"):
                raise QuotaError("Wyczerpany dzienny limit YouTube API.")
            raise RuntimeError(f"YouTube API {method} {path}: 403 {reason}")
        if r.status_code >= 400:
            raise RuntimeError(f"YouTube API {method} {path}: {r.status_code} {r.text[:300]}")
        return r.json() if r.text else {}

    # ---------- odczyt ----------
    def resolve_channels(self, handles):
        """{channel_id: {"title", "uploads", "priority"}}"""
        out = {}
        for i, h in enumerate(handles):
            data = self._call("GET", "/channels", {"part": "snippet,contentDetails", "forHandle": h})
            items = data.get("items") or []
            if not items:
                print(f"  ! nie znaleziono kanału {h}")
                continue
            it = items[0]
            out[it["id"]] = {
                "title": it["snippet"]["title"],
                "uploads": it["contentDetails"]["relatedPlaylists"]["uploads"],
                "priority": len(handles) - i,
            }
        return out

    def recent_uploads(self, uploads_id, since_iso, channel_id, max_pages=20):
        vids, token = [], None
        for _ in range(max_pages):
            p = {"part": "snippet,contentDetails", "playlistId": uploads_id, "maxResults": 50}
            if token:
                p["pageToken"] = token
            data = self._call("GET", "/playlistItems", p)
            oldest_reached = False
            for it in data.get("items") or []:
                published = it["contentDetails"].get("videoPublishedAt") or it["snippet"].get("publishedAt", "")
                if published < since_iso:
                    oldest_reached = True
                    continue
                vids.append({"id": it["contentDetails"]["videoId"], "title": it["snippet"]["title"],
                             "channel_id": channel_id})
            token = data.get("nextPageToken")
            if oldest_reached or not token:
                break
        return vids

    def enrich(self, videos):
        """Dopisuje czas trwania, wyświetlenia, status transmisji."""
        by_id = {v["id"]: v for v in videos}
        ids = list(by_id)
        for i in range(0, len(ids), 50):
            data = self._call("GET", "/videos", {"part": "contentDetails,statistics,snippet",
                                                 "id": ",".join(ids[i:i + 50])})
            for it in data.get("items") or []:
                v = by_id[it["id"]]
                v["duration"] = _duration(it["contentDetails"].get("duration"))
                v["views"] = int((it.get("statistics") or {}).get("viewCount", 0))
                v["live"] = it["snippet"].get("liveBroadcastContent", "none") != "none"
                rr = it["contentDetails"].get("regionRestriction") or {}
                cc = os.getenv("VIEWER_COUNTRY", "PL")
                v["blocked"] = (cc in rr.get("blocked", [])) or ("allowed" in rr and cc not in rr["allowed"])
        dropped = [v for v in videos if v.get("blocked")]
        for v in dropped:
            print(f"  ~ pomijam (zablokowany w {os.getenv('VIEWER_COUNTRY', 'PL')}): {v['title'][:80]}")
        return [v for v in videos if "duration" in v and not v.get("blocked")]

    def search(self, query, since_iso):
        data = self._call("GET", "/search", {"part": "snippet", "type": "video", "q": query,
                                             "maxResults": 10, "publishedAfter": since_iso,
                                             "order": "relevance"}, cost=100)
        return [{"id": it["id"]["videoId"], "title": it["snippet"]["title"],
                 "channel_id": it["snippet"]["channelId"], "channel_title": it["snippet"]["channelTitle"]}
                for it in data.get("items") or []]

    # ---------- zapis ----------
    def _find_my_playlist(self, title):
        token = None
        while True:
            p = {"part": "snippet", "mine": "true", "maxResults": 50}
            if token:
                p["pageToken"] = token
            data = self._call("GET", "/playlists", p)
            for it in data.get("items") or []:
                if it["snippet"]["title"] == title:
                    return it["id"]
            token = data.get("nextPageToken")
            if not token:
                return None

    def _playlist_items(self, pid):
        items, token = [], None
        while True:
            p = {"part": "snippet", "playlistId": pid, "maxResults": 50}
            if token:
                p["pageToken"] = token
            data = self._call("GET", "/playlistItems", p)
            items += [(it["id"], it["snippet"]["resourceId"]["videoId"]) for it in data.get("items") or []]
            token = data.get("nextPageToken")
            if not token:
                return items

    def sync_playlist(self, title, description, privacy, video_ids):
        """Tworzy lub aktualizuje playlistę o danym tytule, tak by zawierała dokładnie video_ids."""
        body = {"snippet": {"title": title[:150], "description": description[:4900]},
                "status": {"privacyStatus": privacy}}
        pid = self._find_my_playlist(title[:150])
        if pid:
            body["id"] = pid
            self._call("PUT", "/playlists", {"part": "snippet,status"}, body, cost=50, write=True)
            existing = self._playlist_items(pid)
        else:
            pid = self._call("POST", "/playlists", {"part": "snippet,status"}, body, cost=50, write=True)["id"]
            existing = []
            time.sleep(5)  # świeża playlista potrzebuje chwili, zanim przyjmie filmy
        if [v for _, v in existing] == video_ids:
            return pid
        for item_id, _ in existing:
            self._call("DELETE", "/playlistItems", {"id": item_id}, cost=50, write=True)
        for vid in video_ids:
            time.sleep(0.5)
            try:
                self._call("POST", "/playlistItems", {"part": "snippet"},
                           {"snippet": {"playlistId": pid,
                                        "resourceId": {"kind": "youtube#video", "videoId": vid}}},
                           cost=50, write=True)
            except QuotaError:
                raise
            except RuntimeError as e:
                print(f"  ! nie dodano {vid}: {e}")
        return pid
