"""KdenShorts root executable script."""

import sys
from pathlib import Path

# Ensure root repository directory is discoverable on sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Bootstrap environment and auto-install any missing dependencies before importing CLI
from clip_harvester.bootstrap import ensure_environment

if __name__ == "__main__":
    ensure_environment()
    from clip_harvester.cli import main

    main()
