# ghsum/__main__.py
try:
    from .cli import main
except ImportError:
    # Fallback if Python didn’t treat us as a package for some reason
    from ghsum.cli import main

if __name__ == "__main__":
    main()
