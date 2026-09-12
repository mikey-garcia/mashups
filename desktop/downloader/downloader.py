from pathlib import Path
import subprocess

def download(url: str, out_dir="downloads") -> Path:
    """Download best available audio. Use only for media you are permitted to download."""
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    tmpl = str(out / "%(title)s.%(ext)s")
    subprocess.run(["yt-dlp", "-x", "--audio-format", "flac", "-o", tmpl, url], check=True)
    files = sorted(out.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files: raise RuntimeError("yt-dlp produced no file")
    return files[0]
