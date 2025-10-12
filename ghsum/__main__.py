"""Module entrypoint for `python -m ghsum`.

This module enables running ghsum as a Python module using `python -m ghsum`.
It forwards to the same main() function as the console script.

Usage:
    ```bash
    # Run as module (equivalent to 'ghsum' command)
    python -m ghsum username --format json
    
    # With full options
    python -m ghsum username --full --format md --summarizer ollama
    ```

Note:
    Prefer using the installed console script `ghsum` when available,
    as it's more convenient and doesn't require Python module syntax.
"""

try:
    from .cli import main
except ImportError:
    # Fallback if Python didn’t treat us as a package for some reason.
    from ghsum.cli import main

if __name__ == "__main__":
    main()
