from pathlib import Path
import subprocess, tempfile
from shared.models import Project, Clip

def _render_clip(c: Clip, dst: Path):
    filters=[]
    if c.offset: filters.append(f"atrim=start={c.offset}")
    if c.duration is not None: filters.append(f"atrim=duration={c.duration}")
    if c.gain_db: filters.append(f"volume={c.gain_db}dB")
    # atempo supports .5-2 per stage; V0 rejects more extreme values.
    if not 0.5 <= c.stretch <= 2.0: raise ValueError("V0 stretch must be 0.5..2.0")
    if c.stretch != 1.0: filters.append(f"atempo={1.0/c.stretch}")
    delay=int(c.start*1000); filters.append(f"adelay={delay}:all=1")
    cmd=["ffmpeg","-y","-i",c.source]
    if filters: cmd += ["-af", ",".join(filters)]
    cmd += ["-ar","48000","-ac","2",str(dst)]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def render(project: Project, output: str) -> Path:
    if not project.clips: raise ValueError("timeline is empty")
    out=Path(output); out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        clips=[]
        for i,c in enumerate(project.clips):
            p=Path(td)/f"{i}.wav"; _render_clip(c,p); clips.append(p)
        cmd=["ffmpeg","-y"]
        for p in clips: cmd += ["-i",str(p)]
        cmd += ["-filter_complex",f"amix=inputs={len(clips)}:duration=longest:normalize=0",str(out)]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out
