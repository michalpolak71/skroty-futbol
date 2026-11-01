"""JEDNORAZOWO, na Twoim komputerze: łączy bota z Twoim kanałem YouTube.

1. pip install google-auth-oauthlib
2. Połóż obok plik client_secret.json (pobrany z Google Cloud Console)
3. python auth_setup.py
4. W przeglądarce zaloguj się i wybierz SWÓJ KANAŁ (jeśli masz kilka – ten, na którym mają być playlisty)
5. Skopiuj wypisane 3 wartości do zmiennych na Railway
"""
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube"]

flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

print("\nWklej do Railway → Variables:\n")
print(f"YOUTUBE_CLIENT_ID={creds.client_id}")
print(f"YOUTUBE_CLIENT_SECRET={creds.client_secret}")
print(f"YOUTUBE_REFRESH_TOKEN={creds.refresh_token}")
