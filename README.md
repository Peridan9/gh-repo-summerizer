# ghsum – GitHub Repository Summarizer

A small CLI and Python SDK to generate short, readable summaries for GitHub repositories.
Works with a no-LLM fallback (deterministic) or a local Ollama model.

Quick start
1. install
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

2. CLI examples (replace USERNAME with your GitHub user)
- Summarize a user and print JSON to stdout:
```bash
ghsum USERNAME
```
- Markdown output including languages and README excerpt:
```bash
ghsum USERNAME --full --format md
```
- Save JSON to a file:
```bash
ghsum USERNAME --out out/repos.json
```
- Run via uv (developer convenience):
```bash
uv run -m ghsum USERNAME --full --readme full --summarizer ollama
```

Python SDK usage
```python
import ghsum

repos = ghsum.list_user_repos("USERNAME")
summary = ghsum.basic_summary("my-repo", "README content...")
summarizer = ghsum.get_summarizer("ollama", model="llama3.2:3b")
print(summarizer.summarize("my-repo", "README content..."))
```

Summarizers — note on quality
- basic: a minimal, deterministic fallback that simply extracts the first paragraph. It is intentionally simple and low-cost, but the output quality is limited — do not rely on it for public-facing summaries.
- ollama: uses a local LLM (better quality). Recommended when you need good summaries and have an Ollama model available.

Options (CLI)
```bash
ghsum USERNAME [--full] [--format json|md] [--out PATH]
             [--include-forks] [--include-archived]
             [--readme none|excerpt|full]
             [--summarizer basic|ollama] [--model NAME]
             [--config PATH]
```

Configuration
`config.toml` lets you set defaults. Example:
```toml
[summarizer]
kind = "ollama"         # "basic" | "ollama"
model = "llama3.2:3b"
num_ctx = 8192

[prompt]
template_file = "prompts/portfolio_summary.txt"

[cache]
dir = ".cache"

[github]
include_forks = false
include_archived = false
```

Environment variables override config where applicable:
- `GITHUB_TOKEN` — GitHub API token for higher rate limits
- `OLLAMA_BASE_URL` — Ollama server URL (default `http://localhost:11434`)
- `LANGFUSE_*` — Langfuse tracing keys (optional)

Prompt customization
If `prompt.template_file` is set, placeholders available are:
- `{repo_name}`
- `{description}`
- `{text}` (cleaned README or description)

Output examples

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

Development notes
- There are currently no automated tests included. If you add unit tests, use `pytest`.
- Use a feature branch for larger changes and run the CLI locally with `uv run -m ghsum ...` to validate.

Project layout (brief)
```
ghsum/                      # top-level package
├── __main__.py              # CLI entrypoint (python -m ghsum)
├── __init__.py              # SDK-friendly exports (light facade)
├── cli/
│   └── main.py              # CLI argument parsing and invocation
├── core/
│   ├── __init__.py          # public core exports (get_summarizer, basic_summary, ...)
│   ├── github.py            # GitHub API helpers (list_user_repos, get_readme, ...)
│   ├── summarizer.py        # Summarizer implementations (basic, Ollama/LangChain, parsers)
│   └── config.py            # config loading and Settings dataclass
└── prompts/                  # customizable prompt templates (important)
    └── portfolio_summary.txt # default prompt template used by summarizers
```

License
MIT
