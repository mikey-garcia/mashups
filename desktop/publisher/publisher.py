from pathlib import Path
import shutil
from mutagen.id3 import ID3, TIT2, TPE1, TALB, APIC
from mutagen.mp3 import MP3
from desktop.editor.render import render

def publish(project, title, artist, album="Mashups", artwork=None, library="library"):
    lib=Path(library); lib.mkdir(parents=True, exist_ok=True)
    safe="".join(c for c in title if c.isalnum() or c in " -_()").strip()
    wav=lib/(safe+".wav"); mp3=lib/(safe+".mp3")
    render(project, str(wav))
    import subprocess
    subprocess.run(["ffmpeg","-y","-i",str(wav),"-codec:a","libmp3lame","-q:a","2",str(mp3)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    wav.unlink(missing_ok=True)
    audio=MP3(mp3, ID3=ID3)
    try: audio.add_tags()
    except Exception: pass
    audio.tags.add(TIT2(encoding=3,text=title)); audio.tags.add(TPE1(encoding=3,text=artist)); audio.tags.add(TALB(encoding=3,text=album))
    if artwork:
        data=Path(artwork).read_bytes(); mime="image/png" if str(artwork).lower().endswith(".png") else "image/jpeg"
        audio.tags.add(APIC(encoding=3,mime=mime,type=3,desc="Cover",data=data))
    audio.save()
    return mp3
