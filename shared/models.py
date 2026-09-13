from __future__ import annotations
from dataclasses import dataclass, asdict, field
from pathlib import Path
import json
import math

@dataclass
class Analysis:
    bpm: float | None = None
    key: str | None = None
    beats: list[float] = field(default_factory=list)

@dataclass
class Song:
    path: str
    title: str = ""
    analysis: Analysis = field(default_factory=Analysis)
    stems: dict[str, str] = field(default_factory=dict)
    duration: float | None = None

@dataclass
class Clip:
    """start is timeline seconds; offset/duration are source seconds.

    stretch = output duration / source duration; pitch is semitones.
    None duration means all remaining source audio.
    """
    source: str
    start: float = 0.0
    offset: float = 0.0
    duration: float | None = None
    gain_db: float = 0.0
    pitch: float = 0.0
    stretch: float = 1.0

    def validate(self):
        for name in ("start", "offset", "gain_db", "pitch", "stretch"):
            if not math.isfinite(getattr(self, name)):
                raise ValueError(f"{name} must be finite")
        if self.start < 0 or self.offset < 0:
            raise ValueError("start and offset must be nonnegative")
        if self.duration is not None and (not math.isfinite(self.duration) or self.duration <= 0):
            raise ValueError("duration must be positive and finite")
        if not 0.5 <= self.stretch <= 2:
            raise ValueError("stretch must be between 0.5 and 2")
        if not -24 <= self.pitch <= 24:
            raise ValueError("pitch must be between -24 and 24 semitones")

@dataclass
class Project:
    name: str
    bpm: float | None = None
    key: str | None = None
    songs: list[Song] = field(default_factory=list)
    clips: list[Clip] = field(default_factory=list)

    def save(self, path: str | Path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(asdict(self), indent=2, allow_nan=False), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path):
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        d["songs"] = [Song(**(s | {"analysis": Analysis(**s.get("analysis", {}))})) for s in d.get("songs", [])]
        d["clips"] = [Clip(**c) for c in d.get("clips", [])]
        return cls(**d)
