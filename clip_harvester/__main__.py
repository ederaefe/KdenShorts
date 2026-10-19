"""Executable package entry point for python -m clip_harvester."""

from clip_harvester.bootstrap import ensure_environment

if __name__ == "__main__":
    ensure_environment()
    from clip_harvester.cli import main

    main()
