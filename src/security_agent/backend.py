from __future__ import annotations

import os
import sys

from security_agent.config import Settings, get_settings


def build_backend(settings: Settings | None = None, allow_shell: bool = False):
    settings = settings or get_settings()
    settings.workspace_dir.mkdir(parents=True, exist_ok=True)
    try:
        from deepagents.backends import FilesystemBackend, LocalShellBackend
    except ImportError:
        return None

    if allow_shell:
        return LocalShellBackend(
            root_dir=str(settings.workspace_dir),
            virtual_mode=True,
            timeout=30,
            max_output_bytes=50000,
            env={"PATH": f"{os.path.dirname(sys.executable)}:{os.environ.get('PATH', '')}"},
        )
    return FilesystemBackend(root_dir=str(settings.workspace_dir), virtual_mode=True)

