"""Allow ``python -m cairn`` as an entry point, mirroring the ``cairn`` script."""

from __future__ import annotations

from .cli.app import main

if __name__ == "__main__":
    main()
