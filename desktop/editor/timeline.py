from dataclasses import replace
import math
from shared.models import Project, Clip


class Timeline:
    def __init__(self, project: Project):
        self.project = project

    def add(self, source: str, **kwargs) -> Clip:
        clip = Clip(source=source, **kwargs)
        clip.validate()
        self.project.clips.append(clip)
        return clip

    def move(self, clip: Clip, start: float):
        if not math.isfinite(start):
            raise ValueError("start must be finite")
        clip.start = max(0.0, start)

    def remove(self, clip: Clip):
        self.project.clips.remove(clip)

    def trim(self, clip: Clip, offset: float, duration: float | None):
        candidate = replace(clip, offset=offset, duration=duration)
        candidate.validate()
        clip.offset, clip.duration = offset, duration

    def split(self, clip: Clip, at: float):
        clip.validate()
        if not math.isfinite(at):
            raise ValueError("split position must be finite")
        left = (at - clip.start) / clip.stretch
        if left <= 0 or (clip.duration is not None and left >= clip.duration):
            return None
        right = replace(clip, start=at, offset=clip.offset + left,
                        duration=None if clip.duration is None else clip.duration - left)
        clip.duration = left
        self.project.clips.append(right)
        return right
