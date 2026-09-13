from pathlib import Path
import hashlib
import json
import sys
import tempfile
from urllib.parse import urlparse

from desktop.audio import ffmpeg, probe, run
from shared.models import Song


def import_file(path, out_dir="projects/sources") -> Song:
    """Copy decoded audio into a content-addressed, 48 kHz stereo FLAC source."""
    source = Path(path).resolve(strict=True)
    with source.open("rb") as f:
        digest = hashlib.file_digest(f, "sha256").hexdigest()
    out = Path(out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"{digest}.flac"
    if not target.exists():
        with tempfile.TemporaryDirectory(dir=out) as td:
            staged = Path(td) / "source.flac"
            ffmpeg(["-i", source, "-map", "0:a:0", "-vn", "-map_metadata", "-1",
                    "-ar", "48000", "-ac", "2", "-c:a", "flac", staged])
            probe(staged)
            staged.replace(target)
    return Song(path=str(target), title=source.stem, duration=probe(target)["duration"])


def download(url: str, out_dir="projects/sources") -> Song:
    """Import exactly the file reported by yt-dlp after postprocessing."""
    if urlparse(url).scheme not in {"http", "https"}:
        raise ValueError("Download URL must use HTTP or HTTPS")
    with tempfile.TemporaryDirectory() as td:
        result = run([
            sys.executable, "-m", "yt_dlp", "--ignore-config", "--no-playlist",
            "-x", "--audio-format", "flac", "--print", "after_move:%(filepath)j",
            "-o", str(Path(td) / "%(title).100B [%(id)s].%(ext)s"), "--", url,
        ])
        paths = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        if len(paths) != 1:
            raise RuntimeError(f"Expected one downloaded audio file, got {len(paths)}")
        return import_file(paths[0], out_dir)


def import_source(source, out_dir="projects/sources") -> Song:
    if urlparse(str(source)).scheme in {"http", "https"}:
        return download(str(source), out_dir)
    return import_file(source, out_dir)
