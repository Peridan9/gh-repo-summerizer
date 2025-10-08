from __future__ import annotations
from typing import Optional, Any, List
import re
import json
from pathlib import Path
from pydantic import BaseModel, Field, validator
from langfuse import Langfuse, get_client
from langfuse.langchain import CallbackHandler
from langchain_ollama.llms import OllamaLLM
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser


def _clean_markdown(text: str) -> str:
    """Remove common markdown noise but keep the full text."""
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
    """Return a compact, deterministic prompt for 3–5 line summaries."""

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

def render_prompt2_from_json(json_path: str | Path) -> ChatPromptTemplate:
    """Load a ChatPromptTemplate from a JSON file (system+user messages)."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    messages = data["messages"]
    input_vars = data.get("input_variables", [])

    # Build a ChatPromptTemplate directly from the messages

    prompt = ChatPromptTemplate.from_messages(messages)
    prompt.input_variables = input_vars  # ensure vars are recognized
    return prompt

def load_prompt_template(path: str | Path) -> PromptTemplate:
    """Load a single-block PromptTemplate from a .txt file."""
    tmpl = Path(path).read_text(encoding="utf-8")
    # NOTE: your file uses placeholders: {repo_name}, {description}, {languages_hint}, {text}
    return PromptTemplate.from_template(tmpl)

# ---- basic (no-LLM) summarizer ---------------------------------------------

def basic_summary(repo_name: str, base_text: str, description: str = "") -> str:
    """LLM-free baseline: first useful paragraph capped to ~90 words."""
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
    """Simple wrapper around a local Ollama server's text-generation API."""

    def __init__(self, model: str = "llama3.2:3b",
                 base_url: str = "http://localhost:11434",
                 num_ctx: int = 8192,
                 prompt_template: str | None = None):

        self.model = OllamaLLM(
            model=model,
            temperature=0.1,
            format="json"
        )
        self.prompt_template = prompt_template
        self.prompt_path = str(Path(__file__).resolve().parents[1] / "prompts" / "protfolio_summary2.txt")

    def summarize(self, repo_name: str, base_text: str, description: str = "", langs: str = "") -> str:

        prompt = load_prompt_template(self.prompt_path)

        inputs = {
            "repo_name": repo_name,
            "cleaned_text": _cap(base_text or ""),
            "description": description or "",
            "languages_hint": langs or ""
        }

        langfuse = get_client()
        langfuse_handler = CallbackHandler()
        
        chain = prompt | self.model | StrOutputParser()
        response = chain.invoke(inputs, config={"callbacks": [langfuse_handler]})
        
        langfuse.flush()
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return response



# ---- factory ----------------------------------------------------------------

def get_summarizer(kind: str, **kwargs) -> Any:
    """Factory that returns a summarizer object or `None` for basic mode."""
    kind = (kind or "basic").lower()
    if kind == "basic":
        return None  # means: use basic_summary()
    if kind == "ollama":
        return OllamaSummarizer(**kwargs)
    raise ValueError(f"Unknown summarizer kind: {kind}")