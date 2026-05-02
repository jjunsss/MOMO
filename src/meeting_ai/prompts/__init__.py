"""Prompt templates loaded from sibling Markdown files."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

PROMPT_DIR = Path(__file__).resolve().parent


def load_prompt(name: str) -> str:
    path = PROMPT_DIR / "{0}.md".format(name)
    if not path.exists():
        raise FileNotFoundError("prompt template not found: {0}".format(path))
    return path.read_text(encoding="utf-8")


def render(template: str, **values: Any) -> str:
    """Lightweight ``{{ key }}`` substitution.

    We deliberately avoid f-strings so prompt files can contain free-form text
    (including braces in JSON examples) without escaping.
    """

    output = template
    for key, value in values.items():
        token = "{{ " + key + " }}"
        output = output.replace(token, str(value))
    return output


def render_named(name: str, mapping: Mapping[str, Any]) -> str:
    return render(load_prompt(name), **dict(mapping))
