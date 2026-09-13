"""Headless mashup workflow. Run from the repo root with python -m desktop.cli."""
import argparse
import math
from pathlib import Path
import sys
import uuid

from desktop.downloader.downloader import import_source
from desktop.editor.timeline import Timeline
from desktop.publisher.publisher import publish
from shared.models import Analysis, Clip, Project


def positive(value):
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise argparse.ArgumentTypeError("must be positive and finite")
    return result


def mash(args):
    for source in (args.vocals_from, args.instrumental_from):
        if Path(source).is_file() and Path(source).resolve() == args.output.resolve():
            raise ValueError("Output must not overwrite an input song")
    for label in ("vocal", "instrumental"):
        clip = Clip("", start=getattr(args, f"{label}_start"),
                    offset=getattr(args, f"{label}_offset"), duration=getattr(args, f"{label}_duration"),
                    stretch=getattr(args, f"{label}_stretch") or 1,
                    pitch=getattr(args, f"{label}_pitch"), gain_db=getattr(args, f"{label}_gain"))
        clip.validate()
        if args.engine == "atempo" and clip.pitch:
            raise ValueError("Pitch shifting requires --engine rubberband")
    if args.output.exists() and not args.overwrite:
        raise FileExistsError(f"Output exists: {args.output}; use --overwrite to replace it")
    if args.output.suffix.lower() != ".mp3":
        raise ValueError("Published output must end in .mp3")
    if args.project and args.project.exists():
        raise FileExistsError(f"Project already exists: {args.project}; choose a new path")
    if args.project and args.project.resolve() == args.output.resolve():
        raise ValueError("Project JSON and audio output must have different paths")
    work = args.work_dir.resolve() / uuid.uuid4().hex[:12]
    project_path = args.project or work / "project.mashup"
    project = Project(args.title)
    for label, source, manual_bpm in (("vocals", args.vocals_from, args.vocal_bpm),
                                       ("instrumental", args.instrumental_from, args.instrumental_bpm)):
        print(f"Importing {label}: {source}", flush=True)
        song = import_source(source, work / "sources")
        if not args.skip_analysis:
            print(f"Analyzing {label}...", flush=True)
            from desktop.analysis.music import analyze
            song.analysis = Analysis(**analyze(song.path))
        if manual_bpm is not None:
            song.analysis.bpm = manual_bpm
        if args.pre_separated:
            song.stems[label] = song.path
        else:
            print(f"Separating {label} ({args.device}); this can take several minutes...", flush=True)
            from desktop.analysis.stems import separate
            song.stems = separate(song.path, work / "stems", not args.four_stems, device=args.device)
        project.songs.append(song)
    project.bpm = args.target_bpm
    timeline = Timeline(project)
    for label, song in zip(("vocal", "instrumental"), project.songs):
        stretch = getattr(args, f"{label}_stretch")
        if stretch is None:
            stretch = 1.0
            if args.target_bpm is not None:
                bpm = song.analysis.bpm
                if bpm is None or not math.isfinite(bpm) or bpm <= 0:
                    raise ValueError(f"Supply --{label}-bpm or --{label}-stretch to use --target-bpm")
                stretch = bpm / args.target_bpm
        stem = "vocals" if label == "vocal" else label
        timeline.add(song.stems[stem], start=getattr(args, f"{label}_start"),
                     offset=getattr(args, f"{label}_offset"), duration=getattr(args, f"{label}_duration"),
                     stretch=stretch, pitch=getattr(args, f"{label}_pitch"),
                     gain_db=getattr(args, f"{label}_gain"))
    project.save(project_path)
    print(f"Saved project: {project_path}", flush=True)
    return export(project, args)


def export(project, args):
    print("Rendering and tagging MP3...", flush=True)
    return publish(project, args.title, args.artist, args.album, args.artwork,
                   output=args.output, year=args.year, genre=args.genre,
                   comments=args.comments, engine=args.engine, overwrite=args.overwrite)


def parser():
    p = argparse.ArgumentParser(description="Mashups: local two-track mashup pipeline")
    sub = p.add_subparsers(dest="command", required=True)
    m = sub.add_parser("mash", help="import, optionally analyze/separate, mix and tag")
    m.add_argument("--vocals-from", required=True, help="Song A file or HTTP(S) URL")
    m.add_argument("--instrumental-from", required=True, help="Song B file or HTTP(S) URL")
    m.add_argument("--pre-separated", action="store_true", help="inputs are already vocals/instrumental")
    m.add_argument("--skip-analysis", action="store_true", help="use manual BPM/stretch only")
    m.add_argument("--four-stems", action="store_true")
    m.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    m.add_argument("--target-bpm", type=positive)
    m.add_argument("--work-dir", type=Path, default=Path("projects"))
    m.add_argument("--project", type=Path, help="save editable JSON here (must be a new file)")
    for label in ("vocal", "instrumental"):
        m.add_argument(f"--{label}-bpm", type=positive)
        m.add_argument(f"--{label}-stretch", type=positive, help="output/source duration; overrides BPM ratio")
        m.add_argument(f"--{label}-duration", type=positive, help="source seconds to keep")
        for field in ("start", "offset", "pitch", "gain"):
            m.add_argument(f"--{label}-{field}", type=float, default=0.0)
    r = sub.add_parser("render", help="render and tag an existing project JSON")
    r.add_argument("project", type=Path)
    for command in (m, r):
        command.add_argument("--title", required=True)
        command.add_argument("--artist", default="Shnatty")
        command.add_argument("--album", default="Mashups")
        command.add_argument("--artwork", type=Path)
        command.add_argument("--year")
        command.add_argument("--genre")
        command.add_argument("--comments")
        command.add_argument("--output", type=Path, required=True)
        command.add_argument("--engine", choices=("rubberband", "atempo"), default="rubberband")
        command.add_argument("--overwrite", action="store_true")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        output = mash(args) if args.command == "mash" else export(Project.load(args.project), args)
    except (OSError, RuntimeError, ValueError, ImportError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Published: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
