"""Repository summarization functionality.

This module provides various summarization strategies for GitHub repositories:
- Basic summarizer: Fast, LLM-free text extraction
- Ollama summarizer: Local LLM-powered summarization via Ollama

The module supports both simple text output and structured JSON output
with Pydantic validation for advanced use cases.

Example:
    ```python
    from ghsum.core.summarizer import get_summarizer, basic_summary
    
    # Use basic summarizer (no LLM required)
    summary = basic_summary("my-repo", "This is a great project...", "A cool tool")
    
    # Use Ollama summarizer
    summarizer = get_summarizer("ollama", model="llama3.2:3b")
    summary = summarizer.summarize("my-repo", "README content...", "Description")
    ```
"""
from __future__ import annotations
from typing import Optional, Any, List
import re
import json
from pathlib import Path
from pydantic import BaseModel, Field, validator
from langfuse import Langfuse, get_client
from langfuse.langchain import CallbackHandler
from langchain_ollama.llms import OllamaLLM
from langchain.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


def _clean_markdown(text: str) -> str:
    """Remove common markdown noise but keep the full text.
    
    Args:
        text: Raw markdown text to clean.
        
    Returns:
        Cleaned text with markdown formatting removed.
        
    Note:
        Removes images, links, code blocks, and heading markers while
        preserving the actual content.
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
    """Cap overly long inputs to keep latency reasonable.
    
    Args:
        s: Input string to potentially truncate.
        max_chars: Maximum character length before truncation.
        
    Returns:
        Original string or truncated string with truncation indicator.
    """
    return s if len(s) <= max_chars else s[:max_chars] + "\n[...truncated...]"

def build_prompt(repo_name: str, base_text: str, description: str = "") -> str:
    """Return a compact, deterministic prompt for 3–5 line summaries.
    
    Args:
        repo_name: Name of the repository.
        base_text: Main text content (usually README).
        description: Existing repository description.
        
    Returns:
        Formatted prompt string for LLM summarization.
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

def render_prompt2_from_json(json_path: str | Path) -> ChatPromptTemplate:
    """Load a ChatPromptTemplate from a JSON file (system+user messages).
    
    Args:
        json_path: Path to JSON file containing prompt configuration.
        
    Returns:
        ChatPromptTemplate object ready for use with LangChain.
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    messages = data["messages"]
    input_vars = data.get("input_variables", [])

    # Build a ChatPromptTemplate directly from the messages
    prompt = ChatPromptTemplate.from_messages(messages)
    prompt.input_variables = input_vars  # ensure vars are recognized
    return prompt

def load_prompt_template(path: str | Path) -> PromptTemplate:
    """Load a single-block PromptTemplate from a .txt file.
    
    Args:
        path: Path to the template file.
        
    Returns:
        PromptTemplate object ready for use with LangChain.
        
    Note:
        Template file should contain placeholders: {repo_name}, {description}, 
        {languages_hint}, {text}
    """
    tmpl = Path(path).read_text(encoding="utf-8")
    return PromptTemplate.from_template(tmpl)

# ---- basic (no-LLM) summarizer ---------------------------------------------

def basic_summary(repo_name: str, base_text: str, description: str = "") -> str:
    """LLM-free baseline: first useful paragraph capped to ~90 words.
    
    Args:
        repo_name: Name of the repository.
        base_text: Main text content (usually README).
        description: Existing repository description.
        
    Returns:
        Summarized text extracted from the first meaningful paragraph.
        
    Note:
        This is a fast, deterministic summarization that doesn't require
        any external services or LLM APIs.
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
    """Simple wrapper around a local Ollama server's text-generation API.
    
    This class provides LLM-powered summarization using a local Ollama server.
    It supports Langfuse integration for tracking and monitoring.
    
    Attributes:
        model: The OllamaLLM instance for text generation.
        prompt_template: Custom prompt template (if provided).
        prompt_path: Path to the default prompt template file.
    """

    def __init__(self, model: str = "llama3.2:3b",
                 base_url: str = "http://localhost:11434",
                 num_ctx: int = 8192,
                 prompt_template: str | None = None):
        """Initialize the Ollama summarizer.
        
        Args:
            model: Ollama model name to use.
            base_url: Base URL of the Ollama server.
            num_ctx: Context length for the model.
            prompt_template: Custom prompt template content.
        """
        self.model = OllamaLLM(
            model=model,
            temperature=0,
            format="json"
        )
        self.prompt_template = prompt_template
        self.prompt_path = str(Path(__file__).resolve().parents[2] / "prompts" / "protfolio_summary2.txt")

    def summarize(self, repo_name: str, base_text: str, description: str = "", langs: str = "") -> str:
        """Generate a summary using the Ollama model.
        
        Args:
            repo_name: Name of the repository.
            base_text: Main text content (usually README).
            description: Existing repository description.
            langs: Comma-separated list of programming languages.
            
        Returns:
            Generated summary text (JSON parsed if possible, raw text otherwise).
            
        Note:
            Integrates with Langfuse for tracking and monitoring.
        """
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
    """Factory that returns a summarizer object or `None` for basic mode.
    
    Args:
        kind: Type of summarizer ("basic" or "ollama").
        **kwargs: Additional arguments passed to the summarizer constructor.
        
    Returns:
        Summarizer instance or None for basic mode.
        
    Raises:
        ValueError: If an unknown summarizer kind is provided.
        
    Example:
        ```python
        # Get basic summarizer (returns None)
        summarizer = get_summarizer("basic")
        
        # Get Ollama summarizer
        summarizer = get_summarizer("ollama", model="llama3.2:3b")
        ```
    """
    kind = (kind or "basic").lower()
    if kind == "basic":
        return None  # means: use basic_summary()
    if kind == "ollama":
        return OllamaSummarizer(**kwargs)
    raise ValueError(f"Unknown summarizer kind: {kind}")
