# simple CLI that prints repo summaries, with optional JSON/Markdown output
from __future__ import annotations
from typing import Dict, Any, List, Optional
import argparse, json, os, re
from .github import list_user_repos, get_languages, get_readme
from .summarizer import get_summarizer, basic_summary, _clean_markdown

def _excerpt(text: str, word_limit: int = 500) -> str:
    """
    Extract a short summary from the first real paragraph of text.

    Strips markdown, skips image/badge lines, and limits to a number of words.

    Args:
        text (str): The input text (e.g., README content).
        word_limit (int): Maximum number of words in the excerpt.

    Returns:
        str: The summarized excerpt.
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
    """
    Return the top k languages by byte count.

    Args:
        lang_bytes (Dict[str, int]): Mapping of language names to byte counts.
        k (int): Number of top languages to return.

    Returns:
        List[str]: List of top language names.
    """
    return [name for name, _ in sorted(lang_bytes.items(), key=lambda kv: kv[1], reverse=True)[:k]]

def summarize_repo(owner: str, repo: Dict[str, Any], include_langs: bool, readme_mode: str,
                   summarizer_kind: str = "basic", model_name: str | None = None) -> Dict[str, Any]:
    name = repo["name"]
    description = repo.get("description") or ""
    item: Dict[str, Any] = {"name": name, "url": repo.get("html_url"), "description": description}

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

    # ---- NEW: produce 3–5 line summary into item["summary"] ----
    summarizer = get_summarizer(summarizer_kind, model=model_name) if summarizer_kind != "basic" else None
    base_text = readme_text or description
    if base_text:
        if summarizer is None:
            item["summary"] = basic_summary(name, base_text, description)
        else:
            item["summary"] = summarizer.summarize(name, base_text, description)

    return item

def to_markdown(items: List[Dict[str, Any]]) -> str:
    """
    Convert a list of repository summaries to Markdown format.

    Args:
        items (List[Dict[str, Any]]): List of repository summary dictionaries.

    Returns:
        str: Markdown-formatted string.
    """
    lines = []
    for it in items:
        tech = f" — _{', '.join(it.get('languages', []))}_" if it.get("languages") else ""
        desc = f": {it['readme_excerpt']}" if it.get("readme_excerpt") else (f": {it['description']}" if it.get("description") else "")
        lines.append(f"- [{it['name']}]({it['url']}){tech}{desc}")
    return "\n".join(lines)

def main() -> None:
    """
    Entry point for the CLI.

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
    
    args = p.parse_args()

    repos = list_user_repos(args.username, include_forks=args.include_forks, include_archived=args.include_archived)
    # include_langs = args.full  # keep old behavior for languages
    items = [
        summarize_repo(
            args.username, r,
            include_langs=args.full,
            readme_mode=args.readme,
            summarizer_kind=args.summarizer,
            model_name=args.model,
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
