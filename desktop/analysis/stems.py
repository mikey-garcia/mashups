from pathlib import Path
import sys
import tempfile
from desktop.audio import ffmpeg, probe, run


def separate(path: str, out_dir="stems", two_stem=True, model="htdemucs", device="cpu") -> dict[str, str]:
    """Run Demucs in an isolated directory; always expose vocals + instrumental."""
    source = Path(path).resolve(strict=True)
    out = Path(out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    # Keep successful results, but never discover stale output from another run/model.
    root = Path(tempfile.mkdtemp(prefix="separation-", dir=out))
    cmd = [sys.executable, "-m", "demucs", "-n", model, "-d", device,
           "--float32", "--clip-mode", "clamp", "--shifts", "0", "-o", str(root)]
    if two_stem:
        cmd += ["--two-stems", "vocals"]
    run([*cmd, str(source)])
    folder = root / model / source.stem
    result = {p.stem: str(p) for p in folder.glob("*.wav")}
    required = {"vocals", "no_vocals"} if two_stem else {"vocals", "drums", "bass", "other"}
    missing = required - result.keys()
    if missing:
        raise RuntimeError(f"Demucs did not produce {sorted(missing)} in {folder}")
    if two_stem:
        result["instrumental"] = result.pop("no_vocals")
    else:
        instrumental = folder / "instrumental.wav"
        inputs = []
        for stem in ("drums", "bass", "other"):
            inputs += ["-i", result[stem]]
        ffmpeg([*inputs, "-filter_complex", "amix=inputs=3:normalize=0:duration=longest",
                "-c:a", "pcm_f32le", instrumental])
        result["instrumental"] = str(instrumental)
    for output in result.values():
        probe(output)
    return result
