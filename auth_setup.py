"""JEDNORAZOWO, na Twoim komputerze: łączy bota z Twoim kanałem YouTube.

W wierszu poleceń (Win+R -> cmd):
    pip install google-auth-oauthlib
    curl -O https://raw.githubusercontent.com/michalpolak71/skroty-futbol/main/auth_setup.py
    python auth_setup.py

Skrypt sam znajdzie plik client_secret_*.json (w bieżącym folderze albo w Pobranych).
W przeglądarce zaloguj się i wybierz SWÓJ KANAŁ. Ostrzeżenie „aplikacja niezweryfikowana”
jest normalne: Zaawansowane -> Przejdź do Skroty Futbol Bot.
Na końcu skopiuj wypisane 3 linijki do Railway -> Variables.
"""
import glob
import os
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube"]

candidates = []
for folder in (".", os.path.join(os.path.expanduser("~"), "Downloads"),
               os.path.join(os.path.expanduser("~"), "Pobrane")):
    candidates += glob.glob(os.path.join(folder, "client_secret*.json"))
if not candidates:
    sys.exit("Nie znaleziono pliku client_secret*.json – pobierz go z Google Cloud (Klienty -> Pobierz JSON).")
secret = max(candidates, key=os.path.getmtime)
print(f"Używam pliku: {secret}")

flow = InstalledAppFlow.from_client_secrets_file(secret, SCOPES)
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

print("\nWklej do Railway -> Variables (każda linijka osobno):\n")
print(f"YOUTUBE_CLIENT_ID={creds.client_id}")
print(f"YOUTUBE_CLIENT_SECRET={creds.client_secret}")
print(f"YOUTUBE_REFRESH_TOKEN={creds.refresh_token}")
input("\nNaciśnij Enter, aby zamknąć...")
