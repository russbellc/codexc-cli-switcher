"""Abstracción de plataforma para codexc (Windows 10/11 y Linux)."""

import os

IS_WINDOWS = os.name == "nt"

if IS_WINDOWS:
    from lib.platform.win32 import (
        create_dir_link,
        ensure_private_dir,
        ensure_public_dir,
        get_dir_security_status,
        get_launcher_path,
        get_local_bin_dir,
        get_real_codex_bin,
        is_executable,
        resolve_real_home,
        set_executable_permissions,
        set_private_file_permissions,
        wrap_codex_command,
    )
else:
    from lib.platform.linux import (
        create_dir_link,
        ensure_private_dir,
        ensure_public_dir,
        get_dir_security_status,
        get_launcher_path,
        get_local_bin_dir,
        get_real_codex_bin,
        is_executable,
        resolve_real_home,
        set_executable_permissions,
        set_private_file_permissions,
        wrap_codex_command,
    )

__all__ = [
    "IS_WINDOWS",
    "create_dir_link",
    "ensure_private_dir",
    "ensure_public_dir",
    "get_dir_security_status",
    "get_launcher_path",
    "get_local_bin_dir",
    "get_real_codex_bin",
    "is_executable",
    "resolve_real_home",
    "set_executable_permissions",
    "set_private_file_permissions",
    "wrap_codex_command",
]
