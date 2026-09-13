from pathlib import Path
import tempfile
from mutagen.id3 import ID3, TIT2, TPE1, TALB, APIC, TDRC, TCON, COMM
from mutagen.mp3 import MP3
from desktop.audio import ffmpeg
from desktop.editor.render import render


def publish(project, title, artist, album="Mashups", artwork=None, library="library",
            output=None, year=None, genre=None, comments=None, engine="rubberband", overwrite=False):
    if not title.strip():
        raise ValueError("Title cannot be empty")
    safe = "".join(c for c in title if c.isalnum() or c in " -_()").strip() or "mashup"
    # Prefix protects reserved Windows device names such as CON and NUL.
    mp3 = Path(output or Path(library) / f"Mashup - {safe[:100]}.mp3").resolve()
    if mp3.suffix.lower() != ".mp3":
        raise ValueError("Published output must end in .mp3")
    sources = [Path(c.source).resolve() for c in project.clips]
    sources += [Path(s.path).resolve() for s in project.songs]
    if mp3 in sources:
        raise ValueError("Output must not overwrite a source")
    if mp3.exists() and not overwrite:
        raise FileExistsError(f"Output exists: {mp3}; use --overwrite to replace it")
    cover = None
    if artwork:
        cover = Path(artwork).read_bytes()
        if cover.startswith(b"\x89PNG\r\n\x1a\n"):
            mime = "image/png"
        elif cover.startswith(b"\xff\xd8\xff"):
            mime = "image/jpeg"
        else:
            raise ValueError("Artwork must be PNG or JPEG")
    mp3.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=mp3.parent) as td:
        wav = render(project, str(Path(td) / "mix.wav"), engine)
        staged = Path(td) / "tagged.mp3"
        ffmpeg(["-i", wav, "-map_metadata", "-1", "-c:a", "libmp3lame", "-q:a", "2", staged])
        audio = MP3(staged, ID3=ID3)
        if audio.tags is None:
            audio.add_tags()
        for frame in (TIT2(encoding=3, text=title), TPE1(encoding=3, text=artist),
                      TALB(encoding=3, text=album)):
            audio.tags.add(frame)
        if year:
            audio.tags.add(TDRC(encoding=3, text=str(year)))
        if genre:
            audio.tags.add(TCON(encoding=3, text=genre))
        if comments:
            audio.tags.add(COMM(encoding=3, lang="eng", desc="", text=comments))
        if cover:
            audio.tags.add(APIC(encoding=3, mime=mime, type=3, desc="Cover", data=cover))
        audio.save()
        if overwrite:
            staged.replace(mp3)
        else:
            # Same-volume hard link publishes the complete file atomically and fails
            # if another export claimed this path after our initial check (NTFS/POSIX).
            mp3.hardlink_to(staged)
    return mp3
