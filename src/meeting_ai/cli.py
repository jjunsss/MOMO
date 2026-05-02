"""Command line interface for the meeting summary pipeline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from meeting_ai.config.loader import load_models_config, load_pipeline_config, load_user_profile
from meeting_ai.config.markdown_profile import load_markdown_profile
from meeting_ai.config.topic_details import apply_topic_details
from meeting_ai.nodes.source_discovery import derive_run_id, find_latest_media
from meeting_ai.pipeline import process_transcript_source
from meeting_ai.renderers.markdown import render_summary_markdown
from meeting_ai.utils.io import read_json, write_text


SUBCOMMANDS = {"process", "render", "auto"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="momo",
        description=(
            "Run the meeting summary pipeline. "
            "Without a subcommand, defaults to `auto` using videos/ and topic_details.json."
        ),
    )
    subparsers = parser.add_subparsers(dest="command")

    process_parser = subparsers.add_parser("process", help="process transcript JSON")
    process_parser.add_argument("source", type=Path, help="transcript JSON path")
    process_parser.add_argument("--profile", type=Path, default=Path("config/user_profile.example.yaml"))
    process_parser.add_argument("--profile-md", type=Path, default=None)
    process_parser.add_argument("--topic-details", type=Path, default=Path("topic_details.json"))
    process_parser.add_argument("--pipeline-config", type=Path, default=Path("config/pipeline.yaml"))
    process_parser.add_argument("--models-config", type=Path, default=Path("config/models.yaml"))
    process_parser.add_argument("--runs-dir", type=Path, default=Path("runs"))
    process_parser.add_argument("--run-id", default=None)
    process_parser.add_argument("--asr-model", default=None, help="override ASR model name")

    render_parser = subparsers.add_parser("render", help="render final_summary.json to Markdown")
    render_parser.add_argument("summary_json", type=Path)
    render_parser.add_argument("--output", type=Path, default=None)

    auto_parser = subparsers.add_parser("auto", help="process the newest media file")
    auto_parser.add_argument("--profile-md", type=Path, default=Path("meeting_profile.md"))
    auto_parser.add_argument("--topic-details", type=Path, default=Path("topic_details.json"))
    auto_parser.add_argument("--videos-dir", type=Path, default=None)
    auto_parser.add_argument("--runs-dir", type=Path, default=Path("runs"))
    auto_parser.add_argument("--run-id", default=None)
    auto_parser.add_argument("--asr-model", default=None, help="override ASR model name")

    return parser


def run_process(args: argparse.Namespace) -> int:
    if args.profile_md:
        loaded = _load_markdown_runtime(args.profile_md, args.topic_details)
    else:
        loaded = {
            "profile": load_user_profile(args.profile),
            "pipeline_config": load_pipeline_config(args.pipeline_config),
            "models_config": load_models_config(args.models_config),
        }
    profile = loaded["profile"]
    pipeline_config = loaded["pipeline_config"]
    models_config = loaded["models_config"]
    if args.asr_model:
        models_config.setdefault("asr", {})["model"] = args.asr_model
    result = process_transcript_source(
        source_path=args.source,
        runs_dir=args.runs_dir,
        run_id=args.run_id,
        profile=profile,
        pipeline_config=pipeline_config,
        models_config=models_config,
    )
    print("Run ID: {0}".format(result.run_id))
    print("Final JSON: {0}".format(result.final_summary_path))
    print("Markdown: {0}".format(result.markdown_path))
    print("Evidence: {0}".format(result.evidence_path))
    return 0


def run_auto(args: argparse.Namespace) -> int:
    loaded = _load_markdown_runtime(args.profile_md, args.topic_details)
    profile = loaded["profile"]
    pipeline_config = loaded["pipeline_config"]
    models_config = loaded["models_config"]
    automation = loaded["automation"]
    if args.asr_model:
        models_config.setdefault("asr", {})["model"] = args.asr_model

    videos_dir = args.videos_dir or Path(automation["videos_dir"])
    source_path = find_latest_media(videos_dir)
    run_id = args.run_id or derive_run_id(source_path, automation.get("run_id", "auto"))
    result = process_transcript_source(
        source_path=source_path,
        runs_dir=args.runs_dir,
        run_id=run_id,
        profile=profile,
        pipeline_config=pipeline_config,
        models_config=models_config,
    )
    print("Source: {0}".format(source_path))
    print("Run ID: {0}".format(result.run_id))
    print("Final JSON: {0}".format(result.final_summary_path))
    print("Markdown: {0}".format(result.markdown_path))
    print("Evidence: {0}".format(result.evidence_path))
    return 0


def _load_markdown_runtime(profile_md: Path, topic_details: Optional[Path]) -> dict:
    loaded = load_markdown_profile(profile_md)
    return apply_topic_details(loaded, topic_details)


def run_render(args: argparse.Namespace) -> int:
    summary = read_json(args.summary_json)
    markdown = render_summary_markdown(summary)
    output: Optional[Path] = args.output
    if output is None:
        output = args.summary_json.with_suffix(".md")
    write_text(output, markdown)
    print("Markdown: {0}".format(output))
    return 0


def _route_to_auto_by_default(argv: List[str]) -> List[str]:
    if not argv:
        return ["auto"]
    first = argv[0]
    if first in SUBCOMMANDS or first in {"-h", "--help"}:
        return argv
    return ["auto"] + argv


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    args = parser.parse_args(_route_to_auto_by_default(raw_argv))
    if args.command == "process":
        return run_process(args)
    if args.command == "auto":
        return run_auto(args)
    if args.command == "render":
        return run_render(args)
    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
