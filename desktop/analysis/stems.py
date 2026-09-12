from pathlib import Path
import subprocess

def separate(path: str, out_dir="stems", two_stem=False) -> dict[str, str]:
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    cmd = ["python", "-m", "demucs", "-o", str(out)]
    if two_stem: cmd += ["--two-stems", "vocals"]
    cmd += [path]
    subprocess.run(cmd, check=True)
    song = Path(path).stem
    roots = list(out.glob(f"*/{song}"))
    if not roots: raise RuntimeError("Demucs output not found")
    root = roots[0]
    result = {p.stem: str(p) for p in root.glob("*.wav")}
    if "vocals" in result and not two_stem:
        # Demucs 'other' is not a full instrumental; render.py can mix non-vocal stems.
        pass
    return result
