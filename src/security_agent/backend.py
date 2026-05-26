from __future__ import annotations

import os
import sys

from security_agent.config import Settings, get_settings


def build_backend(settings: Settings | None = None, allow_shell: bool | None = None):
    settings = settings or get_settings()
    provider = settings.sandbox_provider
    if provider == "local":
        return _build_local_backend(settings, allow_shell=allow_shell)
    if provider == "opensandbox":
        return _build_opensandbox_backend(settings)
    raise ValueError(f"Unsupported sandbox provider: {provider}. Expected 'local' or 'opensandbox'.")


def _build_local_backend(settings: Settings, allow_shell: bool | None = None):
    settings.workspace_dir.mkdir(parents=True, exist_ok=True)
    try:
        from deepagents.backends import FilesystemBackend, LocalShellBackend
    except ImportError:
        return None

    allow_shell = settings.sandbox_allow_shell if allow_shell is None else allow_shell
    if allow_shell:
        return LocalShellBackend(
            root_dir=str(settings.workspace_dir),
            virtual_mode=True,
            timeout=30,
            max_output_bytes=50000,
            env={"PATH": f"{os.path.dirname(sys.executable)}:{os.environ.get('PATH', '')}"},
        )
    return FilesystemBackend(root_dir=str(settings.workspace_dir), virtual_mode=True)


def _build_opensandbox_backend(settings: Settings):
    """Reserved OpenSandbox integration point.

    The project currently ships a local production sandbox by default. Selecting
    OpenSandbox should fail loudly until the deployment has the OpenSandbox SDK,
    connection settings, and a backend adapter installed.
    """
    if not settings.opensandbox_domain:
        raise RuntimeError(
            "SECURITY_AGENT_SANDBOX_PROVIDER=opensandbox requires "
            "SECURITY_AGENT_OPENSANDBOX_DOMAIN to be configured."
        )
    raise RuntimeError(
        "OpenSandbox provider is reserved but not enabled in this lightweight local build. "
        "Use SECURITY_AGENT_SANDBOX_PROVIDER=local, or add an OpenSandbox backend adapter "
        "for your deployment."
    )

