import os
import sys
import re
import base64
import yt_dlp
import requests
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TRCK, TCON, APIC

OUTPUT_DIR = os.environ.get("MUSIC_DIR", "./music")
SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET", "")

def sanitize(name):
    return re.sub(r'[<>:"/\\|?*]', '', name).strip()

def get_spotify_token():
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        print("spotify credentlas not set")
        return None
    try:
        auth = base64.b64encode(f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()).decode()
        resp = requests.post(
            "https://accounts.spotify.com/api/token",
            headers={"Authorization": f"Basic {auth}"},
            data={"grant_type": "client_credentials"},
            timeout=10,
        )
        if resp.status_code != 200:
            print(resp.text)
            return None 
        token = resp.json().get("access_token")
        if not token:
            print(resp.text)
        return token
    except Exception as e:
        print(e)
        return None

def search_spotify(query, token):
    try:
        resp = requests.get(
            "https://api.spotify.com/v1/search",
            headers={"Authorization": f"Bearer {token}"},
            params={"q": query, "type": "track", "limit": 5},
            timeout=10,
        )
        if resp.status_code != 200:
            print(f"[spotify] search failed ({resp.status_code}): {resp.text}")
            return []
        return [
            {
                "title": t.get("name", "Unknown"),
                "artist": ", ".join(a["name"] for a in t.get("artists", [])),
                "album": t.get("album", {}).get("name", "Unknown Album"),
                "album_art_url": t["album"]["images"][0]["url"] if t.get("album", {}).get("images") else None,
                "date": t.get("album", {}).get("release_date", "")[:4],
                "track_number": str(t.get("track_number", "")),
                "genre": "",
                "source": "spotify",
            }
            for t in resp.json().get("tracks", {}).get("items", [])
        ]
    except Exception as e:
        print(f"[spotify] search error: {e}")
        return []


if __name__ == "__main__":
    token = get_spotify_token()
    print("token ok", bool(token))

    if not token:
        sys.exit(1)
    
    results = search_spotify("jingle bells", token)
    print(len(results))
    for i in results:
        print(i)