"""Command-line interface for ghsum.

This module provides the main CLI functionality for GitHub repository summarization.
It parses command-line arguments, retrieves repositories via the GitHub API, and
outputs summaries in JSON or Markdown format.

Features:
    - Multiple summarization backends (basic, Ollama)
    - Flexible output formats (JSON, Markdown)
    - Repository filtering (forks, archived)
    - README content inclusion options
    - Configuration file support

Usage:
    ```bash
    # Basic usage
    ghsum username
    
    # With full details and Markdown output
    ghsum username --full --format md
    
    # Using Ollama summarizer
    ghsum username --summarizer ollama --model llama3.2:3b
    ```

Configuration:
    The CLI supports configuration via:
    - Command-line arguments (highest priority)
    - Environment variables
    - config.toml file (lowest priority)
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional
import argparse, json, os, re
from ..core.github import list_user_repos, get_languages, get_readme
from ..core.summarizer import get_summarizer, basic_summary, _clean_markdown
from ..core.config import load_settings


def _excerpt(text: str, word_limit: int = 500) -> str:
    """Return a short excerpt from the first real paragraph of `text`.

    This function lightly cleans markdown, skips image/badge lines, and
    truncates to a target number of words. It is intentionally simple and
    deterministic to keep the CLI fast and predictable.

    Args:
        text: The input text (e.g., README content).
        word_limit: Maximum number of words in the excerpt.

    Returns:
        A summarized excerpt string.
    """
    # skip image/badge lines
    lines = [ln for ln in text.splitlines() if not re.search(r"!\[.*\]\(.*\)", ln)]
    # find first non-empty paragraph
    para = []
    for ln in lines:
        if ln.strip():
            para.append(ln)
        elif para:
            break
    raw = " ".join(para) if para else text
    # strip markdown links/code fences (very light)
    raw = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", raw)
    raw = re.sub(r"`{1,3}.*?`{1,3}", "", raw)
    raw = re.sub(r"#+\s*", "", raw)  # headings
    words = raw.split()
    return " ".join(words[:word_limit]).strip()


def _top_langs(lang_bytes: Dict[str, int], k: int = 3) -> List[str]:
    """Return the top `k` languages by byte count.

    Args:
        lang_bytes: Mapping of language names to byte counts.
        k: Number of top languages to return.

    Returns:
        A list of top language names.
    """
    return [name for name, _ in sorted(lang_bytes.items(), key=lambda kv: kv[1], reverse=True)[:k]]

def summarize_repo(
        owner: str,
        repo: dict, 
        include_langs: bool, 
        readme_mode: str,
        summarizer_obj=None, 
        summarizer_kind: str = "basic", 
        model_name: str | None = None, 
        use_structured: bool = False) -> dict:
    """Produce a per-repository summary item.
    
    Args:
        owner: Repository owner (username or organization).
        repo: Repository metadata dictionary from GitHub API.
        include_langs: Whether to include programming languages.
        readme_mode: README inclusion mode ("none", "excerpt", "full").
        summarizer_obj: Summarizer instance (None for basic mode).
        summarizer_kind: Type of summarizer being used.
        model_name: Model name for logging purposes.
        use_structured: Whether to use structured output (requires LLM).
        
    Returns:
        Dictionary containing repository summary with keys:
        - name: Repository name
        - url: Repository URL
        - description: Repository description
        - languages: List of top languages (if include_langs=True)
        - readme/readme_excerpt: README content (if readme_mode != "none")
        - summary: Generated summary text
        - structured: Structured output data (if use_structured=True)
    """
    name = repo["name"]
    description = repo.get("description") or ""
    item = {"name": name, "url": repo.get("html_url"), "description": description}

    if include_langs:
        from ..core.github import get_languages
        langs = get_languages(owner, name)
        item["languages"] = _top_langs(langs)

    # readme_mode: "none" | "excerpt" | "full"
    readme_text = None
    if readme_mode != "none":
        from ..core.github import get_readme
        r = get_readme(owner, name)
        if r:
            readme_text = _clean_markdown(r) if readme_mode == "full" else _excerpt(r)
            key = "readme" if readme_mode == "full" else "readme_excerpt"
            item[key] = readme_text

    # Build summary
    base_text = readme_text or description
    if base_text:
        if summarizer_obj is None:  # "basic" path
            item["summary"] = basic_summary(name, readme_text, description)
        else:
            langs_str = ", ".join(item.get("languages", []))
            if use_structured and hasattr(summarizer_obj, 'summarize_structured'):
                # Use structured output
                structured = summarizer_obj.summarize_structured(name, readme_text, description, langs_str)
                item["summary"] = structured.description
                item["structured"] = structured.dict()
            else:
                # Use regular text output
                item["summary"] = summarizer_obj.summarize(name, readme_text, description, langs_str)

    return item

def to_markdown(items: List[Dict[str, Any]]) -> str:
    """Convert a list of repository summaries to Markdown format.

    Args:
        items: List of repository summary dictionaries.

    Returns:
        A Markdown-formatted string.
    """
    lines = []
    for it in items:
        tech = f" — _{', '.join(it.get('languages', []))}_" if it.get("languages") else ""
        desc = f": {it['readme_excerpt']}" if it.get("readme_excerpt") else (f": {it['description']}" if it.get("description") else "")
        lines.append(f"- [{it['name']}]({it['url']}){tech}{desc}")
    return "\n".join(lines)

def main() -> None:
    """Entry point for the CLI.

    Parses command-line arguments, loads configuration, retrieves repositories
    from GitHub, generates summaries, and outputs results in the requested format.
    
    The function handles:
    - Argument parsing and validation
    - Configuration loading (CLI > env > config file)
    - Repository data retrieval from GitHub API
    - Summary generation using selected backend
    - Output formatting (JSON or Markdown)
    - File writing or stdout output
    
    Raises:
        SystemExit: On argument parsing errors or API failures.
    """
    p = argparse.ArgumentParser(prog="ghsum", description="Summarize a GitHub profile's repos.")

    p.add_argument("username", help="GitHub username (owner)")
    p.add_argument("--full", action="store_true", help="Include languages and README excerpt")
    p.add_argument("--format", choices=["json", "md"], default="json", help="Output format")
    p.add_argument("--out", help="Write to file instead of stdout")
    p.add_argument("--include-forks", action="store_true", help="Include forked repos")
    p.add_argument("--include-archived", action="store_true", help="Include archived repos")
    p.add_argument(
        "--readme",
        choices=["none", "excerpt", "full"],
        default="excerpt" if "--full" in os.sys.argv else "none",
        help="Include README: 'none' (skip), 'excerpt' (default), or 'full'."
    )
    p.add_argument("--summarizer", choices=["basic", "ollama"], default="basic",
               help="Summary engine. 'basic' (no LLM) or 'ollama' (local).")
    p.add_argument("--model", default="llama3.2:3b",
               help="Model name for ollama (default: llama3.2:3b). Ignored for basic.")
    p.add_argument("--structured", action="store_true", 
               help="Use structured output with Pydantic validation (requires ollama).")
    p.add_argument("--config", help="Path to config.toml (defaults to ./config.toml if present)")

    args = p.parse_args()

    # Load config.toml (if present) + env defaults
    s = load_settings(args.config or "config.toml")

    # Effective settings (CLI > env/config > code defaults)
    summarizer_kind = args.summarizer or s.summarizer_kind
    model_name = args.model or s.model
    num_ctx = s.num_ctx
    base_url = s.ollama_base_url
    prompt_template = s.prompt_template

    summarizer_obj = None
    if summarizer_kind != "basic":
        summarizer_obj = get_summarizer(
            summarizer_kind,
            model=model_name,
            num_ctx=num_ctx,
            base_url=base_url,
            prompt_template=prompt_template,
        )

    # Readme mode and flags remain from your CLI (args.readme, args.full, etc.)

    repos = list_user_repos(args.username, include_forks=args.include_forks, include_archived=args.include_archived)

    items = [
        summarize_repo(
            args.username, r,
            include_langs=args.full,
            readme_mode=args.readme,
            summarizer_obj=summarizer_obj,
            summarizer_kind=summarizer_kind,
            model_name=model_name,
            use_structured=args.structured,
        )
        for r in repos
    ]

    if args.format == "json":
        payload = json.dumps(items, ensure_ascii=False, indent=2)
    else:
        payload = to_markdown(items)

    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(payload)
        print(f"wrote {args.out} ({len(items)} repos)")
    else:
        print(payload)

if __name__ == "__main__":
    main()
