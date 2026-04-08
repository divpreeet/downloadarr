# downloadarr
an on demand music downloader with a web interface that does tagging and proper metadata

## how it works
 - you enter a song you want to download  
 - downloadarr finds metadata on spotify/deezer  
 - gives you 5 results to pick the correct metadata  
 - formats the metadata title to search on youtube  
 - gives you 5 youtube results  
 - your song is downloaded and stored as `MUSIC_DIR/Artist/Album/Song`

you can choose the output folder — just change `MUSIC_DIR` in `docker-compose.yml`.

eg:
```sh
MUSIC_DIR=/app/music
```

### spotify usage
by default, downloadarr uses spotify first and deezer as a fallback.  
to use spotify, create an app in the spotify developer dashboard (Web API), then:

```sh
cp .env.example .env
nano .env
```

## installation
> downloadarr is now a docker app with a web interface for easier setups on home servers!

### 0. install docker
- **Linux:** https://docs.docker.com/engine/install/  
- **Windows/Mac:** install **Docker Desktop**

### 1. clone the repo
```sh
git clone https://github.com/divpreeet/downloadarr.git
cd downloadarr/
```

### 2. create a `.env` file (optional, only if using spotify)
```sh
cp .env.example .env
nano .env
```
then enter your spotify id + secret.

### 3. configure ports / volumes (optional)
edit `docker-compose.yml` to change the port or mount a custom music folder:
```yaml
ports:
  - "8000:8000"
volumes:
  - /path/to/your/music:/app/music
```
make sure you update `MUSIC_DIR` too.

### 4. run
```sh
sudo docker-compose up -d --build
```

then open:
```sh
http://localhost:8000/
```

### notes
- changing env vars in `.env` only needs a **restart**, not a rebuild.  
- overwrite is not available yet (coming soon).  