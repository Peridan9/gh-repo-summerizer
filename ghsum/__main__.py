# ghsum/__main__.py
"""Module entrypoint for `python -m ghsum`.

Prefer using the installed console script `ghsum`. This module simply forwards
to the same `main()` function.
"""

try:
    from .cli import main
except ImportError:
    # Fallback if Python didn’t treat us as a package for some reason.
    from ghsum.cli import main

if __name__ == "__main__":
    main()
