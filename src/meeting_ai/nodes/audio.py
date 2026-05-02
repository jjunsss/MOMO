"""Audio extraction for media inputs."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from meeting_ai.utils.io import ensure_dir


def extract_audio(source_path: Path, output_path: Path) -> Path:
    ensure_dir(output_path.parent)
    if output_path.exists() and output_path.stat().st_size > 0:
        return output_path

    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "ffmpeg is not on PATH. Install ffmpeg to extract audio from media inputs."
        )

    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(source_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(output_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(
            "ffmpeg failed for {0} (exit {1}): {2}".format(
                source_path, completed.returncode, completed.stderr.strip().splitlines()[-1] if completed.stderr.strip() else "no stderr"
            )
        )
    return output_path

