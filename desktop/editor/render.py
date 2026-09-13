from pathlib import Path
import tempfile
from desktop.audio import ffmpeg, probe, run
from shared.models import Project, Clip


def _render_clip(c: Clip, dst: Path, engine="rubberband"):
    c.validate()
    info = probe(c.source)
    remaining = info["duration"] - c.offset
    if remaining <= 0 or (c.duration is not None and c.duration > remaining + 1 / 48000):
        raise ValueError("Clip trim is outside the source audio")
    duration = remaining if c.duration is None else c.duration
    filters = [f"atrim=start={c.offset}:duration={duration}", "asetpts=PTS-STARTPTS",
               "aresample=48000", "aformat=channel_layouts=stereo"]
    if c.stretch != 1 or c.pitch:
        if engine == "rubberband":
            filters.append(f"rubberband=tempo={1 / c.stretch}:pitch={2 ** (c.pitch / 12)}:pitchq=quality")
        elif c.pitch:
            raise ValueError("Pitch shifting requires the rubberband engine")
        else:
            filters.append(f"atempo={1 / c.stretch}")
    samples = round(duration * c.stretch * 48000)
    filters += [f"apad=whole_len={samples}", f"atrim=end_sample={samples}",
                "asetpts=PTS-STARTPTS", f"volume={c.gain_db}dB",
                f"adelay={round(c.start * 48000)}S:all=1"]
    ffmpeg(["-i", Path(c.source).resolve(), "-map", "0:a:0", "-af", ",".join(filters),
            "-ar", "48000", "-ac", "2", "-c:a", "pcm_f32le", dst])


def render(project: Project, output: str, engine="rubberband") -> Path:
    if not project.clips:
        raise ValueError("timeline is empty")
    if engine not in {"rubberband", "atempo"}:
        raise ValueError("Unknown rendering engine")
    out = Path(output).resolve()
    if out.suffix.lower() != ".wav":
        raise ValueError("render produces WAV; use publish for MP3")
    if out in [Path(c.source).resolve() for c in project.clips]:
        raise ValueError("Output must not overwrite a source")
    if engine == "rubberband" and any(c.pitch or c.stretch != 1 for c in project.clips):
        if " rubberband " not in run(["ffmpeg", "-hide_banner", "-filters"]).stdout:
            raise RuntimeError("FFmpeg needs librubberband for pitch/stretch; use --engine atempo for tempo only")
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out.parent) as td:
        inputs = []
        for i, clip in enumerate(project.clips):
            p = Path(td) / f"{i}.wav"
            _render_clip(clip, p, engine)
            inputs += ["-i", p]
        staged = Path(td) / "mix.wav"
        # Float intermediates preserve peaks until the final limiter; no auto makeup gain.
        mix = f"amix=inputs={len(project.clips)}:duration=longest:normalize=0,alimiter=limit=0.891251:level=0:latency=1"
        ffmpeg([*inputs, "-filter_complex", mix, "-ar", "48000", "-ac", "2",
                "-c:a", "pcm_s24le", staged])
        staged.replace(out)
    return out
