"""Small FFmpeg boundary shared by the local audio pipeline."""
from pathlib import Path
import json
import subprocess


def run(args):
    try:
        return subprocess.run([str(a) for a in args], check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError(f"{args[0]} was not found; install it and add it to PATH") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"{args[0]} failed:\n{exc.stderr[-8000:]}") from exc


def ffmpeg(args):
    return run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y", *args])


def probe(path):
    data = json.loads(run([
        "ffprobe", "-v", "error", "-select_streams", "a:0", "-show_streams",
        "-show_format", "-of", "json", str(Path(path).resolve()),
    ]).stdout)
    if not data["streams"]:
        raise ValueError(f"No audio stream: {path}")
    stream = data["streams"][0]
    return {"duration": float(data["format"]["duration"]),
            "sample_rate": int(stream["sample_rate"]), "channels": stream["channels"]}
