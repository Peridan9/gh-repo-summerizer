# simple CLI that prints repo summaries, with optional JSON/Markdown output
from __future__ import annotations
from typing import Dict, Any, List, Optional
import argparse, json, os, re
from .github import list_user_repos, get_languages, get_readme

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

def summarize_repo(owner: str, repo: Dict[str, Any], include_langs: bool, readme_mode: str) -> Dict[str, Any]:
    name = repo["name"]
    item: Dict[str, Any] = {
        "name": name,
        "url": repo.get("html_url"),
        "description": repo.get("description") or "",
    }

    if include_langs:
        langs = get_languages(owner, name)
        item["languages"] = _top_langs(langs)

    if readme_mode != "none":
        readme = get_readme(owner, name)
        if readme:
            if readme_mode == "full":
                item["readme"] = _clean_markdown(readme)   # <-- full text
            else:
                item["readme_excerpt"] = _excerpt(readme)  # <-- first paragraph

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
    args = p.parse_args()

    repos = list_user_repos(args.username, include_forks=args.include_forks, include_archived=args.include_archived)
    include_langs = args.full  # keep old behavior for languages
    items = [
        summarize_repo(args.username, r, include_langs=include_langs, readme_mode=args.readme)
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
