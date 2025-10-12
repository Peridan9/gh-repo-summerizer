"""GitHub repository summarizer.

A comprehensive tool for summarizing GitHub repositories using various backends.
This package can be used both as a command-line tool and as a Python SDK.

Features:
    - Multiple summarization strategies (basic, Ollama LLM)
    - GitHub API integration for repository data
    - Flexible configuration management
    - Both CLI and programmatic interfaces
    - Support for various output formats

Quick Start:
    ```python
    import ghsum
    
    # Get repositories for a user
    repos = ghsum.list_user_repos("octocat")
    
    # Generate basic summary
    summary = ghsum.basic_summary("my-repo", "README content...")
    
    # Use Ollama summarizer
    summarizer = ghsum.get_summarizer("ollama", model="llama3.2:3b")
    summary = summarizer.summarize("my-repo", "README content...")
    ```

CLI Usage:
    ```bash
    ghsum username --format json
    ghsum username --full --format md
    ghsum username --summarizer ollama --model llama3.2:3b
    ```
"""

__version__ = "0.1.0"

# Re-export main functionality for easy importing
from .core import (
    list_user_repos,
    get_languages,
    get_readme,
    get_summarizer,
    basic_summary,
    OllamaSummarizer,
    load_settings,
    Settings,
)

__all__ = [
    "list_user_repos",
    "get_languages",
    "get_readme", 
    "get_summarizer",
    "basic_summary",
    "OllamaSummarizer",
    "load_settings",
    "Settings",
]


