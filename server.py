from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn
import os
from main import (
    search_deezer, search_spotify, search_youtube, get_spotify_token, download_audio, tagging, organize, fetch_art, OUTPUT_DIR
)
from fastapi.staticfiles import StaticFiles


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
            raise HTTPException(status_code="404", detail="no metadata found :(")
        
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search/youtube")
def youtube_search(req: SearchRequest):
    try:
        results = search_youtube(req.query)
        if not results:
            raise HTTPException(status_code=404, detail="no youtube results :(")
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _download_task(url: str, metadata:dict):
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        temp = os.path.join(OUTPUT_DIR, "temp_download")

        mp3 = download_audio(url, temp)
        if not mp3:
            print(f"downloaded failed for {metadata.get('title')}")
            return

        album_art = fetch_art(metadata.get("album_art_url"))
        tagging(mp3, metadata, album_art)
        path = organize(mp3, metadata)
        print(f"downloaded to {path}")
    except Exception as e:
        print(e)

@app.post("/download")
def download(req: DownloadRequest, background_tasks: BackgroundTasks):
    try:
        if not req.url or not req.metadata:
            raise HTTPException(status_code=400, detail="url and metadata req")

        background_tasks.add_task(
            _download_task,
            req.url,
            req.metadata
        )

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
        raise HTTPException(status_code = 500, detail=str(e))


if os.path.exists("web"):
    app.mount("/", StaticFiles(directory="web", html=True), name="web")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
