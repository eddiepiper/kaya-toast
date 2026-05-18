from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)
    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML mapping in {path}")
    return data


def load_taxonomy(config_dir: Path = CONFIG_DIR) -> dict[str, Any]:
    return load_yaml(config_dir / "taxonomy.yaml")


def load_scoring(config_dir: Path = CONFIG_DIR) -> dict[str, Any]:
    return load_yaml(config_dir / "scoring.yaml")


def load_preferences(config_dir: Path = CONFIG_DIR) -> dict[str, Any]:
    return load_yaml(config_dir / "preferences.yaml")


def load_sources(config_dir: Path = CONFIG_DIR) -> dict[str, Any]:
    return load_yaml(config_dir / "sources.yaml")


def load_llm(config_dir: Path = CONFIG_DIR) -> dict[str, Any]:
    return load_yaml(config_dir / "llm.yaml")


def load_all_config(config_dir: Path = CONFIG_DIR) -> dict[str, dict[str, Any]]:
    return {
        "taxonomy": load_taxonomy(config_dir),
        "scoring": load_scoring(config_dir),
        "preferences": load_preferences(config_dir),
        "sources": load_sources(config_dir),
        "llm": load_llm(config_dir),
    }
