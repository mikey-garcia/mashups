# Shnatty Mash — V0

Local-first mashup pipeline with a separately deployable private distribution server.

## Layout
- `desktop/downloader`: yt-dlp adapter
- `desktop/analysis`: Demucs stems + librosa beat/key analysis
- `desktop/editor`: timeline model + FFmpeg renderer
- `desktop/publisher`: MP3 encoding/tagging + HTTPS upload
- `shared`: project/song/clip data model
- `server`: password-protected Flask library and upload API

## Local prerequisites
Install Python 3.11/3.12, FFmpeg and yt-dlp, then:

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

Demucs is CPU-capable but a supported GPU is much faster.

## Server
Only `server/` plus its Python dependencies need to run on the Linode. Set the three values from `.env.example`, then:

```bash
export MASH_PASSWORD='...'
export MASH_UPLOAD_TOKEN='...'
export MASH_SECRET='...'
python -m server.app
```

Put Caddy in front using `Caddyfile.example`.

## Current V0
The backend pipeline and private server are implemented. The graphical timeline UI is deliberately not faked yet: the next milestone is a thin desktop UI over the working `Project -> Timeline -> render -> publish` API.

## Notes
Use the downloader only for media you have permission to download. Password protection controls access; it does not itself grant redistribution rights.
