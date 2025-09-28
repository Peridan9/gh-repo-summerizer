# tiny, synchronous GitHub client
from typing import Any, Dict, List, Optional
import os, base64
import httpx
from dotenv import load_dotenv
load_dotenv()

GH_API = "https://api.github.com"

def _headers() -> Dict[str, str]:
    """
    Construct HTTP headers for GitHub API requests.

    Returns:
        Dict[str, str]: Headers including Accept, API version, and Authorization if GITHUB_TOKEN is set.
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
    """
    Return a list of repositories owned by the specified user.

    Handles pagination and can filter out forks and archived repositories.

    Args:
        username (str): GitHub username.
        include_forks (bool): If False, exclude forked repositories.
        include_archived (bool): If False, exclude archived repositories.

    Returns:
        List[Dict[str, Any]]: List of repository metadata dictionaries.
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
    """
    Get the language breakdown (in bytes) for a given repository.

    Args:
        owner (str): Repository owner.
        repo (str): Repository name.

    Returns:
        Dict[str, int]: Mapping of language names to byte counts.
    """
    with httpx.Client(timeout=20.0, headers=_headers()) as client:
        r = client.get(f"{GH_API}/repos/{owner}/{repo}/languages")
        r.raise_for_status()
        return r.json()

def get_readme(owner: str, repo: str) -> Optional[str]:
    """
    Retrieve the README file content for a repository.

    Args:
        owner (str): Repository owner.
        repo (str): Repository name.

    Returns:
        Optional[str]: README content as UTF-8 string, or None if not found.
    """
    with httpx.Client(timeout=20.0, headers=_headers()) as client:
        r = client.get(f"{GH_API}/repos/{owner}/{repo}/readme")
        if r.status_code == 404:
            return None
        r.raise_for_status()
        data = r.json()
        if data.get("encoding") == "base64" and "content" in data:
            return base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
        return None
