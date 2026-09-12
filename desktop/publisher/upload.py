from pathlib import Path
import requests

def upload(server: str, token: str, audio: str, title: str, artist: str=""):
    with Path(audio).open("rb") as f:
        r=requests.post(server.rstrip("/")+"/api/tracks",headers={"Authorization":f"Bearer {token}"},files={"audio":f},data={"title":title,"artist":artist},timeout=120)
    r.raise_for_status(); return r.json()
