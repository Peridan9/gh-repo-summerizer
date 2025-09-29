from __future__ import annotations
from typing import Optional, Any
import httpx
import os
import re

def render_prompt(template: str | None, repo_name: str, base_text: str, description: str) -> str:
    if template:
        # simple Python format placeholders
        return template.format(repo_name=repo_name, text=_cap(_clean_markdown(base_text or "")), description=description or "")
    # fallback to the built-in prompt
    return build_prompt(repo_name, base_text, description)

def _clean_markdown(text: str) -> str:
    """
    Remove common markdown noise but keep the full text.

    Args:
        text (str): The input markdown text.

    Returns:
        str: The cleaned text without markdown.
    """
    lines = [ln for ln in text.splitlines() if not re.search(r"!\[.*\]\(.*\)", ln)]
    raw = "\n".join(lines)
    # [text](url) -> text
    raw = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", raw)
    # strip code fences and inline code
    raw = re.sub(r"`{3}.*?`{3}", "", raw, flags=re.S)
    raw = re.sub(r"`([^`]+)`", r"\1", raw)
    # strip leading hashes in headings (keep the heading text)
    raw = re.sub(r"^\s*#+\s*", "", raw, flags=re.M)
    return raw.strip()


def _cap(s: str, max_chars: int = 12000) -> str:
    """Cap overly long inputs to keep latency reasonable."""
    return s if len(s) <= max_chars else s[:max_chars] + "\n[...truncated...]"

def build_prompt(repo_name: str, base_text: str, description: str = "") -> str:
    """
    A compact, deterministic prompt for portfolio/resume summaries (3–5 lines).
    """
    cleaned = _clean_markdown(base_text or "")
    cleaned = _cap(cleaned)
    return f"""
You are a concise technical writer. Summarize this repository for a personal site / resume.

Constraints:
- 3–5 lines (60–120 words total).
- Explain WHAT it does, HOW at a high level, and key TECH.
- Neutral technical tone. No hype/emojis/markdown.

Repository name: {repo_name}
Existing one-line description (may be empty): {description}

Text:
{cleaned}
""".strip()

# ---- basic (no-LLM) summarizer ---------------------------------------------

def basic_summary(repo_name: str, base_text: str, description: str = "") -> str:
    """
    LLM-free baseline: take first useful paragraph and cap to ~90 words.
    """
    text = base_text.strip() or description.strip() or repo_name
    text = _clean_markdown(text)
    # pick first non-empty paragraph
    para = []
    for ln in text.splitlines():
        if ln.strip():
            para.append(ln.strip())
        elif para:
            break
    raw = " ".join(para) if para else text
    words = raw.split()
    return " ".join(words[:90]).strip()

# ---- Ollama (local) summarizer ---------------------------------------------

class OllamaSummarizer:
    def __init__(self, model: str = "llama3.2:3b",
                 base_url: str = "http://localhost:11434",
                 num_ctx: int = 8192,
                 prompt_template: str | None = None):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.num_ctx = int(num_ctx)
        self.prompt_template = prompt_template

    def summarize(self, repo_name: str, base_text: str, description: str = "") -> str:
        prompt = render_prompt(self.prompt_template, repo_name, base_text, description)
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_ctx": self.num_ctx},
        }
        with httpx.Client(timeout=90.0) as client:
            r = client.post(f"{self.base_url}/api/generate", json=payload)
            r.raise_for_status()
            data = r.json()
            return (data.get("response") or "").strip()

# ---- factory ----------------------------------------------------------------

def get_summarizer(kind: str, **kwargs) -> Any:
    kind = (kind or "basic").lower()
    if kind == "basic":
        return None  # means: use basic_summary()
    if kind == "ollama":
        return OllamaSummarizer(**kwargs)
    raise ValueError(f"Unknown summarizer kind: {kind}")