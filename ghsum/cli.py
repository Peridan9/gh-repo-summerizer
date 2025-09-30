"""Command-line interface for ghsum.

Parses arguments, retrieves repositories via the GitHub API, and prints
summaries in JSON or Markdown. It supports a "basic" built-in summarizer
or an optional local LLM backend via Ollama.
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional
import argparse, json, os, re
from .github import list_user_repos, get_languages, get_readme
from .summarizer import get_summarizer, basic_summary, _clean_markdown
from .config import load_settings


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

def summarize_repo(owner: str, repo: dict, include_langs: bool, readme_mode: str,
                   summarizer_obj=None, summarizer_kind: str = "basic", model_name: str | None = None) -> dict:
    """Produce a per-repository summary item.

    Fetches languages and README on demand and applies either the built-in
    basic summarizer or the configured LLM summarizer.

    Args:
        owner: GitHub username.
        repo: The repository JSON object from GitHub API.
        include_langs: Whether to include the top languages list.
        readme_mode: One of "none", "excerpt", or "full".
        summarizer_obj: Optional LLM summarizer; if None, uses `basic_summary`.
        summarizer_kind: Selected summarizer kind (for logging/telemetry).
        model_name: Model name when using Ollama.

    Returns:
        A dictionary with keys like name, url, description, languages,
        readme_excerpt/readme, and summary.
    """
    name = repo["name"]
    description = repo.get("description") or ""
    item = {"name": name, "url": repo.get("html_url"), "description": description}

    if include_langs:
        from .github import get_languages
        langs = get_languages(owner, name)
        item["languages"] = _top_langs(langs)

    # readme_mode: "none" | "excerpt" | "full"
    readme_text = None
    if readme_mode != "none":
        from .github import get_readme
        r = get_readme(owner, name)
        if r:
            readme_text = _clean_markdown(r) if readme_mode == "full" else _excerpt(r)
            key = "readme" if readme_mode == "full" else "readme_excerpt"
            item[key] = readme_text

    # Build 3–5 line summary
    base_text = readme_text or description
    if base_text:
        if summarizer_obj is None:  # "basic" path
            item["summary"] = basic_summary(name, base_text, description)
        else:
            item["summary"] = summarizer_obj.summarize(name, base_text, description)

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

    Parses arguments, summarizes repositories, and prints or writes output.
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
