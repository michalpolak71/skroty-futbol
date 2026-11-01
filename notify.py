"""Opcjonalne powiadomienie push przez ntfy.sh (darmowa aplikacja na telefon)."""
import os

import requests


def send(title, message, link=None):
    topic = os.getenv("NTFY_TOPIC")
    if not topic:
        return
    payload = {"topic": topic, "title": title, "message": message}
    if link:
        payload["click"] = link
    try:
        requests.post(os.getenv("NTFY_SERVER", "https://ntfy.sh"), json=payload, timeout=15)
    except requests.RequestException as e:
        print(f"  ! powiadomienie nie wysłane: {e}")
