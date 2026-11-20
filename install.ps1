# =============================================================================
# codexc — Instalador Multi-Cuenta para OpenAI Codex CLI (Windows 10/11)
# =============================================================================

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RealHome = if ($env:CODEX_REAL_HOME) { $env:CODEX_REAL_HOME } else { $env:USERPROFILE }
$CodexcHome = Join-Path $RealHome ".codexc"
$CacheDir = Join-Path $CodexcHome "cache"
$HomesDir = Join-Path $RealHome ".codexc_homes"
$LocalBinDir = if ($env:LOCALAPPDATA) {
    Join-Path (Join-Path $env:LOCALAPPDATA "codexc") "bin"
} else {
    Join-Path (Join-Path $RealHome ".local") "bin"
}

Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "        codexc - Instalador Multi-Cuenta (Windows)      " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# ── Paso 1: Verificar Python 3.10+ ───────────────────────────────────────────
Write-Host "[1/6] Verificando requisitos del sistema..." -ForegroundColor White

$PythonExe = $null
foreach ($cand in @("python", "python3", "py")) {
    $cmd = Get-Command $cand -ErrorAction SilentlyContinue
    if ($cmd) {
        try {
            $verArgs = if ($cand -eq "py") { @("-3", "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')") } else { @("-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')") }
            $verOut = & $cmd.Source @verArgs 2>$null
            if ($LASTEXITCODE -eq 0 -and $verOut) {
                $parts = $verOut.Trim().Split(".")
                $maj = [int]$parts[0]
                $min = [int]$parts[1]
                if ($maj -gt 3 -or ($maj -eq 3 -and $min -ge 10)) {
                    $PythonExe = if ($cand -eq "py") { (& $cmd.Source -3 -c "import sys; print(sys.executable)").Trim() } else { $cmd.Source }
                    Write-Host "  Python: $verOut ($PythonExe)" -ForegroundColor DarkGray
                    break
                }
            }
        } catch {}
    }
}

if (-not $PythonExe) {
    Write-Host "X Python 3.10+ no encontrado. Instala Python 3.10 o superior." -ForegroundColor Red
    exit 1
}

# Detectar binario real de Codex (.exe / .cmd, nunca .ps1 ni wrapper propio)
$CodexBin = $null
$StandaloneCodex = Join-Path $RealHome ".codex\packages\standalone\current\bin\codex.exe"
if (Test-Path $StandaloneCodex -PathType Leaf) {
    $CodexBin = $StandaloneCodex
}

if (-not $CodexBin) {
    foreach ($name in @("codex.exe", "codex.cmd", "codex")) {
        $cmds = Get-Command $name -All -ErrorAction SilentlyContinue
        foreach ($c in $cmds) {
            $src = $c.Source
            if (-not $src) { continue }
            if ($src.ToLower().EndsWith(".ps1")) { continue }
            $dir = Split-Path -Parent $src
            if ($dir.TrimEnd("\").ToLower() -eq $LocalBinDir.TrimEnd("\").ToLower()) { continue }
            if (Test-Path $src -PathType Leaf) {
                $CodexBin = $src
                break
            }
        }
        if ($CodexBin) { break }
    }
}

if (-not $CodexBin) {
    $ExtraCandidates = @()
    if ($env:LOCALAPPDATA) {
        $ExtraCandidates += Join-Path $env:LOCALAPPDATA "Author Software\nvm\.nodejs\codex.cmd"
    }
    if ($env:APPDATA) {
        $ExtraCandidates += Join-Path $env:APPDATA "npm\codex.cmd"
    }
    foreach ($cand in $ExtraCandidates) {
        if (Test-Path $cand -PathType Leaf) {
            $CodexBin = $cand
            break
        }
    }
}

if ($CodexBin) {
    Write-Host "  Binario real de Codex encontrado: $CodexBin" -ForegroundColor Green
} else {
    Write-Host "  ! Binario real de Codex no detectado aun en rutas estandar." -ForegroundColor Yellow
}

# ── Paso 2: Crear directorios base ───────────────────────────────────────────
Write-Host "[2/6] Creando directorios base..." -ForegroundColor White
New-Item -ItemType Directory -Force -Path $LocalBinDir | Out-Null
New-Item -ItemType Directory -Force -Path $CacheDir | Out-Null
New-Item -ItemType Directory -Force -Path $HomesDir | Out-Null

# ── Paso 3: Copiar lib/ y bin/codexc a %USERPROFILE%\.codexc\ ────────────────
Write-Host "[3/6] Instalando codexc en $CodexcHome..." -ForegroundColor White
$DestBinDir = Join-Path $CodexcHome "bin"
$DestLibDir = Join-Path $CodexcHome "lib"
New-Item -ItemType Directory -Force -Path $DestBinDir | Out-Null

Copy-Item -Path (Join-Path $ScriptDir "bin\codexc") -Destination (Join-Path $DestBinDir "codexc") -Force
if (Test-Path $DestLibDir) {
    Remove-Item -Path $DestLibDir -Recurse -Force
}
Copy-Item -Path (Join-Path $ScriptDir "lib") -Destination $DestLibDir -Recurse -Force

# Generar codexc.cmd en LOCAL_BIN_DIR
$InstalledScript = Join-Path $DestBinDir "codexc"
$CodexcCmdPath = Join-Path $LocalBinDir "codexc.cmd"
$CodexcCmdContent = "@echo off`r`n`"$PythonExe`" `"$InstalledScript`" %*`r`n"
[System.IO.File]::WriteAllText($CodexcCmdPath, $CodexcCmdContent, [System.Text.Encoding]::ASCII)
Write-Host "  Lanzador creado: $CodexcCmdPath" -ForegroundColor Green

# ── Paso 4: Añadir LOCAL_BIN_DIR al User PATH ────────────────────────────────
Write-Host "[4/6] Configurando User PATH..." -ForegroundColor White
$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
$PathEntries = if ($UserPath) { $UserPath.Split(";", [System.StringSplitOptions]::RemoveEmptyEntries) } else { @() }
$AlreadyInPath = $false
foreach ($entry in $PathEntries) {
    if ($entry.TrimEnd("\").ToLower() -eq $LocalBinDir.TrimEnd("\").ToLower()) {
        $AlreadyInPath = $true
        break
    }
}
if (-not $AlreadyInPath) {
    $NewUserPath = if ($UserPath) { "$UserPath;$LocalBinDir" } else { $LocalBinDir }
    [Environment]::SetEnvironmentVariable("Path", $NewUserPath, "User")
    $env:Path = "$env:Path;$LocalBinDir"
    Write-Host "  Agregado al User PATH: $LocalBinDir" -ForegroundColor Green
} else {
    Write-Host "  Ya presente en User PATH: $LocalBinDir" -ForegroundColor DarkGray
}

# ── Paso 5: Instalar skill para agentes ──────────────────────────────────────
Write-Host "[5/6] Registrando skill de agente..." -ForegroundColor White
$SkillSrc = Join-Path $ScriptDir "skills\codexc\SKILL.md"
if (Test-Path $SkillSrc -PathType Leaf) {
    $SkillDestDir = Join-Path $RealHome ".agents\skills\codexc"
    New-Item -ItemType Directory -Force -Path $SkillDestDir | Out-Null
    Copy-Item -Path $SkillSrc -Destination (Join-Path $SkillDestDir "SKILL.md") -Force
    Write-Host "  Skill sincronizada en: $SkillDestDir" -ForegroundColor Green
}

# ── Paso 6: Verificar doctor y tests ─────────────────────────────────────────
Write-Host "[6/6] Ejecutando 'codexc doctor' y pruebas unitarias..." -ForegroundColor White
& $CodexcCmdPath doctor

$TestsDir = Join-Path $ScriptDir "tests"
if (Test-Path $TestsDir -PathType Container) {
    Push-Location $ScriptDir
    try {
        & $PythonExe -m unittest discover -s tests
    } finally {
        Pop-Location
    }
}

Write-Host ""
Write-Host "codexc instalado correctamente en Windows." -ForegroundColor Green
Write-Host "Abre una nueva terminal para usar 'codexc', 'codex', 'codex01', etc." -ForegroundColor Cyan
Write-Host ""
