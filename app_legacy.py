"""Compatibility launcher.

This file used to contain the pre-Django HTTP server. It now delegates to the
Django app so editor links or old run configurations cannot start the obsolete
version by accident.
"""
from __future__ import annotations

from app import run


if __name__ == "__main__":
    run()
