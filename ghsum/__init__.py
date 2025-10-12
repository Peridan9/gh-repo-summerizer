"""GitHub repository summarizer.

A tool for summarizing GitHub repositories using various backends.
Can be used as a CLI tool or imported as an SDK.
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


