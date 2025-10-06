from __future__ import annotations
from typing import Optional, Any, List
import httpx
import os
import re
import json
from pydantic import BaseModel, Field, validator
from langfuse import get_client

_langfuse = get_client()

# Pydantic models for structured output
class RepositorySummary(BaseModel):
    """Structured summary of a repository."""
    
    name: str = Field(description="Repository name")
    description: str = Field(description="What the repository does (1-2 sentences)")
    purpose: str = Field(description="Primary purpose or use case")
    technologies: List[str] = Field(description="Key technologies used (max 5)")
    complexity: str = Field(default="medium", description="Complexity level: simple, medium, complex")
    target_audience: str = Field(default="developers", description="Who would use this")
    
    @validator('technologies')
    def validate_technologies(cls, v):
        """Ensure technologies list is reasonable."""
        if len(v) > 5:
            raise ValueError("Too many technologies listed")
        return [tech.lower().strip() for tech in v if tech.strip()]
    
    @validator('complexity')
    def validate_complexity(cls, v):
        """Ensure complexity is one of the allowed values."""
        allowed = ['simple', 'medium', 'complex']
        if v.lower() not in allowed:
            raise ValueError(f"Complexity must be one of: {allowed}")
        return v.lower()

def render_prompt(template: str | None, repo_name: str, base_text: str, description: str, langs: str) -> str:
    """Render the final prompt string for an LLM summarizer.

    If an external template is provided, use it with simple `.format()`
    placeholders. Otherwise, fall back to the built-in deterministic
    `build_prompt()`.
    """
    if template:
        # simple Python format placeholders
        return template.format(repo_name=repo_name, text=_cap(_clean_markdown(base_text or "")), description=description or "", languages_hint=langs or"")
    # fallback to the built-in prompt
    return build_prompt(repo_name, base_text, description)

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

def build_structured_prompt(repo_name: str, base_text: str, description: str = "", langs: str = "") -> str:
    """Build a prompt that requests structured JSON output."""
    
    schema_example = {
        "name": "example-repo",
        "description": "A tool for managing database migrations",
        "purpose": "Simplify database schema changes across environments",
        "technologies": ["python", "sqlalchemy", "postgresql"],
        "complexity": "medium",
        "target_audience": "backend developers"
    }
    
    return f"""
You are a technical writer. Analyze this repository and provide a structured summary.

CRITICAL: Respond with ONLY valid JSON matching this exact schema:
{json.dumps(schema_example, indent=2)}

Repository name: {repo_name}
Existing description: {description or "None"}
Languages detected: {langs or "None"}

Source text:
{_cap(_clean_markdown(base_text or ""))}

Instructions:
- Be factual and only use information from the provided text
- Keep description to 1-2 sentences
- List only technologies explicitly mentioned
- Choose complexity: simple (basic scripts), medium (applications), complex (systems)
- Be conservative with technology claims

Respond with valid JSON only:
"""

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
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.num_ctx = int(num_ctx)
        self.prompt_template = prompt_template

    def summarize(self, repo_name: str, base_text: str, description: str = "", langs: str = "") -> str:
        prompt = render_prompt(self.prompt_template, repo_name, base_text, description, langs)
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_ctx": self.num_ctx,
                "temperature": 0.1,
                "top_p": 0.9,
                "repeat_penalty": 1.1,
            },
        }

        # --- Langfuse tracing ---
        lf = _langfuse
        # Root span for this repo summarization
        with lf.start_as_current_span(
            name="ghsum.summarize",
            input={
                "repo_name": repo_name,
                "readme": base_text,
                "description": description,
                "languages_hint": langs,
            },
            metadata={"provider": "ollama"},
        ) as root:

            # Attach useful trace attributes (optional)
            root.update_trace(tags=["ghsum", "summarize"], metadata={"repo": repo_name})

            # Child "generation" for the actual LLM call
            with lf.start_as_current_generation(
                name="ollama.generate",
                model=self.model,
                input=[{"role": "user", "content": prompt}],
                model_parameters=payload.get("options", {}),
            ) as gen:
                try:
                    with httpx.Client(timeout=90.0) as client:
                        r = client.post(f"{self.base_url}/api/generate", json=payload)
                        r.raise_for_status()
                        data = r.json()
                        response_text = (data.get("response") or "").strip()

                        # record output (+ any usage data you compute)
                        gen.update(output=response_text)
                except Exception as e:
                    # mark generation as failed
                    gen.update(output={"error": str(e)})
                    raise

            # set root output with a short preview (keep UI clean)
            root.update(output={"preview": response_text[:200]})

        return response_text

    def summarize_structured(self, repo_name: str, base_text: str, description: str = "", langs: str = "") -> RepositorySummary:
        """Generate a structured summary using Pydantic validation."""
        prompt = build_structured_prompt(repo_name, base_text, description, langs)
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_ctx": self.num_ctx,
                "temperature": 0.1,      # Lower temperature for consistency
                "top_p": 0.9,
                "repeat_penalty": 1.1,
            },
        }
        
        try:
            with httpx.Client(timeout=90.0) as client:
                r = client.post(f"{self.base_url}/api/generate", json=payload)
                r.raise_for_status()
                data = r.json()
                response_text = data.get("response", "").strip()
                
                # Try to extract JSON from response
                try:
                    # Look for JSON in the response
                    json_start = response_text.find('{')
                    json_end = response_text.rfind('}') + 1
                    if json_start != -1 and json_end > json_start:
                        json_text = response_text[json_start:json_end]
                        json_data = json.loads(json_text)
                        return RepositorySummary(**json_data)
                    else:
                        raise ValueError("No JSON found in response")
                except (json.JSONDecodeError, ValueError, TypeError) as e:
                    # Fallback to basic summary if structured parsing fails
                    print(f"Warning: Failed to parse structured response: {e}")
                    return RepositorySummary(
                        name=repo_name,
                        description=description or "Repository summary",
                        purpose="Software project",
                        technologies=[],
                        complexity="medium",
                        target_audience="developers"
                    )
        except Exception as e:
            print(f"Warning: Summarization failed: {e}")
            return RepositorySummary(
                name=repo_name,
                description=description or "Repository summary",
                purpose="Software project", 
                technologies=[],
                complexity="medium",
                target_audience="developers"
            )

# ---- factory ----------------------------------------------------------------

def get_summarizer(kind: str, **kwargs) -> Any:
    """Factory that returns a summarizer object or `None` for basic mode."""
    kind = (kind or "basic").lower()
    if kind == "basic":
        return None  # means: use basic_summary()
    if kind == "ollama":
        return OllamaSummarizer(**kwargs)
    raise ValueError(f"Unknown summarizer kind: {kind}")