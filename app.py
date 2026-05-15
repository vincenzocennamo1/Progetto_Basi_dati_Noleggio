from __future__ import annotations

import os
import sys

from django.core.management import execute_from_command_line


def run() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "noleggio_project.settings")
    port = os.environ.get("PORT", "8000")
    print(f"Applicazione Django avviata su http://127.0.0.1:{port}/login")
    execute_from_command_line([sys.argv[0], "runserver", f"127.0.0.1:{port}", "--noreload"])


if __name__ == "__main__":
    run()
