# ghsum – GitHub Repository Summarizer

`ghsum` is a small CLI that lists repositories for a GitHub user and produces concise summaries. It can output JSON or Markdown, and supports a fast built‑in summarizer (no LLM) or a local LLM via Ollama.

## Features
- Summarize all repos for a GitHub user
- Output as JSON or Markdown
- Optional README excerpt or full README inclusion
- Language highlights (top languages)
- Two summary modes:
  - Basic: deterministic, no LLM, zero network beyond GitHub API
  - Ollama: use your local model (e.g., `llama3.2:3b`)

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

Run tests (if/when added):
```bash
uv run pytest -q
```

## License

MIT
