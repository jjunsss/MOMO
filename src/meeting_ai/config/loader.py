"""Load YAML or JSON configuration files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import yaml

from meeting_ai.config.defaults import (
    default_models_config,
    default_pipeline_config,
    default_user_profile,
)


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_mapping(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        data = yaml.safe_load(text) or {}
    if not isinstance(data, dict):
        raise ValueError("config file must contain a mapping: {0}".format(path))
    return data


def load_user_profile(path: Path) -> Dict[str, Any]:
    return _deep_merge(default_user_profile(), load_mapping(path))


def load_pipeline_config(path: Path) -> Dict[str, Any]:
    return _deep_merge(default_pipeline_config(), load_mapping(path))


def load_models_config(path: Path) -> Dict[str, Any]:
    return _deep_merge(default_models_config(), load_mapping(path))
