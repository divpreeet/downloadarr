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

def search_deezer(query):
    try:
        resp = requests.get("https://api.deezer.com/search", params={"q": query, "limit": 5}, timeout=10)
        if resp.status_code != 200:
            return []
        return [
            {
                "title": t.get("title", "Unknown"),
                "artist": t.get("artist", {}).get("name", "Unknown Artist"),
                "album": t.get("album", {}).get("title", "Unknown Ablum"),
                "album_art_url": t.get("album", {}).get("cover_big"),
                "track_number": str(t.get("track_pos", "")),
                "date": "",
                "genre": "",
                "source": "deezer",
            }
            for t in resp.json().get("data", [])
        ]
    except Exception as e:
        print(e)
        return []

def fetch_art(url):
    if not url:
        return None
    try:
        resp = requests.get(url, timeout=10)
        return resp.content if resp.status_code == 200 else None
    except Exception:
        return None

def metadata(query):
    results = []
    token = get_spotify_token()
    if token:
        results = search_spotify(query, token)

    if not results:
        print("no resuslts with spotify, trying deezer")
        results = search_deezer(query)
    
    if not results:
        print("no metadata found on any service")
    
    source = results[0].get("source", "unknown")
    print(f"resulsts from {source}:")
    for i, r in enumerate(results):
        print(f"  {i + 1}. {r['artist']} - {r['title']} ({r['album']}) [{r['date']}]")
        print("0 to skip")

    while True:
        try:
            c = int(input(f"pick metadata - (0-{len(results)}): ").strip())
            if c == 0:
                return None, None
            if 1 <= c <= len(results):
                break
        except ValueError:
            pass

    sel = results[c-1]
    print(f"{sel['artist']} - {sel['title']} ({sel['album']})")
    
    return sel, fetch_art(sel.get("album_art_url"))

def search_youtube(query):
    print(f"searching yt for {query}")
    try:
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "extract_flat": False, "noplaylist": True}) as ydl:
            result = ydl.extract_info(f"ytsearch5:{query}", download=False)
        entries = result.get("entries", [])
        if not entries:
            return []
        results = []
        print("youtube results: ")
        for i, e in enumerate(entries):
            dur = e.get("duration", 0)
            results.append({"title": e.get("title", "Unkown"), "url": e.get("webpage_url", "")})
            print(f"  {i + 1}. {e.get('title', 'Unknown')} ({dur // 60}:{dur % 60:02d})")
        return results
    except Exception as e:
        print(e)
        return []
    
def download_audio(url, output_path):
    print("downloadinggggg")
    try:
        with yt_dlp.YoutubeDL({
            "format": "bestaudio/best",
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "320"}],
            "outtmpl": output_path,
            "quiet": True,
            "no_warnings": True,
        }) as ydl:
            ydl.download([url])
        mp3 = output_path + ".mp3"
        return mp3 if os.path.exists(mp3) else None
    except Exception as e:
        print(e)
        return []

def tagging(filepath, metadata, album_art):
    try:
        audio = MP3(filepath, ID3=ID3)
    except Exception:
        audio = MP3(filepath)
    try:
        audio.add_tags()
    except Exception:
        pass

    tags = audio.tags
    tag_map = {
        "title": TIT2, "artist": TPE1, "album": TALB,
        "date": TDRC, "track_number": TRCK, "genre":TCON
    }
    for key, tag_cls, in tag_map.items():
        if metadata.get(key):
            tags.add(tag_cls(encoding=3, text=metadata[key]))

    if album_art:
        tags.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=album_art))
        audio.save()
    
    
    
if __name__ == "__main__":
    token = get_spotify_token()
    print("token ok", bool(token))

    if not token:
        sys.exit(1)
    
    results = search_spotify("jingle bells", token)
    print(len(results))
    for i in results:
        print(i)