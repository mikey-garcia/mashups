from shared.models import Project, Clip

class Timeline:
    def __init__(self, project: Project): self.project = project
    def add(self, source: str, **kwargs) -> Clip:
        clip = Clip(source=source, **kwargs); self.project.clips.append(clip); return clip
    def move(self, clip: Clip, start: float): clip.start = max(0.0, start)
    def remove(self, clip: Clip): self.project.clips.remove(clip)
    def split(self, clip: Clip, at: float):
        if at <= clip.start: return None
        left = at - clip.start
        if clip.duration is not None and left >= clip.duration: return None
        old_duration = clip.duration
        clip.duration = left
        right_duration = None if old_duration is None else old_duration - left
        right = Clip(clip.source, at, clip.offset + left, right_duration, clip.gain_db, clip.pitch, clip.stretch)
        self.project.clips.append(right); return right
