#!/usr/bin/env bash
# =============================================================================
# codexc — Instalador Multi-Cuenta para OpenAI Codex CLI
# Multi-account switcher con perfiles CODEX_HOME aislados por cuenta
#
# Uso:
#   chmod +x install.sh && ./install.sh
#
# Requisitos:
#   - Linux x86_64 (Ubuntu / Debian / RHEL / Arch)
#   - OpenAI Codex CLI instalado
#   - Python 3.10+
# =============================================================================

set -e

BOLD="\033[1m"
GREEN="\033[32m"
CYAN="\033[36m"
YELLOW="\033[33m"
RED="\033[31m"
DIM="\033[2m"
RESET="\033[0m"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$SCRIPT_DIR/bin"
REAL_HOME="${CODEX_REAL_HOME:-/home/aidev}"
LOCAL_BIN="$REAL_HOME/.local/bin"
SKILL_DIR="$REAL_HOME/proyectos/.agents/skills/codexc"

echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}${CYAN}║        codexc — Instalador Multi-Cuenta              ║${RESET}"
echo -e "${BOLD}${CYAN}║     OpenAI Codex CLI Switcher para Linux             ║${RESET}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════════╝${RESET}"
echo ""

# ── Paso 1: Verificar requisitos ──────────────────────────────────────────────
echo -e "${BOLD}[1/5] Verificando requisitos del sistema...${RESET}"

if ! command -v python3 &>/dev/null; then
    echo -e "${RED}✗ Python3 no encontrado. Instalar con: sudo apt install python3${RESET}"
    exit 1
fi

PYTHON_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo -e "  ${DIM}Python: $PYTHON_VER${RESET}"

CODEX_BIN=""
for path in \
    "$REAL_HOME/.codex/packages/standalone/current/bin/codex" \
    "$HOME/.codex/packages/standalone/current/bin/codex" \
    "$(which codex 2>/dev/null || true)"; do
    if [ -n "$path" ] && [ -x "$path" ] && [[ "$path" != *".local/bin/codex"* ]]; then
        CODEX_BIN="$path"
        break
    fi
done

if [ -n "$CODEX_BIN" ]; then
    echo -e "  ${GREEN}✓ Binario central de Codex encontrado:${RESET} ${DIM}$CODEX_BIN${RESET}"
else
    echo -e "  ${YELLOW}⚠ Binario central de Codex no detectado aún en rutas estándar.${RESET}"
    echo -e "  ${DIM}  El conmutador funcionará una vez que instales Codex CLI.${RESET}"
fi

# ── Paso 2: Crear directorios base ────────────────────────────────────────────
echo -e "${BOLD}[2/5] Creando directorios y configurando permisos...${RESET}"
mkdir -p "$LOCAL_BIN"
mkdir -p "$REAL_HOME/.codexc/cache"
mkdir -p "$REAL_HOME/.codexc_homes"
chmod 700 "$REAL_HOME/.codexc/cache" 2>/dev/null || true
chmod 700 "$REAL_HOME/.codexc_homes" 2>/dev/null || true

# ── Paso 3: Instalar ejecutable y symlinks ─────────────────────────────────────
echo -e "${BOLD}[3/5] Instalando binario codexc en $LOCAL_BIN...${RESET}"
chmod +x "$BIN_DIR/codexc"
ln -sf "$BIN_DIR/codexc" "$LOCAL_BIN/codexc"

# Asegurar compatibilidad si HOME difiere de REAL_HOME
if [ "$HOME" != "$REAL_HOME" ] && [ -d "$HOME" ]; then
    mkdir -p "$HOME/.local/bin"
    ln -sf "$BIN_DIR/codexc" "$HOME/.local/bin/codexc"
fi

# ── Paso 4: Instalar skill para agentes ────────────────────────────────────────
echo -e "${BOLD}[4/5] Registrando skill de agente en el sistema...${RESET}"
if [ -d "$SCRIPT_DIR/skills/codexc" ]; then
    mkdir -p "$SKILL_DIR"
    cp -f "$SCRIPT_DIR/skills/codexc/SKILL.md" "$SKILL_DIR/SKILL.md" 2>/dev/null || true
    echo -e "  ${GREEN}✓ Skill codexc sincronizada en:${RESET} ${DIM}$SKILL_DIR${RESET}"
fi

# ── Paso 5: Sincronizar perfiles y verificar doctor ───────────────────────────
echo -e "${BOLD}[5/5] Sincronizando perfiles y lanzadores...${RESET}"
"$LOCAL_BIN/codexc" doctor >/dev/null 2>&1 || true

echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}${GREEN}║     ¡codexc se ha instalado correctamente!           ║${RESET}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════════════╝${RESET}"
echo ""
echo -e "Comandos principales:"
echo -e "  ${CYAN}codexc${RESET}                 Ver panel de cuentas y consumo de cuotas"
echo -e "  ${CYAN}codexc list --refresh${RESET}  Actualizar cuotas en vivo desde OpenAI"
echo -e "  ${CYAN}codexc add${RESET}             Registrar una nueva cuenta"
echo -e "  ${CYAN}codexc auto${RESET}            Rotar a la cuenta con mayor saldo (5h)"
echo -e "  ${CYAN}codex01, codex02...${RESET}    Lanzadores dedicados independientes"
echo ""
echo -e "Para asegurar que ${CYAN}~/.local/bin${RESET} esté en tu PATH, ejecuta:"
echo -e "  ${BOLD}source ~/.bashrc${RESET}"
echo ""
