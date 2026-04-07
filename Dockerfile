FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py server.py ./
COPY web/ ./web/

RUN mkdir -p /app/music

EXPOSE 8000

ENV MUSIC_DIR=/app/music
ENV PYTHONUNBUFFERED=1

CMD ["python", "server.py"]