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
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "noplaylist": True,
        "ignoreerrors": True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            result = ydl.extract_info(f"ytsearch10:{query}", download=False)

        entries = [e for e in (result.get("entries") or []) if e]
        if not entries:
            return []

        results = []
        print("youtube results:")
        for i, e in enumerate(entries[:5]):
            vid = e.get("webpage_url") or e.get("url")
            if vid and not str(vid).startswith("http"):
                vid = f"https://www.youtube.com/watch?v={vid}"

            dur = e.get("duration")
            if isinstance(dur, (int, float)):
                dur = int(dur)
            else:
                dur = 0
            
            title = e.get("title", "Unknown")
            results.append({"title": title, "url": vid})
            print(f"  {i + 1}. {title} ({dur // 60}:{dur % 60:02d})")

        return results
    except Exception as e:
        print("youtube search error:", e)
        return []

def download_audio(url, output_path):
    print("downloading...")
    try:
        with yt_dlp.YoutubeDL({
            "format": "bestaudio/best",
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", 'preferredquality':320}],
            "outtmpl": output_path,
            "quiet": True,
            "no_warnings": True,
        }) as ydl:
            ydl.download([url])
        mp3 = output_path + ".mp3"
        if os.path.exists(mp3):
            return mp3
        else:
            None
    except Exception as e:
        print(e)
        return None
    
def tagging(filepath, metadata, album_art):
    audio = MP3(filepath, ID3=ID3)
    try:
        audio.add_tags()
    except Exception:
        pass

    tags = audio.tags
    tag_map = {
        "title": TIT2, "artist": TPE1, "album": TALB,
        "date": TDRC, "track_number": TRCK, "genre": TCON
    }
    for key, tag_cls in tag_map.items():
        val = metadata.get(key)
        if val:
            tags.add(tag_cls(encoding=3, text=str(val)))

    if album_art:
        tags.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=album_art))

    audio.save()

def organize(filepath, metadata):
    artist = sanitize(metadata.get("artist", "Unknown Artist"))
    album = sanitize(metadata.get("album", "Unknown Album"))
    title = sanitize(metadata.get("title", "track"))
    num = metadata.get("track_number", "")
    # i have no idea why this works
    filename = f"{num.zfill(2)} - {title}.mp3" if num else f"{title}.mp3"
    dir = os.path.join(OUTPUT_DIR, artist, album)
    os.makedirs(dir, exist_ok=True)
    dest = os.path.join(dir, filename)

    if os.path.exists(dest):
        print(f"already exists: {dest}")
        overwrite = input("overwrite? (y/n): ")
        if overwrite != "y":
            os.remove(filepath)
            print("skipped")
            return dest
    
    os.rename(filepath, dest)
    print(f"saved: {dest}")
    return dest

def download(query):
    print(f"\n{'=' * 40}")
    print(f"processing: {query}")
    print(f"{'=' * 40}")

    metadata_song, album_art = metadata(query)
    if metadata_song:
        meta = metadata_song
    else:
        meta = {
            "title": query,
            "artist": "Unknown Artist",
            "album": "Unknown Album",
            "date": "",
            "track_number": "",
            "genre": ""
        }

    yt_query = f"{meta['artist']} - {meta['title']}" if meta["artist"] != "Unknown Artist" else query
    results = search_youtube(yt_query)
    if not results:
        print("no results found")
        return

    while True:
        try:
            c = int(input(f"pick video (1-{len(results)}): ").strip())
            if 1 <= c <= len(results):
                break
        except ValueError:
            pass

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    mp3 = download_audio(results[c - 1]["url"], os.path.join(OUTPUT_DIR, "temp_download"))
    if not mp3:
        print("download failed")
        return

    tagging(mp3, meta, album_art)
    organize(mp3, meta)
    print("done")

def main():
    if len(sys.argv) > 1:
        download(" ".join(sys.argv[1:]))
    else:
        print("downloadarr")
        print("type a song name or 'quit' to exit")
        while True:
            query = input("song: ").strip()
            if query.lower() in ("quit"):
                break
            if query:
                download(query)

# def test(query="fein"):
#     metadatar = search_deezer(query)
#     if not metadatar:
#         print("no deezer metadata for the qwuery")
        
#     meta = metadatar[0]
#     print("metadata:", meta['artist'], meta["title"], meta["album"])

#     yt_results = search_youtube(f"{meta['artist']} {meta['title']} audio")
#     if not yt_results:
#         print("no youtube results")
#         return
    
#     yt = yt_results[0]
#     print("yt:", yt["title"])
#     print("url", yt["url"])

#     os.makedirs(OUTPUT_DIR, exist_ok=True)
#     out_base = os.path.join(OUTPUT_DIR, sanitize(f"{meta['artist']}, {meta['title']}"))    
#     mp3_path = download_audio(yt["url"], out_base)
#     if not mp3_path:
#         print("download failed; skipping tagging")
#         return
#     tagging(mp3_path, meta, fetch_art(meta.get("album_art_url")))

#     audio = MP3(mp3_path, ID3=ID3)

if __name__ == "__main__":
    main()