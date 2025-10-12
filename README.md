# ghsum – GitHub Repository Summarizer

`ghsum` is a comprehensive tool for summarizing GitHub repositories that can be used both as a command-line tool and as a Python SDK. It supports multiple summarization backends and flexible output formats.

## Architecture

The project is organized into two main modules:
- **`ghsum/core/`**: Core business logic (GitHub API, summarization, configuration)
- **`ghsum/cli/`**: Command-line interface implementation

This structure enables both CLI usage and SDK integration in your Python projects.

## Features

### CLI Tool
- Summarize all repos for a GitHub user
- Output as JSON or Markdown
- Optional README excerpt or full README inclusion
- Language highlights (top languages)
- Two summary modes:
  - Basic: deterministic, no LLM, zero network beyond GitHub API
  - Ollama: use your local model (e.g., `llama3.2:3b`)

### Python SDK
- Import and use core functionality in your Python projects
- Access GitHub API utilities directly
- Use summarization backends programmatically
- Flexible configuration management

## Installation

Prereqs: Python 3.12+, `uv` or `pip`.

Using uv (recommended):
```bash
uv sync
uv run ghsum --help
```

Using pip:
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
ghsum --help
```

## Quick start

### CLI Usage

Summarize a user and print JSON to stdout:
```bash
ghsum octocat
```

Markdown output with languages and README excerpt:
```bash
ghsum octocat --full --format md
```

Write JSON to a file:
```bash
ghsum octocat --out out/repos.json
```

### Python SDK Usage

```python
import ghsum

# Get repositories for a user
repos = ghsum.list_user_repos("octocat")

# Generate basic summary
summary = ghsum.basic_summary("my-repo", "README content...")

# Use Ollama summarizer
summarizer = ghsum.get_summarizer("ollama", model="llama3.2:3b")
summary = summarizer.summarize("my-repo", "README content...")

# Load configuration
settings = ghsum.load_settings("config.toml")
```

## Options

```bash
ghsum USERNAME [--full] [--format json|md] [--out PATH]
             [--include-forks] [--include-archived]
             [--readme none|excerpt|full]
             [--summarizer basic|ollama] [--model NAME]
             [--config PATH]
```

- `--full`: Include top languages and README excerpt.
- `--format`: `json` (default) or `md`.
- `--out`: Write results to a file.
- `--include-forks`, `--include-archived`: Include those repositories.
- `--readme`: `none` (default), `excerpt`, or `full`.
- `--summarizer`: `basic` (no LLM) or `ollama` (local model).
- `--model`: Ollama model name, e.g., `llama3.2:3b`.
- `--config`: Path to a TOML config file (defaults to `./config.toml` if present).

## Configuration

`config.toml` allows you to set defaults. Example:

```toml
[summarizer]
kind = "ollama"         # "basic" | "ollama"
model = "llama3.2:3b"
num_ctx = 8192

[prompt]
template_file = "prompts/portfolio_summary.txt"
version = "v1"

[cache]
dir = ".cache"

[github]
include_forks = false
include_archived = false
```

Environment variables override config values where applicable:
- `GITHUB_TOKEN`: Auth token for higher GitHub API rate limits.
- `OLLAMA_BASE_URL`: Base URL for local Ollama server (default `http://localhost:11434`).
- `SUMMARIZER`, `SUMMARY_MODEL`, `SUMMARY_NUM_CTX`: Override summarizer defaults.

## Prompt customization

If you provide a `prompt.template_file` in `config.toml`, it will be used with placeholders:
- `{repo_name}`
- `{description}`
- `{text}` (cleaned README or description)

See `prompts/portfolio_summary.txt` for a default template.

## Output examples

Markdown:
```md
- [ghsum](https://github.com/you/ghsum) — _Python_ : A small CLI to summarize repos...
```

JSON:
```json
[
  {
    "name": "ghsum",
    "url": "https://github.com/you/ghsum",
    "languages": ["Python", "Shell"],
    "readme_excerpt": "...",
    "summary": "..."
  }
]
```

## Development

Run locally with uv:
```bash
uv run ghsum octocat --full --format md
```

### Project Structure

```
ghsum/
├── __init__.py          # Main package with SDK exports
├── __main__.py          # Module entry point (python -m ghsum)
├── cli/                 # CLI functionality
│   ├── __init__.py
│   └── main.py          # CLI main function
└── core/                # Core business logic (SDK)
    ├── __init__.py
    ├── config.py        # Configuration management
    ├── github.py        # GitHub API interactions
    └── summarizer.py    # Repository summarization
```

### SDK Development

The core module is designed for easy integration:

```python
from ghsum.core import list_user_repos, get_summarizer, basic_summary

# Direct core imports for advanced usage
repos = list_user_repos("username", include_forks=False)
summarizer = get_summarizer("ollama", model="llama3.2:3b")
```

## License

MIT
