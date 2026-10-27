#!/usr/bin/env bash
# Script de instalación para codexc (Codex CLI Switcher)
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$SCRIPT_DIR/bin"
REAL_HOME="${CODEX_REAL_HOME:-/home/aidev}"
LOCAL_BIN="$REAL_HOME/.local/bin"

echo "=== Instalando codexc en $LOCAL_BIN ==="
mkdir -p "$LOCAL_BIN"

# 1. Asegurar permisos de ejecución
chmod +x "$BIN_DIR/codexc"

# 2. Enlazar o copiar codexc a ~/.local/bin/
ln -sf "$BIN_DIR/codexc" "$LOCAL_BIN/codexc"

# 3. También en el HOME actual si es diferente
if [ "$HOME" != "$REAL_HOME" ] && [ -d "$HOME" ]; then
    mkdir -p "$HOME/.local/bin"
    ln -sf "$BIN_DIR/codexc" "$HOME/.local/bin/codexc"
fi

# 3. Ejecutar auto-migración y generación de lanzadores
"$LOCAL_BIN/codexc" list >/dev/null 2>&1 || true

echo "✓ codexc instalado correctamente en $LOCAL_BIN/codexc."
echo "Comandos disponibles:"
echo "  • codexc list    : Ver tabla de cuentas y cuotas"
echo "  • codexc add     : Registrar nueva cuenta"
echo "  • codex01, ...   : Lanzadores independientes por perfil"
