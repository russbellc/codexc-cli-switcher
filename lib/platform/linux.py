"""Implementación de plataforma Linux/POSIX para codexc."""

import os
import shutil


def resolve_real_home() -> str:
    """Resuelve el directorio home real del usuario en Linux."""
    env_home = os.environ.get("CODEX_REAL_HOME")
    if env_home:
        return env_home
    expanded = os.path.expanduser("~")
    if expanded and expanded not in ("~", "/root"):
        return expanded
    return "/home/aidev"


def get_local_bin_dir(real_home: str) -> str:
    """Retorna el directorio local de ejecutables (~/.local/bin) en Linux."""
    return os.path.join(real_home, ".local", "bin")


def get_real_codex_bin(real_home: str, local_bin_dir: str) -> str:
    """Localiza el binario real de Codex CLI en Linux excluyendo el wrapper local."""
    central_bin = os.path.join(
        real_home, ".codex", "packages", "standalone", "current", "bin", "codex"
    )
    if os.path.isfile(central_bin) and os.access(central_bin, os.X_OK):
        return central_bin

    cand = shutil.which("codex")
    if cand and os.path.realpath(cand) != os.path.realpath(os.path.join(local_bin_dir, "codex")):
        return cand

    return os.path.join(
        real_home,
        ".codex",
        "packages",
        "standalone",
        "releases",
        "0.164.0-x86_64-unknown-linux-musl",
        "bin",
        "codex",
    )


def create_dir_link(src: str, dst: str) -> bool:
    """Crea un enlace simbólico de directorio en Linux."""
    try:
        os.symlink(src, dst)
        return True
    except OSError:
        return False


def ensure_private_dir(path: str) -> None:
    """Crea un directorio privado con permisos 0700 en Linux."""
    os.makedirs(path, mode=0o700, exist_ok=True)
    try:
        os.chmod(path, 0o700)
    except OSError:
        pass


def ensure_public_dir(path: str) -> None:
    """Crea un directorio de ejecutables con permisos 0755 en Linux."""
    os.makedirs(path, mode=0o755, exist_ok=True)


def set_private_file_permissions(path: str) -> None:
    """Aplica permisos 0600 a un archivo sensible en Linux."""
    os.chmod(path, 0o600)


def set_executable_permissions(path: str) -> None:
    """Aplica permisos 0755 a un script ejecutable en Linux."""
    os.chmod(path, 0o755)


def is_executable(path: str) -> bool:
    """Verifica si el archivo existe y tiene permiso de ejecución en Linux."""
    return os.path.isfile(path) and os.access(path, os.X_OK)


def get_dir_security_status(path: str) -> str:
    """Retorna el estado de permisos del directorio de caché para 'codexc doctor'."""
    try:
        return "0700" if oct(os.stat(path).st_mode & 0o777) == "0o700" else "aviso"
    except OSError:
        return "aviso"


def get_launcher_path(local_bin_dir: str, alias: str) -> str:
    """Retorna la ruta esperada del lanzador de un alias en Linux."""
    return os.path.join(local_bin_dir, alias)


def wrap_codex_command(real_bin: str, args: list[str]) -> list[str]:
    """Construye la lista de argumentos para invocar el binario real en Linux."""
    return [real_bin, *args]
