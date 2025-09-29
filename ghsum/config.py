# src/ghsum/config.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os
import tomllib  # Python 3.11+

# If you're using python-dotenv already, it will be loaded elsewhere (github.py).
# This module just reads config.toml and merges env & CLI defaults.

@dataclass
class Settings:
    # summarizer
    summarizer_kind: str = "basic"
    model: str = "llama3.2:3b"
    num_ctx: int = 8192
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    # prompt
    prompt_template: str | None = None
    prompt_version: str = "v1"

    # misc
    cache_dir: str = ".cache"
    include_forks: bool = False
    include_archived: bool = False

def read_file_text(path: Path | None) -> str | None:
    if not path:
        return None
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None

def load_config(path: str = "config.toml") -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    with p.open("rb") as f:
        return tomllib.load(f)

def load_settings(config_path: str | None = None) -> Settings:
    cfg = load_config(config_path or "config.toml")

    s = Settings()

    # summarizer section
    summ = cfg.get("summarizer", {})
    s.summarizer_kind = os.getenv("SUMMARIZER", summ.get("kind", s.summarizer_kind))
    s.model = os.getenv("SUMMARY_MODEL", summ.get("model", s.model))
    s.num_ctx = int(os.getenv("SUMMARY_NUM_CTX", summ.get("num_ctx", s.num_ctx)))
    s.ollama_base_url = os.getenv("OLLAMA_BASE_URL", s.ollama_base_url)

    # prompt section
    pr = cfg.get("prompt", {})
    s.prompt_version = pr.get("version", s.prompt_version)
    tmpl_path = pr.get("template_file")
    s.prompt_template = read_file_text(Path(tmpl_path)) if tmpl_path else None

    # cache section
    ch = cfg.get("cache", {})
    s.cache_dir = ch.get("dir", s.cache_dir)

    # github defaults
    gh = cfg.get("github", {})
    s.include_forks = gh.get("include_forks", s.include_forks)
    s.include_archived = gh.get("include_archived", s.include_archived)

    return s
