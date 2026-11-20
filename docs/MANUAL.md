# Manual Completo de `codexc`
## OpenAI Codex CLI Multi-Account Switcher

> **Versión:** v1.3 | **Fecha:** Noviembre 2026  
> **Plataformas:** Linux x86_64 (Ubuntu / Debian / RHEL / Arch) y Windows 10/11  
> **Compatibilidad:** OpenAI Codex CLI (standalone, bundled y npm en Windows)  
> **Referencia técnica:** [Arquitectura y Funcionalidad Técnica](ARQUITECTURA_Y_FUNCIONALIDAD.md)

---

## Índice

1. [¿Para qué sirve codexc?](#1-para-qué-sirve-codexc)
2. [Instalación y Requisitos](#2-instalación-y-requisitos)
3. [Primeros Pasos y Ciclo de Vida de Cuentas](#3-primeros-pasos-y-ciclo-de-vida-de-cuentas)
4. [Comandos de Referencia](#4-comandos-de-referencia)
5. [Aislamiento de Perfiles por `$CODEX_HOME`](#5-aislamiento-de-perfiles-por-codex_home)
6. [Ejecución en Múltiples Paneles en Paralelo](#6-ejecución-en-múltiples-paneles-en-paralelo)
7. [Modo `--yolo` Automático e Inyección de Argumentos](#7-modo---yolo-automático-e-inyección-de-argumentos)
8. [API de Cuotas de OpenAI ChatGPT y Monitoreo](#8-api-de-cuotas-de-openai-chatgpt-y-monitoreo)
9. [Arquitectura de Renovación de Tokens (`app-server`)](#9-arquitectura-de-renovación-de-tokens-app-server)
10. [Seguridad y Permisos del Sistema de Archivos](#10-seguridad-y-permisos-del-sistema-de-archivos)
11. [Diagnóstico, Troubleshooting y `codexc doctor`](#11-diagnóstico-troubleshooting-y-codexc-doctor)
12. [Integración con Agentes Autónomos (Skill para Herdr)](#12-integración-con-agentes-autónomos-skill-para-herdr)
13. [Historia de Versiones y Decisiones de Diseño](#13-historia-de-versiones-y-decisiones-de-diseño)

---

## 1. ¿Para qué sirve codexc?

OpenAI Codex CLI está diseñado para interactuar con una única cuenta local predeterminada almacenada en `~/.codex/auth.json`. Cuando un desarrollador o equipo trabaja a jornada completa utilizando modelos avanzados (como `gpt-6.1-sol` o `gpt-5.6-sol`), las limitaciones de tokens de una sola suscripción de ChatGPT Plus o Pro se alcanzan rápidamente:

- **Ventana de 5 horas:** Límite rodante estricto para modelos insignia.
- **Límite semanal:** Tope acumulativo de cómputo para la cuenta.

`codexc` transforma Codex CLI en un entorno multi-cuenta profesional:
- Permite gestionar múltiples perfiles independientes (`codex01`, `codex02`, etc.).
- Proporciona lanzadores directos para correr múltiples agentes en paralelo en distintos paneles del terminal (Herdr, tmux, zellij) sin competencia de credenciales ni sobrescritura de archivos SQLite.
- Ofrece monitoreo en tiempo real de saldos y rotación automática hacia la cuenta con mayor disponibilidad.

---

## 2. Instalación y Requisitos

### Requisitos

| Componente | Requisito mínimo | Notas |
|---|---|---|
| **Sistema Operativo** | Linux x86_64 o Windows 10/11 | Probado en Ubuntu 20.04/22.04/24.04/26.04 y Windows 10/11 |
| **Python** | 3.10+ | Biblioteca estándar únicamente, no requiere pip ni librerías de terceros |
| **Codex CLI** | 0.160.0+ | Instalado en el sistema (binario nativo o `codex.exe` / `codex.cmd` en Windows) |
| **Cuentas ChatGPT** | Plus, Pro o Team | Al menos una cuenta activa |

### Instalación Automática en Linux

```bash
git clone https://github.com/russbellc/codexc-cli-switcher.git
cd codexc-cli-switcher
chmod +x install.sh
./install.sh
source ~/.bashrc
```

### Instalación Automática en Windows 10/11

El repositorio incluye [`install.cmd`](../install.cmd) (wrapper que ejecuta PowerShell con `-NoProfile -ExecutionPolicy Bypass`) e [`install.ps1`](../install.ps1).

Desde **CMD**:

```cmd
git clone https://github.com/russbellc/codexc-cli-switcher.git
cd codexc-cli-switcher
install.cmd
```

O directamente desde **PowerShell**:

```powershell
git clone https://github.com/russbellc/codexc-cli-switcher.git
cd codexc-cli-switcher
.\install.ps1
```

**¿Qué realiza `install.ps1`?**
1. Verifica que **Python 3.10+** (`python`, `python3` o `py -3`) esté instalado.
2. Localiza el binario real de Codex CLI evitando scripts `.ps1` (busca `%USERPROFILE%\.codex\packages\standalone\current\bin\codex.exe`, `codex.exe`/`codex.cmd` en `PATH` excluyendo `%LOCALAPPDATA%\codexc\bin`, y rutas estándar como `%LOCALAPPDATA%\Author Software\nvm\.nodejs\codex.cmd` o `%APPDATA%\npm\codex.cmd`).
3. Crea los directorios base:
   - `%LOCALAPPDATA%\codexc\bin`
   - `%USERPROFILE%\.codexc\cache`
   - `%USERPROFILE%\.codexc_homes`
4. Copia `bin\codexc` y `lib\` a `%USERPROFILE%\.codexc\bin\codexc` y `%USERPROFILE%\.codexc\lib\`, y genera `%LOCALAPPDATA%\codexc\bin\codexc.cmd`.
5. Agrega `%LOCALAPPDATA%\codexc\bin` al `Path` del usuario en Windows si aún no está registrado.
6. Sincroniza `skills\codexc\SKILL.md` en `%USERPROFILE%\.agents\skills\codexc\SKILL.md`.
7. Ejecuta `codexc.cmd doctor` y la suite `python -m unittest discover -s tests`.

> **Nota:** Tras finalizar el instalador en Windows, abre una nueva terminal (CMD, PowerShell o Windows Terminal) para que el nuevo `Path` de usuario surta efecto y puedas usar `codexc`, `codex`, `codex01`, etc.

### Instalación Manual (Linux)

Si prefieres realizar la configuración paso a paso en Linux:

```bash
# 1. Crear directorio local de binarios
mkdir -p ~/.local/bin

# 2. Enlazar codexc a ~/.local/bin/
ln -sf /ruta/a/codexc-cli-switcher/bin/codexc ~/.local/bin/codexc
chmod +x /ruta/a/codexc-cli-switcher/bin/codexc

# 3. Asegurar que ~/.local/bin esté en tu $PATH (~/.bashrc o ~/.zshrc)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# 4. Sincronizar perfiles y generar lanzadores
codexc doctor
```

---

## 3. Primeros Pasos y Ciclo de Vida de Cuentas

### 3.1. Agregar cuentas (`codexc add`)

El comando `add` asiste en el registro de cuentas vinculándolas directamente a un `$CODEX_HOME` aislado:

```bash
# Registro con alias correlativo automático (codex01, codex02, ...)
codexc add

# O asignando un alias explícito
codexc add codex02
```

**Flujo en entornos locales con interfaz gráfica:**
1. Se abre el servidor local de autenticación de Codex en `http://localhost:1455`.
2. Tu navegador web se abre para iniciar sesión con tu cuenta de OpenAI.
3. Al completar el inicio de sesión, `codexc` extrae los tokens, detecta el correo de la cuenta y genera el lanzador correspondiente.

**Flujo en servidores remotos o entornos headless:**
```bash
codexc add codex02 --device-auth
```
Proporcionará una URL y un código alfanumérico para autenticarte desde cualquier otro dispositivo (teléfono o computadora local) sin necesidad de reenvío de puertos.

### 3.2. Protección contra cuentas duplicadas

`codexc` compara el `account_id` y el correo contra todos los perfiles existentes. Si intentas registrar accidentalmente la misma cuenta que ya existe bajo otro alias, `codexc` aborta la operación y limpia el directorio temporal para evitar redundancia y desperdicio de perfiles.

### 3.3. Migración portable entre equipos (Windows ↔ Ubuntu Linux)

No necesitas repetir el proceso de autenticación OAuth (`codexc add`) en cada máquina. `codexc` permite exportar las vinculaciones existentes (`auth.json` y `config.toml`) a un bundle JSON portátil (`codexc-bundle-v1`) e importarlas en otro equipo (por ejemplo de **Windows 10/11** a **Ubuntu Linux**, o viceversa):

```bash
# 1. En el equipo origen: exportar todos los perfiles (genera codexc-accounts-bundle.json)
codexc export

# O exportar un único perfil a una ruta específica:
codexc export codex01 -o codex01-bundle.json

# 2. Transferir el bundle de forma cifrada (ejemplo con scp):
scp codexc-accounts-bundle.json usuario@servidor:/tmp/codexc-accounts-bundle.json

# 3. En el equipo destino: importar las cuentas
codexc import /tmp/codexc-accounts-bundle.json

# 4. Borrar el archivo bundle en ambos equipos tras finalizar la importación
rm -f /tmp/codexc-accounts-bundle.json
```

> **Importante sobre rotación de `refresh_token`:** OpenAI rota los tokens de refresco cuando una sesión renueva su `access_token`. Si utilizas el mismo perfil simultáneamente en ambos equipos (por ejemplo Windows y Ubuntu Linux), cuando uno renueve el `refresh_token` el otro equipo puede quedar con el token anterior invalidado. En ese escenario, vuelve a exportar desde el equipo actualizado e importa con `codexc import <archivo> --overwrite`, o utiliza cuentas distintas en cada máquina.

---

## 4. Comandos de Referencia

### `codexc` o `codexc list`
Muestra la tabla interactiva de perfiles registrados con barras de progreso visuales para las ventanas de 5 horas y semanal.

```text
┌───────────┬──────────────────────────────┬──────────┬───────────────┬────────────────────────────────┬────────────────────────────────┐
│ ALIAS     │ CUENTA / EMAIL               │ PLAN     │ ESTADO        │ 5 HORAS (DISPONIBLE / RESET)   │ SEMANAL (DISPONIBLE / RESET)   │
├───────────┼──────────────────────────────┼──────────┼───────────────┼────────────────────────────────┼────────────────────────────────┤
│   codex01 │ dev1@gmail.com               │ PLUS     │   DEFAULT     │ 5H:  [████████]  96% (1h 35m)  │ Sem: [████░░░░]  47% (4d 10h)  │
├───────────┼──────────────────────────────┼──────────┼───────────────┼────────────────────────────────┼────────────────────────────────┤
│ * codex02 │ dev2@gmail.com               │ PLUS     │ * ACTIVA      │ 5H:  [████████]  98% (4h 15m)  │ Sem: [█████░░░]  67% (4d 12h)  │
└───────────┴──────────────────────────────┴──────────┴───────────────┴────────────────────────────────┴────────────────────────────────┘
```

**Opciones:**
- `--refresh`, `-r`: Invalida la memoria caché local (TTL 60s) y fuerza una petición en vivo a la API de OpenAI.
- `--json`: Devuelve la información en formato JSON estandarizado para scripts y automatizaciones.

### `codex01`, `codex02`, ...
Lanzadores de ejecución directa. Inician el binario oficial de Codex fijando el entorno `$CODEX_HOME` de dicho perfil y habilitando automáticamente el modo `--yolo`.

### `codexc switch <alias>` (o `codexc <alias>`)
Cambia el perfil activo al que apuntará el comando global `codex`.

```bash
codexc switch codex02
# o simplemente:
codexc codex02
```

### `codexc default <alias>`
Establece cuál cuenta será seleccionada si no existe una sesión activa definida.

### `codexc auto`
Analiza los porcentajes restantes de todas las cuentas y realiza un cambio automático hacia la cuenta con mayor saldo disponible en la ventana crítica de 5 horas.

### `codexc quota [alias]`
Muestra un reporte detallado con las marcas de tiempo ISO exactas y el tiempo restante para el restablecimiento de cuotas.

### `codexc doctor`
Ejecuta una batería de comprobaciones sobre:
- Existencia y ejecutabilidad del binario real de Codex (`codex` en Linux; `codex.exe` o `codex.cmd` en Windows, evitando `codex.ps1`).
- Integridad y permisos del sistema (`0700`/`0600` en Linux; `NTFS privado` en Windows) de los perfiles y del directorio de caché.
- Existencia y consistencia de los lanzadores en `~/.local/bin/` (Linux) o `%LOCALAPPDATA%\codexc\bin\` (Windows: `codex01.cmd`, `codex.cmd`, `codexc.cmd`).
- Estado de la cuenta activa, cuenta predeterminada y directorios base.

### `codexc rm <alias>`
Elimina de forma segura un perfil y su directorio asociado en `~/.codexc_homes/` (Linux) o `%USERPROFILE%\.codexc_homes\` (Windows), además de su lanzador y caché, solicitando confirmación explícita para evitar pérdida accidental de datos.

### `codexc export [alias] [-o <archivo>]`
Exporta uno o todos los perfiles configurados (`auth.json` y `config.toml`, si existe) a un archivo JSON en formato `codexc-bundle-v1` protegido con permisos privados (`0600` en Linux):
- Si omites `alias`, exporta todos los perfiles en `codexc-accounts-bundle.json` (o la ruta indicada con `-o` / `--output`).
- Si indicas `alias` (ej. `codexc export codex01`), exporta únicamente ese perfil en `codexc-codex01.json` por defecto.

### `codexc import <archivo> [--alias <nuevo_alias>] [--overwrite]`
Importa perfiles desde un bundle `codexc-bundle-v1` en el equipo destino:
- Restaura `auth.json` y `config.toml`, enlaza `skills/` (symlink en Linux o NTFS Junction en Windows) y ejecuta `sync_launchers()`.
- Si no existían perfiles previos, establece automáticamente el primer alias importado como `active` y `default`.
- `--alias <nuevo_alias>`: renombra el alias destino al importar (válido únicamente cuando el bundle contiene exactamente 1 cuenta).
- `--overwrite`: permite reemplazar un perfil existente o actualizar credenciales duplicadas (`account_id` / `email`) cuando se resincroniza tras una rotación de tokens.

---

## 5. Aislamiento de Perfiles por `CODEX_HOME`

OpenAI Codex CLI respeta de manera nativa la variable de entorno `CODEX_HOME`. `codexc` aprovecha este diseño para estructurar el sistema de archivos de forma limpia en ambas plataformas:

### Rutas en Linux

```text
~/.codexc/
├── active                        ← Almacena el alias activo actual
├── default                       ← Almacena el alias predeterminado
└── cache/                        ← Caché privada con permisos 0700
    ├── codex01.json
    └── codex02.json

~/.codexc_homes/
├── codex01/                      ← Permisos 0700
│   ├── auth.json                 ← Tokens OAuth y ChatGPT ID (permisos 0600)
│   ├── config.toml               ← Configuración de modelo, TUI y MCPs
│   ├── state_5.sqlite            ← Historial de estados y conversaciones
│   ├── goals_1.sqlite            ← Objetivos persistentes del perfil
│   ├── logs_2.sqlite             ← Base de datos de logs locales
│   └── skills -> ~/.codex/skills ← Enlace simbólico a las skills globales
└── codex02/
    ├── auth.json                 ← Credenciales independientes
    └── ...
```

### Rutas en Windows 10/11

```text
%USERPROFILE%\.codexc\
├── active                        ← Alias activo para el wrapper 'codex.cmd'
├── default                       ← Alias predeterminado
├── bin\codexc                    ← Copia del CLI Python principal
├── lib\platform\                 ← Módulos de plataforma (win32.py, linux.py)
└── cache\                        ← Caché privada de cuotas
    ├── codex01.json
    └── codex02.json

%USERPROFILE%\.codexc_homes\
├── codex01\
│   ├── auth.json                 ← Credenciales OAuth2 del perfil
│   ├── config.toml               ← Configuración TOML copiada/propia
│   ├── skills -> %USERPROFILE%\.codex\skills  ← NTFS Junction (mklink /J)
│   └── (archivos de Codex CLI)   ← state_5.sqlite, goals_1.sqlite, logs_2.sqlite, locks
└── codex02\
    └── ...

%LOCALAPPDATA%\codexc\bin\
├── codexc.cmd                    ← Lanzador global de codexc
├── codex.cmd                     ← Wrapper global dinámico
├── codex01.cmd                   ← Lanzador dedicado para codex01
└── codex02.cmd                   ← Lanzador dedicado para codex02
```

### ¿Por qué compartir `skills/` mediante symlink o NTFS Junction?
Las skills y herramientas de asistencia son utilidades compartidas. En Linux `codexc` crea un enlace simbólico (`os.symlink`), mientras que en Windows crea un **NTFS Junction** mediante `cmd /c mklink /J <dst> <src>` en `lib/platform/win32.py`. A diferencia de los symlinks tradicionales en Windows, un *NTFS Junction* de directorio **no requiere privilegios de Administrador ni activar el Developer Mode**, permitiendo que cualquier skill nueva en `~/.codex/skills` (o `%USERPROFILE%\.codex\skills`) esté disponible al instante en todos los perfiles sin duplicación de almacenamiento.

### Resolución del binario de Codex en Windows (`codex.exe` / `codex.cmd` vs `codex.ps1`)
En instalaciones de Codex CLI mediante `npm` en Windows suelen coexistir `codex.ps1` y `codex.cmd`. Invocar `codex.ps1` desde subprocesos o scripts batch falla con frecuencia debido a políticas de ejecución (`ExecutionPolicy`) de PowerShell. Por ello, `get_real_codex_bin()` en `lib/platform/win32.py` sigue este orden estricto:
1. Busca el binario standalone `%USERPROFILE%\.codex\packages\standalone\current\bin\codex.exe`.
2. Consulta `shutil.which` para `codex.exe`, `codex.cmd` y `codex`: si encuentra un archivo `.ps1`, lo descarta y busca su hermano `.exe`, `.cmd` o `.bat` en el mismo directorio, ignorando siempre los wrappers propios dentro de `%LOCALAPPDATA%\codexc\bin` para evitar recursión infinita.
3. Si aún no lo halla, verifica rutas estándar como `%LOCALAPPDATA%\Author Software\nvm\.nodejs\codex.cmd` y `%APPDATA%\npm\codex.cmd`.
4. Cuando `codexc` invoca un `.cmd`/`.bat` mediante `subprocess` (por ejemplo al ejecutar `app-server`), `wrap_codex_command()` lo envuelve automáticamente con `["cmd", "/c", real_bin, *args]`.

---

## 6. Ejecución en Múltiples Paneles en Paralelo

El mayor beneficio del aislamiento radica en el **desarrollo concurrente**. En herramientas de multipaneleo como **Herdr**, tmux o zellij:

```text
┌──────────────────────────────────────┬──────────────────────────────────────┐
│ HERDR PANE 1                         │ HERDR PANE 2                         │
│ $ codex01                            │ $ codex02                            │
│                                      │                                      │
│ Cuenta: dev1@gmail.com               │ Cuenta: dev2@gmail.com               │
│ CODEX_HOME: ~/.codexc_homes/codex01  │ CODEX_HOME: ~/.codexc_homes/codex02  │
│ Tarea: Implementación de backend     │ Tarea: Testing y revisión de código  │
└──────────────────────────────────────┴──────────────────────────────────────┘
```

**Ventajas clave:**
1. **Cero colisión de locks:** Las bases de datos SQLite (`state_5.sqlite`, `goals_1.sqlite`) no compiten por bloqueos de escritura.
2. **Independencia de tokens:** Si una cuenta necesita renovar su `access_token`, el refresco ocurre de manera aislada sin invalidar la sesión del otro panel.
3. **Multiplicación de cuota:** Tienes a tu disposición la suma de las cuotas de 5 horas de todas tus cuentas activas.

---

## 7. Modo `--yolo` Automático e Inyección de Argumentos

Por defecto, los desarrolladores que utilizan lanzadores dedicados prefieren trabajar de forma fluida sin tener que responder "yes" a cada lectura de archivo o comando de terminal.

Los lanzadores generados por `codexc` (scripts Bash en `~/.local/bin/` en Linux o scripts `.cmd` como `codex01.cmd` y `codex.cmd` en `%LOCALAPPDATA%\codexc\bin\` en Windows) resuelven esto de forma inteligente:

1. **Inyección transparente:** Al escribir `codex01`, el lanzador fija `CODEX_HOME` y ejecuta internamente el binario real con `--yolo`:
   ```bash
   # Linux
   exec "$REAL_BIN" --yolo "${ARGS[@]}"
   ```
   ```cmd
   :: Windows
   call "%REAL_BIN%" --yolo %ARGS%
   ```
2. **Detección de subcomandos:** Subcomandos nativos como `doctor`, `login`, `features` o `app-server` rechazan la bandera `--yolo`. El lanzador detecta si el primer argumento posicional es un subcomando conocido (`KNOWN_SUBS`) y **omite** `--yolo` automáticamente para evitar errores.
3. **Opción `--no-yolo`:** Si en una sesión específica deseas supervisión paso a paso:
   ```bash
   codex01 --no-yolo
   ```
   El lanzador filtra `--no-yolo` (no lo reenvía al binario real), suprime el modo `--yolo` e inicia Codex con las solicitudes de aprobación habituales.

---

## 8. API de Cuotas de OpenAI ChatGPT y Monitoreo

`codexc` obtiene el consumo exacto consultando la misma API interna que utiliza la interfaz web de ChatGPT:

- **URL:** `https://chatgpt.com/backend-api/codex/usage`
- **Método:** `GET`
- **Encabezados:**
  - `Authorization: Bearer <access_token>`
  - `chatgpt-account-id: <account_id>`
  - `User-Agent: codex-cli/0.164.0`

### Estructura de la Respuesta

```json
{
  "rate_limit": {
    "primary_window": {
      "used_percent": 4.0,
      "limit_window_seconds": 18000,
      "reset_after_seconds": 5700,
      "reset_at": 1793234400.0
    },
    "secondary_window": {
      "used_percent": 53.0,
      "limit_window_seconds": 604800,
      "reset_after_seconds": 381600,
      "reset_at": 1793610300.0
    },
    "plan_type": "plus"
  }
}
```

- **`primary_window`:** Límite rodante de 5 horas (`18000` segundos). Es el medidor más sensible para desarrollo continuo.
- **`secondary_window`:** Límite semanal (`604800` segundos).
- **Caché atómico:** Los resultados se guardan en `~/.codexc/cache/<alias>.json` con un TTL de 60 segundos para evitar sobrecargar los servidores de OpenAI y garantizar respuestas instantáneas en la terminal.

---

## 9. Arquitectura de Renovación de Tokens (`app-server`)

Uno de los mayores desafíos en herramientas multi-cuenta es la expiración del `access_token` (vida útil típica de 1 hora).

### Enfoques descartados:
- **Refresco manual OAuth2:** Intentar contactar directamente a `https://auth.openai.com/oauth/token` compite con los procesos activos de Codex CLI, provocando carreras y sobreescrituras en disco.
- **Comandos de diagnóstico (`codex doctor`):** Aunque diagnostican el estado, no garantizan la rotación síncrona del token en memoria ni un protocolo de salida predecible.

### La solución de `codexc` (Commit `cd886a0`):
`codexc` delega la renovación directamente al motor interno de Codex mediante el protocolo **`app-server`**:

```text
[codexc] ──(stdio JSON-RPC)──> [codex app-server --listen stdio://]
                             ├── initialize (clientInfo)
                             └── account/read (refreshToken: true)
                                      │
                                      ▼
                        Motor nativo de Codex actualiza
                        auth.json y bases de datos con
                        bloqueo SQLite seguro
```

**Manejo robusto de I/O y Anti-Zombies:**
- **Linux / POSIX:** lectura no bloqueante mediante `os.set_blocking(fd, False)` y `select.select` con `os.read(fd, 8192)` (más respaldo con `readline()` cuando el stream no expone descriptor real).
- **Windows 10/11:** dado que `select.select` no opera sobre pipes de subprocesos en Windows, `attempt_native_token_refresh()` utiliza un hilo lector demonio (`threading.Thread`) que deposita líneas de `stdout` en `queue.Queue`, consumido con timeout bajo la misma ventana de **6 segundos**.
- **Limpieza incondicional en bloque `finally`:** cierra `stdin`, ejecuta `terminate()` → `wait(timeout=0.8)` y, si el proceso sigue vivo, ejecuta `kill()` → `wait(timeout=1.0)` para evitar procesos huérfanos o zombis.
- **Validación:** suite unitaria hermética multiplataforma con **16 tests** en [`tests/test_codexc.py`](../tests/test_codexc.py), ejecutable con `python -m unittest discover -s tests`.

---

## 10. Seguridad y Permisos del Sistema de Archivos

Las credenciales de acceso a ChatGPT contienen tokens capaces de realizar acciones en tu cuenta. Por esta razón, `codexc` aplica una política de **privilegio mínimo** adaptada a cada plataforma:

1. **Directorios de perfiles:** En Linux, `~/.codexc_homes/` y cada carpeta hija se crean con `0700` (`rwx------`). En Windows, se alojan bajo el perfil privado del usuario (`%USERPROFILE%\.codexc_homes\`).
2. **Archivos de credenciales:** Cada `auth.json` y `config.toml` se protege con `chmod 0600` (`rw-------`) en Linux; en Windows `set_private_file_permissions()` mantiene compatibilidad segura sin fallar cuando los bits POSIX no aplican sobre NTFS.
3. **Caché privada:** `~/.codexc/cache` (`0700` en Linux) o `%USERPROFILE%\.codexc\cache` (`NTFS privado` en Windows) resguarda los archivos `<alias>.json`.
4. **Validación estricta de alias:** Los nombres de perfiles se validan contra la expresión regular `^[a-zA-Z0-9_-]{1,32}$`, bloqueando cualquier intento de inyección de rutas (`path traversal`) o caracteres especiales.

---

## 11. Diagnóstico, Troubleshooting y `codexc doctor`

Si en algún momento experimentas un comportamiento inesperado, ejecuta:

```bash
codexc doctor
```

El diagnóstico comprueba:
- [x] Si el ejecutable real de Codex existe y responde (`codex` en Linux; `.exe`/`.cmd` válido en Windows, descartando `.ps1`).
- [x] Que los directorios de perfiles y caché existan con su estado de seguridad (`0700` en Linux / `NTFS privado` en Windows).
- [x] Que cada perfil disponga de su directorio, `auth.json` y lanzador ejecutable (`~/.local/bin/<alias>` en Linux o `%LOCALAPPDATA%\codexc\bin\<alias>.cmd` en Windows).
- [x] Cuál es la cuenta activa y la cuenta predeterminada.

### Problemas comunes y soluciones

#### 1. "Error 401 Unauthorized" al consultar cuotas
- **Causa:** El `access_token` expiró y el `refresh_token` requiere renovación.
- **Solución:** Ejecuta `codexc list --refresh`. `codexc` invocará automáticamente la renovación nativa por `app-server`. Si tu sesión fue cerrada desde la web de OpenAI, ejecuta `codexc add <alias>` para volver a vincularla.

#### 2. Mi terminal no encuentra el comando `codex01` o `codexc`
- **En Linux:** `~/.local/bin` no está presente en tu variable `$PATH`.
  ```bash
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
  source ~/.bashrc
  ```
- **En Windows:** abre una **nueva terminal** tras ejecutar `install.cmd` / `install.ps1`, o recarga el `Path` en la misma sesión de PowerShell:
  ```powershell
  $env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")
  ```
  Verifica también que `%LOCALAPPDATA%\codexc\bin` figure en tu variable `Path` de usuario.

#### 3. En PowerShell aparece error de `ExecutionPolicy` al instalar o ejecutar Codex
- **Causa:** PowerShell bloquea scripts `.ps1` si `ExecutionPolicy` está restringida.
- **Solución:** Para instalar `codexc`, ejecuta `install.cmd` desde CMD (invoca `powershell -NoProfile -ExecutionPolicy Bypass -File install.ps1`). Para los lanzadores en tiempo de ejecución, `codexc` resuelve `codex.exe` o `codex.cmd` y genera wrappers `.cmd` (`codex.cmd`, `codex01.cmd`, `codexc.cmd`), evitando `codex.ps1`.

#### 4. Quiero ingresar a una cuenta sin modo `--yolo`
- **Solución:** Simplemente agrega el flag `--no-yolo`:
  ```bash
  codex01 --no-yolo
  ```

---

## 12. Integración con Agentes Autónomos (Skill para Herdr)

`codexc` incluye una skill pre-configurada para que coordinadores de IA y agentes de desarrollo puedan interactuar con el conmutador.

Ubicación de la skill:
```text
skills/codexc/SKILL.md
```

### Funciones habilitadas para los agentes:
- Inspección de saldos antes de lanzar tareas complejas de razonamiento (`codexc list --json`).
- Selección de la cuenta con mayor saldo para tareas extensas (`codexc auto`).
- Aislamiento de agentes supervisores y agentes ejecutores en terminales paralelas de Herdr.

---

## 13. Historia de Versiones y Decisiones de Diseño

### v1.0 (27 de Octubre de 2026)
- Creación de la arquitectura base de aislamiento mediante `$CODEX_HOME`.
- Lanzadores independientes en `~/.local/bin/` (`codex01`, `codex02`).
- Conexión con la API de OpenAI ChatGPT para lectura de ventanas de 5H y semanal.
- Wrapper inteligente para el comando global `codex`.

### v1.1 (28 de Octubre de 2026)
- **Auditoría de seguridad:** Restricción de permisos a `0700` y `0600`.
- Detección estricta de cuentas duplicadas por `account_id`.
- Protección contra inyección de nombres y caracteres reservados en alias.
- Migración de caché a `~/.codexc/cache` privado.

### v1.2 (28 de Octubre de 2026)
- **Renovación nativa:** Delegación de refresco de tokens al protocolo `app-server` de Codex CLI (`account/read` con `refreshToken=true`).
- **I/O no bloqueante:** Implementación de `select.select` con límite de 6 segundos y recolección forzosa anti-zombis.
- **Lanzadores `--yolo`:** Inyección por defecto de modo auto-aprobación con detección inteligente de subcomandos nativos y bandera `--no-yolo`.

### v1.3 (Noviembre de 2026)
- **Soporte nativo Windows 10/11 + Linux:** Capa de plataforma en [`lib/platform/`](../lib/platform/__init__.py) (`linux.py` y `win32.py`).
- **Instalador Windows:** [`install.ps1`](../install.ps1) e [`install.cmd`](../install.cmd) con configuración automática de `%USERPROFILE%\.codexc`, `%USERPROFILE%\.codexc_homes` y `%LOCALAPPDATA%\codexc\bin` en el `Path` del usuario.
- **Lanzadores `.cmd` y enlaces Junction:** Generación de `codex01.cmd`, `codex.cmd` y `codexc.cmd`; enlaces NTFS Junction (`mklink /J`) para `skills/`; resolución de `codex.exe`/`codex.cmd` evitando `codex.ps1`.
- **Concurrencia portable en `app-server`:** Lector `threading.Thread` + `queue.Queue` en Windows manteniendo `select.select` en Linux.
- **Portabilidad entre equipos (`export` / `import`):** Subcomandos `codexc export [alias] [-o <archivo>]` (formato `codexc-bundle-v1`) y `codexc import <archivo> [--alias <nuevo_alias>] [--overwrite]` para migrar perfiles entre Windows y Linux sin re-autenticar.
- **Suite unitaria multiplataforma:** [`tests/test_codexc.py`](../tests/test_codexc.py) con **16 tests** en verde (`python -m unittest discover -s tests`).

---

## Licencia

Distribuido bajo la licencia MIT.  
Copyright (c) 2026 Mikail Russbell Castro Jara.
