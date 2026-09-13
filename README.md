# Mashups

A local, purpose-built mashup pipeline with a separate private distribution server.
The first usable interface is a CLI: two songs → vocals/instrumental → manually
configured mix → tagged MP3. Projects are readable JSON, not a binary format.

## Install on Windows

Use Python 3.11 or 3.12. Install FFmpeg and put both `ffmpeg` and `ffprobe` on PATH.
Pitch shifting and the default stretch engine require an FFmpeg build with
[librubberband](https://ffmpeg.org/ffmpeg-filters.html#rubberband). Check with:

```powershell
ffmpeg -filters | Select-String rubberband
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m desktop.cli --help
```

`requirements.txt` installs the desktop dependencies only. Demucs uses a matched
PyTorch/torchaudio pair older than 2.6; these bounds avoid removed torchaudio APIs.
CPU is the default and works without a supported GPU. `--device cuda` requires a
CUDA-capable NVIDIA GPU and the corresponding PyTorch installation. Separation
can take several minutes and downloads model weights on first use.

For already-separated audio, install only `requirements-core.txt` and use
`--pre-separated --skip-analysis`. This avoids all ML dependencies. `yt-dlp` is
invoked using the active virtual environment, so it needs no separate PATH entry.

## Make a mashup

```powershell
python -m desktop.cli mash `
  --vocals-from "song-a.mp3" `
  --instrumental-from "song-b.mp3" `
  --vocal-bpm 128 --instrumental-bpm 120 --target-bpm 120 `
  --title "Song A x Song B" --artist "Shnatty" `
  --artwork "cover.jpg" `
  --output "library\song-a-x-song-b.mp3"
```

Either input can also be an HTTP(S) URL supported by yt-dlp. A URL imports exactly
one result; playlists and user yt-dlp configuration are disabled. Only import
media you have permission to download.

By default both complete songs are analyzed before separation. `--vocal-bpm` and
`--instrumental-bpm` override estimates. BPM matching changes playback speed;
it does **not** identify the correct musical entry point. Without `--target-bpm`
or explicit stretch, both tracks retain their original tempo.

For a quick run with existing stems and no analysis:

```powershell
python -m desktop.cli mash `
  --vocals-from "vocals.wav" --instrumental-from "instrumental.wav" `
  --pre-separated --skip-analysis `
  --vocal-stretch 1.0666667 --vocal-start 8 --vocal-pitch 2 --vocal-gain -3 `
  --title "My Mashup" --output "library\my-mashup.mp3"
```

Both tracks have `--vocal-*` / `--instrumental-*` controls:

| Control | Meaning |
|---|---|
| `start` | Placement in timeline seconds; default 0 |
| `offset` | Seconds skipped at the beginning of the source; default 0 |
| `duration` | Source seconds retained; default is all remaining audio |
| `stretch` | Output duration / source duration; range 0.5–2; overrides BPM calculation |
| `bpm` | Override detected source BPM |
| `pitch` | Pitch shift in semitones; range −24 to +24 |
| `gain` | Gain in dB; default 0 |

For 128 → 120 BPM, stretch is `128/120`, and the DSP tempo factor is `120/128`.
A split at timeline time `t` advances the source offset by `(t-start)/stretch`.
`--engine atempo` provides tempo-only rendering when Rubber Band is unavailable;
it rejects nonzero pitch instead of silently ignoring it.

Two-stem separation is the default. `--four-stems` also retains drums, bass and
other, and sums them into the instrumental. Both modes expose `vocals` and
`instrumental` through the same interface. Demucs runs in isolated directories
with random shift augmentation disabled. No cross-device bit-exact ML guarantee
is made.

## Projects and export

Each run creates `projects/<run-id>/` containing canonical 48 kHz stereo FLAC
sources, stems and `project.mashup`. Imports are keyed by source content within
that run. Original files are never edited. CLI-created project paths are absolute:
you can re-render from another working directory, but moving the project to a new
machine currently requires updating its paths. Separation results remain available
for re-rendering; separate CLI runs do not yet share a stem cache.

Use `--project new-path.mashup` to choose the JSON location. The CLI prints the
saved path before rendering so failures can be corrected without separating again.
Edit clip values in that JSON, then:

```powershell
python -m desktop.cli render "projects\RUN-ID\project.mashup" `
  --title "My Mashup" --artist "Shnatty" --output "library\revision.mp3"
```

Exports include title, artist and album. Optional flags: `--year`, `--genre`,
`--comments` and `--artwork` (PNG/JPEG). Existing output files require `--overwrite`.
Temporary rendering/tagging completes before the finished MP3 is published.

Rendering uses float WAV intermediates, sample-based timeline placement, and a
final limiter at −1 dBFS with automatic makeup gain disabled. The master WAV is
48 kHz stereo 24-bit PCM; MP3 uses LAME VBR quality 2. The limiter protects PCM
sample peaks; this is not loudness normalization or a true-peak guarantee after
lossy encoding. Use gains to balance tracks and listen for over-limiting.

## Tests

```powershell
python -m pip install -r requirements-core.txt -r server/requirements.txt pytest
python -m pytest -q
```

Tests generate their own tones; no copyrighted audio is bundled. They cover
JSON round-trips, stretched splits, canonical imports, measured pitch/duration,
limiting, CLI export/re-render, ID3 artwork, output preservation and basic server
auth/upload/download. Demucs and yt-dlp subprocess results are simulated in unit
tests; those tests do not establish separation quality or live site compatibility.
A Linux CPU smoke run also completed with two generated eight-second inputs using
real librosa analysis, Demucs htdemucs separation, Rubber Band tempo adjustment and
tagged MP3 export. A real yt-dlp import from a local HTTP server passed. These
smoke runs establish execution, not musical separation quality or compatibility
with every external site. Full-song listening and Windows ML installation remain
important local checks.

## Layout and next milestones

- `shared/models.py`: Song/Analysis/Clip/Project and JSON serialization.
- `desktop/audio.py`: thin FFmpeg/ffprobe process boundary.
- `desktop/downloader`: interchangeable URL/file import into Song.
- `desktop/analysis`: librosa analysis and Demucs adapter.
- `desktop/editor`: timeline state and offline rendering.
- `desktop/publisher`: MP3 tagging and independent HTTP upload adapter.
- `desktop/cli.py`: pipeline orchestration.
- `server`: small Flask library; no desktop or ML imports.

The analysis key field is currently only the strongest average chroma pitch class;
it does not reliably determine tonic or major/minor. BPM/beat estimates may need
manual correction. Downbeat detection, Auto Sync, playback, waveforms, desktop UI,
undo/redo, music section detection, FLAC publishing and CLI upload are still future
work. The next milestone is listening to a real two-song export, then playback and
a basic timeline over this pipeline.

## Private server (separate installation)

On the Linode, install only `server/requirements.txt`. Configure the three values
from `.env.example` as environment variables; the application does not auto-load
that file. `python -m server.app` starts the development server on 127.0.0.1:8000.
`Caddyfile.example` shows the reverse proxy configuration for music.shnatty.com.

The server is still a prototype: production secret validation, upload limits,
filename collisions, session hardening and a production WSGI runner need work
before deployment. This pipeline change does not deploy it. Desktop/server
communication remains HTTP through `desktop/publisher/upload.py`.

The mobile page downloads a normal MP3. Spotify Local Files setup is manual;
there is no direct Spotify import or public-catalog upload integration.
