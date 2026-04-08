from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
import uvicorn
import os
import threading
import time
from datetime import datetime
from main import (
    search_deezer, search_spotify, search_youtube, get_spotify_token, download_audio, tagging, organize, fetch_art, OUTPUT_DIR
)
from mutagen.id3 import ID3, APIC

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

class SearchRequest(BaseModel):
    query: str

class DownloadRequest(BaseModel):
    url: str
    metadata: dict

active_downloads = {}

@app.post("/search/metadata")
def metadata_search(req: SearchRequest):
    try:
        results = []
        token = get_spotify_token()
        if token:
            results = search_spotify(req.query, token)
        if not results:
            results = search_deezer(req.query)
        if not results:
            raise HTTPException(status_code=404, detail="no metadata found")
        
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search/youtube")
def youtube_search(req: SearchRequest):
    try:
        results = search_youtube(req.query)
        if not results:
            raise HTTPException(status_code=404, detail="no youtube results")
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def _download_task(url: str, metadata: dict):
    download_id = f"{metadata.get('artist')}_{metadata.get('title')}_{datetime.now().timestamp()}"
    
    active_downloads[download_id] = {
        "id": download_id,
        "title": metadata.get("title"),
        "artist": metadata.get("artist"),
        "status": "downloading",
        "progress": 0
    }
    
    print(f"[download] Starting: {download_id}")
    
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        temp = os.path.join(OUTPUT_DIR, f"temp_download_{download_id}")

        print(f"[download] Downloading audio from {url}")
        mp3 = download_audio(url, temp)
        
        if not mp3:
            active_downloads[download_id]["status"] = "failed"
            print(f"[download] Failed to download MP3 for {metadata.get('title')}")
            return

        print(f"[download] Downloaded to {mp3}")
        active_downloads[download_id]["status"] = "tagging"
        
        album_art = fetch_art(metadata.get("albumArtURL"))
        tagging(mp3, metadata, album_art)

        active_downloads[download_id]["status"] = "organizing"
        path = organize(mp3, metadata)

        active_downloads[download_id]["status"] = "completed"
        print(f"[download] Completed: {path}")

    except Exception as e:
        active_downloads[download_id]["status"] = "error"
        print(f"[download] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        def remove_later():
            time.sleep(300)
            active_downloads.pop(download_id, None)
        
        threading.Thread(target=remove_later, daemon=True).start()

@app.post("/download")
def download(req: DownloadRequest, background_tasks: BackgroundTasks):
    try:
        if not req.url or not req.metadata:
            raise HTTPException(status_code=400, detail="url and metadata required")

        background_tasks.add_task(_download_task, req.url, req.metadata)
        return {"status": "downloading", "message": "download started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/library")
def library():
    try:
        library = []
        
        if not os.path.exists(OUTPUT_DIR):
            return {"songs": []}
        
        for artist in os.listdir(OUTPUT_DIR):
            artist_path = os.path.join(OUTPUT_DIR, artist)
            if not os.path.isdir(artist_path) or artist == "temp_download":
                continue

            for album in os.listdir(artist_path):
                album_path = os.path.join(artist_path, album)
                if not os.path.isdir(album_path):
                    continue

                for filename in os.listdir(album_path):
                    if filename.endswith(".mp3") or filename.endswith(".flac"):
                        library.append({
                            "artist": artist,
                            "album": album,
                            "filename": filename,
                            "url": f"/file/{artist}/{album}/{filename}"
                        })
        return {"songs": library}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/file/art/{artist}/{album}/{filename}")
def get_art(artist: str, album: str, filename: str):
    try:
        filepath = os.path.join(OUTPUT_DIR, artist, album, filename)
        print(f"[get_art] Looking for: {filepath}")
        
        if not os.path.exists(filepath):
            print(f"[get_art] File not found: {filepath}")
            raise HTTPException(status_code=404, detail="file not found")
        
        try:
            audio = ID3(filepath)
            print(f"[get_art] ID3 tags found, searching for APIC...")
            for tag in audio.values():
                if isinstance(tag, APIC):
                    print(f"[get_art] Found APIC, returning image")
                    return Response(content=tag.data, media_type=tag.mime)
            print(f"[get_art] No APIC tag found")
        except Exception as e:
            print(f"[get_art] Error reading ID3: {e}")
        
        raise HTTPException(status_code=404, detail="no artwork")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[get_art] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/downloads")
def get_downloads():
    try:
        return {"downloads": list(active_downloads.values())}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if os.path.exists("web"):
    app.mount("/", StaticFiles(directory="web", html=True), name="web")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)