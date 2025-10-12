"""Tiny synchronous GitHub client utilities used by the CLI.

These functions intentionally avoid async and caching for simplicity.
Provide a `GITHUB_TOKEN` in your environment to increase rate limits.
"""
from typing import Any, Dict, List, Optional
import os, base64
import httpx
from dotenv import load_dotenv
load_dotenv()

GH_API = "https://api.github.com"

def _headers() -> Dict[str, str]:
    """Construct HTTP headers for GitHub API requests.

    Returns:
        Headers including Accept, API version, and Authorization if
        `GITHUB_TOKEN` is set.
    """
    h = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h

def list_user_repos(username: str, include_forks: bool = False, include_archived: bool = False) -> List[Dict[str, Any]]:
    """Return repositories owned by `username`.

    Handles pagination and can filter out forks and archived repositories.

    Args:
        username: GitHub username.
        include_forks: If False, exclude forked repositories.
        include_archived: If False, exclude archived repositories.

    Returns:
        List of repository metadata dictionaries.
    """
    results: List[Dict[str, Any]] = []
    page = 1
    with httpx.Client(timeout=20.0, headers=_headers()) as client:
        while True:
            r = client.get(
                f"{GH_API}/users/{username}/repos",
                params={"per_page": 100, "page": page, "type": "owner", "sort": "updated"},
            )
            r.raise_for_status()
            batch = r.json()
            if not batch:
                break
            for item in batch:
                if not include_forks and item.get("fork"):
                    continue
                if not include_archived and item.get("archived"):
                    continue
                results.append(item)
            page += 1
    return results

def get_languages(owner: str, repo: str) -> Dict[str, int]:
    """Return the language breakdown (in bytes) for a repository."""
    with httpx.Client(timeout=20.0, headers=_headers()) as client:
        r = client.get(f"{GH_API}/repos/{owner}/{repo}/languages")
        r.raise_for_status()
        return r.json()

def get_readme(owner: str, repo: str) -> Optional[str]:
    """Retrieve the README content for a repository as a UTF-8 string."""
    with httpx.Client(timeout=20.0, headers=_headers()) as client:
        r = client.get(f"{GH_API}/repos/{owner}/{repo}/readme")
        if r.status_code == 404:
            return None
        r.raise_for_status()
        data = r.json()
        if data.get("encoding") == "base64" and "content" in data:
            return base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
        return None
