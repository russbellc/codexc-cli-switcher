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
$PythonVersion = $null
$nativePySpecs = [System.Collections.Generic.List[object]]::new()
$msixPySpecs = [System.Collections.Generic.List[object]]::new()
$seenPy = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)

$addPySpec = {
    param([string]$ExePath, [string[]]$PreArgs = @())
    if ([string]::IsNullOrWhiteSpace($ExePath)) { return }
    $key = "$ExePath|$($PreArgs -join ' ')"
    if (-not $seenPy.Add($key)) { return }
    if ($ExePath -match '(?i)\\WindowsApps\\') {
        $msixPySpecs.Add(@{ Exe = $ExePath; PreArgs = $PreArgs })
    } else {
        $nativePySpecs.Add(@{ Exe = $ExePath; PreArgs = $PreArgs })
    }
}

if (-not [string]::IsNullOrWhiteSpace($RealHome)) {
    Get-ChildItem -Path (Join-Path $RealHome ".local\bin\python*.exe") -File -ErrorAction SilentlyContinue |
        Sort-Object Name -Descending | ForEach-Object { & $addPySpec $_.FullName }
}
if (-not [string]::IsNullOrWhiteSpace($env:APPDATA)) {
    Get-ChildItem -Path (Join-Path $env:APPDATA "uv\python\cpython-*\python.exe") -File -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending | ForEach-Object { & $addPySpec $_.FullName }
}
if (-not [string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
    Get-ChildItem -Path (Join-Path $env:LOCALAPPDATA "Programs\Python\Python*\python.exe") -File -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending | ForEach-Object { & $addPySpec $_.FullName }
}
foreach ($pat in @("C:\Python*\python.exe", "C:\Program Files\Python*\python.exe")) {
    Get-ChildItem -Path $pat -File -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending | ForEach-Object { & $addPySpec $_.FullName }
}
foreach ($cand in @("python", "python3", "py")) {
    $cmds = Get-Command $cand -All -ErrorAction SilentlyContinue
    foreach ($c in $cmds) {
        if (-not $c.Source) { continue }
        $pre = if ($cand -eq "py") { @("-3") } else { @() }
        & $addPySpec $c.Source $pre
    }
}

$msixFallbackExe = $null
$msixFallbackVer = $null
$pyProbe = "import os, sys; assert sys.version_info >= (3, 10); exe = sys.executable if os.path.exists(sys.executable) else ''; print(exe); print(f'{sys.version_info.major}.{sys.version_info.minor}')"
foreach ($spec in (@($nativePySpecs) + @($msixPySpecs))) {
    try {
        $probeArgs = $spec.PreArgs + @("-S", "-c", $pyProbe)
        $out = & $spec.Exe @probeArgs 2>$null
        if ($LASTEXITCODE -eq 0 -and $out.Count -ge 2) {
            $resolvedExe = "$($out[0])".Trim()
            if (-not $resolvedExe) { $resolvedExe = $spec.Exe }
            $verStr = "$($out[1])".Trim()
            if ($resolvedExe -match '(?i)\\WindowsApps\\') {
                if (-not $msixFallbackExe) {
                    $msixFallbackExe = $resolvedExe
                    $msixFallbackVer = $verStr
                }
                continue
            }
            $PythonExe = $resolvedExe
            $PythonVersion = $verStr
            break
        }
    } catch {}
}
if (-not $PythonExe -and $msixFallbackExe) {
    $PythonExe = $msixFallbackExe
    $PythonVersion = $msixFallbackVer
}

if (-not $PythonExe) {
    Write-Host "X Python 3.10+ no encontrado. Instala Python 3.10 o superior." -ForegroundColor Red
    exit 1
}
Write-Host "  Python: $PythonVersion ($PythonExe)" -ForegroundColor DarkGray

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
