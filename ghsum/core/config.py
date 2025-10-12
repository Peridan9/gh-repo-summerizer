"""Configuration management for ghsum.

This module handles loading and merging configuration from multiple sources:
1. Environment variables (highest priority)
2. TOML configuration file (medium priority)  
3. Default values (lowest priority)

Configuration Sources:
    - config.toml: TOML file with structured configuration
    - Environment variables: Override config file values
    - Default values: Fallback when no config is provided

Example config.toml:
    ```toml
    [summarizer]
    kind = "ollama"
    model = "llama3.2:3b"
    num_ctx = 8192

    [github]
    include_forks = false
    include_archived = false
    ```

Environment Variables:
    SUMMARIZER: Override summarizer kind
    SUMMARY_MODEL: Override model name
    SUMMARY_NUM_CTX: Override context length
    OLLAMA_BASE_URL: Override Ollama server URL
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os
import tomllib  # Python 3.11+

@dataclass
class Settings:
    """Runtime configuration derived from `config.toml` and environment.

    Values are merged with precedence: environment > config file > defaults.
    
    Attributes:
        summarizer_kind: Type of summarizer to use ("basic" or "ollama").
        model: Model name for Ollama summarizer.
        num_ctx: Context length for LLM processing.
        ollama_base_url: Base URL for Ollama server.
        prompt_template: Custom prompt template content.
        prompt_version: Version identifier for prompt templates.
        cache_dir: Directory for caching data.
        include_forks: Whether to include forked repositories.
        include_archived: Whether to include archived repositories.
    """

    # Summarizer configuration
    summarizer_kind: str = "basic"
    model: str = "llama3.2:3b"
    num_ctx: int = 8192
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    # Prompt configuration
    prompt_template: str | None = None
    prompt_version: str = "v1"

    # General configuration
    cache_dir: str = ".cache"
    include_forks: bool = False
    include_archived: bool = False

def read_file_text(path: Path | None) -> str | None:
    """Read a text file if it exists and return its contents, else None.
    
    Args:
        path: Path to the file to read.
        
    Returns:
        File contents as string, or None if file doesn't exist.
    """
    if not path:
        return None
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None

def load_config(path: str = "config.toml") -> dict:
    """Load a TOML config file into a dictionary.
    
    Args:
        path: Path to the TOML configuration file.
        
    Returns:
        Dictionary containing configuration data, or empty dict if file missing.
        
    Note:
        Uses tomllib (Python 3.11+) for TOML parsing.
    """
    p = Path(path)
    if not p.exists():
        return {}
    with p.open("rb") as f:
        return tomllib.load(f)

def load_settings(config_path: str | None = None) -> Settings:
    """Create a `Settings` object from config file and environment variables.
    
    Args:
        config_path: Path to TOML config file. Defaults to "config.toml".
        
    Returns:
        Settings object with merged configuration from all sources.
        
    Example:
        ```python
        from ghsum.core.config import load_settings
        
        # Load with default config file
        settings = load_settings()
        
        # Load with custom config file
        settings = load_settings("custom.toml")
        ```
    """
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
