import base64
import math
from pathlib import Path
import struct
import sys
from types import SimpleNamespace
import wave

import pytest
from mutagen.mp3 import MP3
from desktop.audio import ffmpeg, probe
from desktop.cli import main
from desktop.downloader.downloader import import_file
from desktop.editor.render import render
from desktop.editor.timeline import Timeline
from desktop.publisher.publisher import publish
from shared.models import Analysis, Clip, Project, Song


def tone(path, frequency=440, seconds=2, rate=22050):
    with wave.open(str(path), "wb") as f:
        f.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        f.writeframes(b"".join(struct.pack("<h", round(14000 * math.sin(2 * math.pi * frequency * i / rate)))
                               for i in range(round(seconds * rate))))
    return path


def samples(path, tmp_path):
    target = tmp_path / "decoded.wav"
    ffmpeg(["-i", path, "-ac", "1", "-c:a", "pcm_s16le", target])
    with wave.open(str(target)) as f:
        rate = f.getframerate()
        data = struct.unpack(f"<{f.getnframes()}h", f.readframes(f.getnframes()))
    return rate, data


def test_roundtrip_and_stretched_split(tmp_path):
    p = Project("Unicode 🎵", songs=[Song("a.wav", analysis=Analysis(120, None, [0.1]))])
    t = Timeline(p)
    c = t.add("a.wav", start=3, offset=2, duration=4, stretch=2, pitch=2)
    right = t.split(c, 5)
    assert (c.duration, right.start, right.offset, right.duration) == (1, 5, 3, 3)
    t.trim(right, 4, 2)
    assert right.offset == 4 and right.duration == 2
    p.save(tmp_path / "project.mashup")
    assert Project.load(tmp_path / "project.mashup") == p
    with pytest.raises(ValueError):
        t.trim(c, -1, 1)
    assert c.offset == 2


@pytest.mark.parametrize("field,value", [("stretch", 0), ("start", float("nan")), ("offset", -1),
                                         ("duration", -1), ("pitch", 25)])
def test_invalid_clip(field, value):
    with pytest.raises(ValueError):
        Clip("a.wav", **{field: value}).validate()


def test_import_canonical_and_identity(tmp_path):
    a = tone(tmp_path / "a.wav")
    s = import_file(a, tmp_path / "sources")
    assert probe(s.path) == {"duration": 2.0, "channels": 2, "sample_rate": 48000}
    assert import_file(a, tmp_path / "sources").path == s.path
    tone(a, frequency=880)
    assert import_file(a, tmp_path / "sources").path != s.path


def test_pitch_stretch_offset_and_delay(tmp_path):
    a = tone(tmp_path / "a.wav", seconds=3)
    p = Project("render", clips=[Clip(str(a), start=.25, offset=.5, duration=1, pitch=12, stretch=1.5)])
    out = render(p, str(tmp_path / "mix.wav"))
    assert probe(out)["duration"] == pytest.approx(1.75, abs=1/48000)
    rate, data = samples(out, tmp_path)
    assert max(abs(v) for v in data[:int(.24 * rate)]) < 2
    stable = data[int(.6 * rate):int(1.2 * rate)]
    crossings = sum(a <= 0 < b for a, b in zip(stable, stable[1:]))
    assert crossings / .6 == pytest.approx(880, abs=5)


def test_limiter_and_failed_render_preserves_output(tmp_path):
    a = tone(tmp_path / "a.wav")
    p = Project("loud", clips=[Clip(str(a), gain_db=15), Clip(str(a), gain_db=15)])
    out = render(p, str(tmp_path / "mix.wav"))
    _, data = samples(out, tmp_path)
    assert .8 * 32768 < max(abs(v) for v in data) <= .892 * 32768
    previous = out.read_bytes()
    p.clips[0].offset = 99
    with pytest.raises(ValueError):
        render(p, str(out))
    assert out.read_bytes() == previous


def test_cli_publish_and_rerender(tmp_path):
    a, b = tone(tmp_path / "a.wav"), tone(tmp_path / "b.wav", frequency=660)
    cover = tmp_path / "cover.png"
    cover.write_bytes(base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII="))
    out, project = tmp_path / "out.mp3", tmp_path / "saved.mashup"
    args = ["mash", "--vocals-from", str(a), "--instrumental-from", str(b),
            "--pre-separated", "--skip-analysis", "--vocal-bpm", "120", "--instrumental-bpm", "100",
            "--target-bpm", "100", "--vocal-start", ".2", "--vocal-pitch", "2",
            "--title", "A × B", "--artist", "Shnatty", "--album", "Tests", "--year", "2026",
            "--genre", "Mashup", "--comments", "Generated test tones", "--artwork", str(cover),
            "--output", str(out), "--project", str(project), "--work-dir", str(tmp_path / "work")]
    assert main(args) == 0
    audio = MP3(out)
    assert str(audio.tags["TIT2"]) == "A × B"
    assert str(audio.tags["TPE1"]) == "Shnatty"
    assert str(audio.tags["TALB"]) == "Tests"
    assert audio.tags.getall("APIC")[0].data == cover.read_bytes()
    p = Project.load(project)
    assert p.clips[0].stretch == 1.2 and p.clips[0].start == .2
    assert audio.info.length == pytest.approx(2.6, abs=.05)
    assert main(args) == 1  # no accidental overwrite or expensive reprocessing
    assert main(["render", str(project), "--title", "Again", "--output", str(tmp_path / "again.mp3")]) == 0


def test_publisher_failure_preserves_existing_file(tmp_path):
    target = tmp_path / "existing.mp3"
    target.write_bytes(b"existing")
    with pytest.raises(ValueError):
        publish(Project("empty"), "Title", "Artist", output=target, overwrite=True)
    assert target.read_bytes() == b"existing"


def test_downloader_uses_reported_file(monkeypatch, tmp_path):
    from desktop.downloader import downloader
    chosen = tone(tmp_path / "chosen.wav")
    tone(tmp_path / "newer-unrelated.wav", frequency=900)
    def fake_run(cmd):
        import json
        assert cmd[:3] == [sys.executable, "-m", "yt_dlp"]
        assert "--ignore-config" in cmd and "after_move:%(filepath)j" in cmd
        return SimpleNamespace(stdout=json.dumps(str(chosen)) + "\n")
    monkeypatch.setattr(downloader, "run", fake_run)
    assert downloader.download("https://example.test/audio", tmp_path / "sources").title == "chosen"


@pytest.mark.parametrize("two_stem", [True, False])
def test_demucs_outputs(monkeypatch, tmp_path, two_stem):
    from desktop.analysis import stems
    source = tone(tmp_path / "input.wav")
    def fake_run(cmd):
        assert cmd[:3] == [sys.executable, "-m", "demucs"]
        root = Path(cmd[cmd.index("-o") + 1]) / "htdemucs" / "input"
        root.mkdir(parents=True)
        for name in (["vocals", "no_vocals"] if two_stem else ["vocals", "drums", "bass", "other"]):
            tone(root / f"{name}.wav")
    monkeypatch.setattr(stems, "run", fake_run)
    result = stems.separate(str(source), tmp_path / "stems", two_stem)
    assert {"vocals", "instrumental"} <= result.keys()
    assert "no_vocals" not in result
    assert all(Path(p).exists() for p in result.values())
    if not two_stem:
        _, data = samples(result["instrumental"], tmp_path)
        assert max(abs(v) for v in data) > 30000  # summed, not averaged


def test_server_upload_download(tmp_path, monkeypatch):
    import io
    monkeypatch.setenv("MASH_LIBRARY", str(tmp_path / "library"))
    monkeypatch.setenv("MASH_DB", str(tmp_path / "library.db"))
    monkeypatch.setenv("MASH_PASSWORD", "test-password")
    monkeypatch.setenv("MASH_UPLOAD_TOKEN", "test-token")
    from server.app import app
    client = app.test_client()
    assert client.get("/").status_code == 302
    assert client.post("/api/tracks").status_code == 401
    response = client.post("/api/tracks", headers={"Authorization": "Bearer test-token"},
                           data={"title": "Test", "audio": (io.BytesIO(b"audio"), "test.mp3")})
    assert response.status_code == 200
    path = response.json["path"]
    assert client.get(path).status_code == 302
    client.post("/login", data={"password": "test-password"})
    assert client.get(path).data == b"audio"


def test_missing_demucs_output_cannot_use_stale_run(monkeypatch, tmp_path):
    from desktop.analysis import stems
    source = tone(tmp_path / "input.wav")
    stale = tmp_path / "stems" / "htdemucs" / "input"
    stale.mkdir(parents=True)
    tone(stale / "vocals.wav")
    tone(stale / "no_vocals.wav")
    monkeypatch.setattr(stems, "run", lambda cmd: None)
    with pytest.raises(RuntimeError, match="did not produce"):
        stems.separate(str(source), tmp_path / "stems")


def test_atempo_duration_and_pitch_rejection(tmp_path):
    a = tone(tmp_path / "a.wav")
    p = Project("tempo", clips=[Clip(str(a), stretch=.75)])
    assert probe(render(p, str(tmp_path / "mix.wav"), engine="atempo"))["duration"] == pytest.approx(1.5)
    p.clips[0].pitch = 2
    with pytest.raises(ValueError, match="Pitch shifting requires"):
        render(p, str(tmp_path / "mix.wav"), engine="atempo")


def test_cli_rejects_bad_parameters_before_import(tmp_path, monkeypatch):
    from desktop import cli
    monkeypatch.setattr(cli, "import_source", lambda *args: pytest.fail("should validate before import"))
    assert main(["mash", "--vocals-from", "a.mp3", "--instrumental-from", "b.mp3",
                 "--vocal-start", "nan", "--title", "Bad", "--output", str(tmp_path / "bad.mp3")]) == 1
