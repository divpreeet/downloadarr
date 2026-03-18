# downloadarr
an on demand music downloader with tagging and proper metadata

## how it works
 - you enter a song you want to download
 - downloadarr finds the metadata for your song on spotify/deezer
 - gives you 5 results to pick the correct metadata
 - then, formats the metadata title to search for your song on youtube
 - gives you 5 more results from youtube
 - your song is downloaded and stored as ```OUTPUT_DIR/Artist/Album/Song```

you can choose the ```OUTPUT_DIR```, just export it as a variable with the name ```MUSIC_DIR```, prefferalby in your ```.zshrc``` or ```.bashrc```

eg. 
```sh
export MUSIC_DIR="/Users/divpreet/Music/"
```
### spotify usage
by default, downloadarr goes to use spotify, and deezer as a fallback, to use spotify, you need to provide a client id and secret, for these, you would need to setup a app on the spotify devloper dashboard with webapi capabilitites.

then, just simply export the ID's as variables - 
```sh
export SPOTIFY_CLIENT_ID="client id"
export SPOTIFY_CLIENT_SECRET="client secret"
```

to keep these persistent, just store the variables in your ```.zshrc``` or ```.bashrc```

## installation
1. clone the repo
```sh
git clone https://github.com/divpreeet/downloadarr.git
cd downloadarr/
```
2. create a virtual environment
```sh
python3 -m venv .venv
source .venv/bin/activate
```
3. install the requirements
```sh
pip install -r requirements.txt
```
4. download ffmpeg
```sh
# windows
winget install --id Gyan.FFmpeg -e

# macos
brew install ffmpeg

# debian
sudo apt-get install -y ffmpeg
```
5. run the script and download your favorite songs!
```sh
python3 main.py
```
### notes
 - make sure ffmpeg is installed on your system
 - the app provides an overwrite prompt
 - you can totally skip the metadata part, just click 0 on the prompt for choosing a result.