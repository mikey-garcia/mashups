from pathlib import Path

def analyze(path: str):
    import librosa
    y, sr = librosa.load(path, sr=None, mono=True)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beats = librosa.frames_to_time(beat_frames, sr=sr).tolist()
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    profile = chroma.mean(axis=1)
    names = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
    key = names[int(profile.argmax())]  # intentionally simple V0 key estimate
    return {"bpm": float(tempo.item() if hasattr(tempo, "item") else tempo), "key": key, "beats": beats}
