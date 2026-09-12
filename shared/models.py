from __future__ import annotations
from dataclasses import dataclass, asdict, field
from pathlib import Path
import json

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

@dataclass
class Clip:
    source: str
    start: float = 0.0
    offset: float = 0.0
    duration: float | None = None
    gain_db: float = 0.0
    pitch: float = 0.0
    stretch: float = 1.0

@dataclass
class Project:
    name: str
    bpm: float | None = None
    key: str | None = None
    songs: list[Song] = field(default_factory=list)
    clips: list[Clip] = field(default_factory=list)

    def save(self, path: str | Path):
        Path(path).write_text(json.dumps(asdict(self), indent=2))

    @classmethod
    def load(cls, path: str | Path):
        d = json.loads(Path(path).read_text())
        d["songs"] = [Song(**(s | {"analysis": Analysis(**s.get("analysis", {}))})) for s in d.get("songs", [])]
        d["clips"] = [Clip(**c) for c in d.get("clips", [])]
        return cls(**d)
