"""Background pipeline runner used by the Streamlit GUI.

This module contains no Streamlit imports so it can be unit-tested in
isolation and run from any host that wants to drive the pipeline without
blocking the UI thread.
"""

from __future__ import annotations

import threading
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from meeting_ai.pipeline import PipelineResult, process_transcript_source

from .stages import STAGE_ORDER


@dataclass
class RunState:
    """Mutable shared state inspected by the UI thread."""

    stage: str = "queued"
    completed: List[str] = field(default_factory=list)
    started_at: float = 0.0
    finished_at: float = 0.0
    error: Optional[str] = None
    error_trace: Optional[str] = None
    result: Optional[PipelineResult] = None

    @property
    def elapsed(self) -> float:
        if self.started_at == 0.0:
            return 0.0
        end = self.finished_at if self.finished_at else time.time()
        return max(0.0, end - self.started_at)

    @property
    def is_done(self) -> bool:
        return self.stage == "done" or self.stage == "failed"

    @property
    def is_running(self) -> bool:
        return self.started_at > 0.0 and not self.is_done


class PipelineRunner:
    """Run `process_transcript_source` in a background thread.

    The runner exposes a thread-safe `state` object that the UI polls every
    second. It deliberately keeps Streamlit dependencies at the call site.
    """

    def __init__(
        self,
        *,
        source_path: Path,
        runs_dir: Path,
        run_id: Optional[str],
        profile: Dict[str, Any],
        pipeline_config: Dict[str, Any],
        models_config: Dict[str, Any],
    ) -> None:
        self._source_path = source_path
        self._runs_dir = runs_dir
        self._run_id = run_id
        self._profile = profile
        self._pipeline_config = pipeline_config
        self._models_config = models_config
        self.state = RunState()
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread is not None:
            raise RuntimeError("runner already started")
        self.state.started_at = time.time()
        self.state.stage = "queued"
        self._thread = threading.Thread(
            target=self._run, name="momo-pipeline", daemon=True
        )
        self._thread.start()

    def _on_stage(self, stage: str) -> None:
        with self._lock:
            previous = self.state.stage
            if previous != stage and stage in STAGE_ORDER:
                stage_index = STAGE_ORDER.index(stage)
                for completed_stage in STAGE_ORDER[:stage_index]:
                    if completed_stage not in self.state.completed:
                        self.state.completed.append(completed_stage)
            elif (
                previous
                and previous != stage
                and previous in STAGE_ORDER
                and previous not in self.state.completed
            ):
                self.state.completed.append(previous)
            self.state.stage = stage

    def _run(self) -> None:
        try:
            result = process_transcript_source(
                source_path=self._source_path,
                runs_dir=self._runs_dir,
                run_id=self._run_id,
                profile=self._profile,
                pipeline_config=self._pipeline_config,
                models_config=self._models_config,
                on_stage=self._on_stage,
            )
        except Exception as exc:  # pragma: no cover - reported to UI
            with self._lock:
                self.state.error = str(exc) or exc.__class__.__name__
                self.state.error_trace = traceback.format_exc()
                self.state.stage = "failed"
                self.state.finished_at = time.time()
            return

        with self._lock:
            self.state.result = result
            self.state.stage = "done"
            self.state.finished_at = time.time()
