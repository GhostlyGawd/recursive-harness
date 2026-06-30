"""`python -m fleet` → the Agent Mail CLI (mirrors mission_control/__main__.py)."""
import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
