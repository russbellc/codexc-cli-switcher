"""Implementación de plataforma Windows 10/11 para codexc."""

import os
import shutil
import subprocess


def resolve_real_home() -> str:
    """Resuelve el directorio home real del usuario en Windows."""
    return os.environ.get("CODEX_REAL_HOME") or os.path.expanduser("~")


def get_local_bin_dir(real_home: str) -> str:
    """Retorna el directorio local de ejecutables en Windows."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return os.path.join(local_app_data, "codexc", "bin")
    return os.path.join(real_home, ".local", "bin")


def _is_inside_dir(path: str, directory: str) -> bool:
    """Verifica si 'path' reside dentro de 'directory' (insensible a mayúsculas)."""
    try:
        p_norm = os.path.normcase(os.path.realpath(os.path.dirname(path)))
        d_norm = os.path.normcase(os.path.realpath(directory))
        return p_norm == d_norm
    except OSError:
        return False


def _resolve_non_ps1_candidate(cand: str, local_bin_dir: str) -> str | None:
    """Descarta wrappers propios y scripts .ps1, resolviendo .exe/.cmd válidos."""
    if not cand:
        return None
    lower = cand.lower()
    if lower.endswith(".ps1"):
        base = cand[:-4]
        for ext in (".exe", ".cmd", ".bat"):
            sibling = base + ext
            if os.path.isfile(sibling) and not _is_inside_dir(sibling, local_bin_dir):
                return sibling
        return None
    if os.path.isfile(cand) and not _is_inside_dir(cand, local_bin_dir):
        return cand
    return None


def get_real_codex_bin(real_home: str, local_bin_dir: str) -> str:
    """Localiza el binario real de Codex CLI en Windows (.exe/.cmd, nunca .ps1)."""
    standalone_exe = os.path.join(
        real_home, ".codex", "packages", "standalone", "current", "bin", "codex.exe"
    )
    if os.path.isfile(standalone_exe):
        return standalone_exe

    for name in ("codex.exe", "codex.cmd", "codex"):
        cand = shutil.which(name)
        resolved = _resolve_non_ps1_candidate(cand, local_bin_dir) if cand else None
        if resolved:
            return resolved

    extra_candidates: list[str] = []
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        extra_candidates.append(
            os.path.join(local_app_data, "Author Software", "nvm", ".nodejs", "codex.cmd")
        )
    app_data = os.environ.get("APPDATA")
    if app_data:
        extra_candidates.append(os.path.join(app_data, "npm", "codex.cmd"))
    else:
        extra_candidates.append(
            os.path.join(real_home, "AppData", "Roaming", "npm", "codex.cmd")
        )

    for cand in extra_candidates:
        if os.path.isfile(cand) and not _is_inside_dir(cand, local_bin_dir):
            return cand

    return standalone_exe


def create_dir_link(src: str, dst: str) -> bool:
    """Crea un NTFS Junction en Windows sin requerir privilegios de administrador."""
    try:
        res = subprocess.run(
            ["cmd", "/c", "mklink", "/J", dst, src],
            check=False,
            capture_output=True,
        )
        return res.returncode == 0 and os.path.exists(dst)
    except OSError:
        return False


def ensure_private_dir(path: str) -> None:
    """Crea un directorio privado bajo el perfil de usuario en Windows."""
    os.makedirs(path, exist_ok=True)


def ensure_public_dir(path: str) -> None:
    """Crea el directorio de ejecutables en Windows."""
    os.makedirs(path, exist_ok=True)


def set_private_file_permissions(path: str) -> None:
    """Mantiene compatibilidad sin fallar cuando los bits POSIX no aplican en NTFS."""
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def set_executable_permissions(path: str) -> None:
    """En Windows la ejecutabilidad depende de la extensión (.cmd/.bat/.exe)."""
    _ = path


def is_executable(path: str) -> bool:
    """Verifica si el archivo existe y es ejecutable (.cmd/.bat/.exe) en Windows."""
    if not os.path.isfile(path):
        return False
    return path.lower().endswith((".cmd", ".bat", ".exe")) or os.access(path, os.X_OK)


def get_dir_security_status(path: str) -> str:
    """Retorna el estado del directorio de caché en Windows."""
    return "NTFS privado" if os.path.isdir(path) else "aviso"


def get_launcher_path(local_bin_dir: str, alias: str) -> str:
    """Retorna la ruta esperada del lanzador .cmd de un alias en Windows."""
    return os.path.join(local_bin_dir, f"{alias}.cmd")


def wrap_codex_command(real_bin: str, args: list[str]) -> list[str]:
    """Envuelve archivos .cmd/.bat con 'cmd /c' para subprocess en Windows."""
    if real_bin.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", real_bin, *args]
    return [real_bin, *args]
