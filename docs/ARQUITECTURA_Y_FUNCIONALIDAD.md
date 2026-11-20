# Arquitectura y Funcionalidad de `codexc`

> **Documento técnico de referencia** — Basado en la implementación actual de [`bin/codexc`](../bin/codexc), [`lib/platform/`](../lib/platform/__init__.py), [`install.sh`](../install.sh), [`install.ps1`](../install.ps1), [`install.cmd`](../install.cmd), [`tests/test_codexc.py`](../tests/test_codexc.py) y [`skills/codexc/SKILL.md`](../skills/codexc/SKILL.md).  
> **Plataformas soportadas:** Linux x86_64 y Windows 10/11 | **Python:** 3.10+ (biblioteca estándar, cero dependencias externas)

---

## 1. Visión general y mapa de componentes

`codexc` es un administrador multi-cuenta y aislador de perfiles para **OpenAI Codex CLI**. Su objetivo es permitir el uso simultáneo y sin colisiones de múltiples suscripciones (por ejemplo `codex01`, `codex02`, ...) en paneles paralelos, monitorear el consumo de cuotas en tiempo real y rotar automáticamente la cuenta activa en **Linux** y **Windows 10/11**.

| Componente | Ubicación en repo / sistema | Responsabilidad |
|---|---|---|
| **CLI principal** | [`bin/codexc`](../bin/codexc) → `~/.local/bin/codexc` (Linux) o `%USERPROFILE%\.codexc\bin\codexc` + `codexc.cmd` (Windows) | Script Python 3 puro (1537 líneas) que gestiona perfiles, cuotas, caché, renovación nativa de tokens, exportación/importación portable, lanzadores y diagnósticos. |
| **Capa de plataforma** | [`lib/platform/__init__.py`](../lib/platform/__init__.py), [`linux.py`](../lib/platform/linux.py), [`win32.py`](../lib/platform/win32.py) | Selecciona mediante `IS_WINDOWS = os.name == "nt"` las operaciones nativas de rutas, enlaces (`os.symlink` vs `mklink /J`), permisos, detección de binario real y envoltura de subprocesos. |
| **Lanzadores fijos** | `~/.local/bin/codex01`, `codex02` (Linux) / `%LOCALAPPDATA%\codexc\bin\codex01.cmd`, `codex02.cmd` (Windows) | Wrappers Bash o `.cmd` generados por `sync_launchers()`. Fijan `CODEX_HOME` al perfil correspondiente e inyectan `--yolo` de forma inteligente. |
| **Wrapper global** | `~/.local/bin/codex` (Linux) / `%LOCALAPPDATA%\codexc\bin\codex.cmd` (Windows) | Wrapper dinámico administrado por `codexc`. Si `CODEX_HOME` no está definido, resuelve el perfil desde `active` → `default` → `codex01` y aplica la misma lógica de `--yolo`. |
| **Instaladores** | [`install.sh`](../install.sh) (Linux), [`install.ps1`](../install.ps1) e [`install.cmd`](../install.cmd) (Windows) | Validan Python 3.10+ y Codex CLI, crean directorios base, instalan ejecutables/lanzadores (y `Path` de usuario en Windows), registran la skill y ejecutan `codexc doctor` (y `unittest` en Windows). |
| **Skill para agentes** | [`skills/codexc/SKILL.md`](../skills/codexc/SKILL.md) | Instrucciones operativas para que agentes autónomos consulten saldos (`list --json`, `quota`), roten cuentas (`auto`, `switch`) y usen lanzadores paralelos. |
| **Suite de pruebas** | [`tests/test_codexc.py`](../tests/test_codexc.py) | Suite unitaria hermética multiplataforma (`unittest`) ejecutable con `python -m unittest discover -s tests`. |

---

## 2. Modelo de almacenamiento y aislamiento nativo por `CODEX_HOME`

### Estructura de directorios y archivos

`codexc` resuelve el directorio raíz mediante `REAL_HOME = resolve_real_home()`:
- En **Linux** (`lib/platform/linux.py`): toma `CODEX_REAL_HOME`, `os.path.expanduser("~")` (si no es `"~"` ni `"/root"`), o `"/home/aidev"`. Los ejecutables y wrappers se ubican en `LOCAL_BIN_DIR = ~/.local/bin`.
- En **Windows 10/11** (`lib/platform/win32.py`): toma `CODEX_REAL_HOME` o `os.path.expanduser("~")` (`%USERPROFILE%`). Los lanzadores `.cmd` se ubican en `LOCAL_BIN_DIR = %LOCALAPPDATA%\codexc\bin` (o `%USERPROFILE%\.local\bin` si `LOCALAPPDATA` no está definido).

En ambos sistemas organiza el estado y los perfiles en árboles separados:

```text
REAL_HOME/                            (~ en Linux | %USERPROFILE% en Windows)
├── .codexc/                          # Estado global y caché de codexc
│   ├── active                        # Alias actualmente activo para el wrapper 'codex'
│   ├── default                       # Alias predeterminado de respaldo
│   ├── bin/codexc                    # (Windows) Copia instalada de bin/codexc
│   ├── lib/platform/                 # (Windows) Copia instalada de la capa de plataforma
│   └── cache/                        # 0700 en Linux | directorio privado bajo perfil en Windows
│       ├── codex01.json              # Caché atómico de cuotas (0600 en Linux, TTL 60s)
│       └── codex02.json
│
├── .codexc_homes/                    # Perfiles aislados de Codex CLI (0700 en Linux)
│   ├── codex01/                      # Directorio aislado del perfil
│   │   ├── auth.json                 # Credenciales OAuth2 de OpenAI (0600 en Linux)
│   │   ├── config.toml               # Configuración TOML copiada/propia del perfil
│   │   ├── skills -> ~/.codex/skills # Symlink (Linux) o NTFS Junction mklink /J (Windows)
│   │   └── (archivos de Codex CLI)   # state_5.sqlite, goals_1.sqlite, logs_2.sqlite, sesiones, locks
│   └── codex02/
│       └── ...
│
├── .local/bin/                       # Linux: directorio de ejecutables y wrappers Bash
│   ├── codexc -> .../bin/codexc      # Symlink al script principal
│   ├── codex                         # Wrapper global dinámico Bash
│   ├── codex01                       # Lanzador dedicado Bash para codex01
│   └── codex02                       # Lanzador dedicado Bash para codex02
│
└── AppData/Local/codexc/bin/         # Windows (%LOCALAPPDATA%\codexc\bin\): wrappers .cmd
    ├── codexc.cmd                    # Invoca "<sys.executable>" "<codexc>" %*
    ├── codex.cmd                     # Wrapper global dinámico .cmd
    ├── codex01.cmd                   # Lanzador dedicado .cmd para codex01
    └── codex02.cmd                   # Lanzador dedicado .cmd para codex02
```

### Validación de alias y listado (`validate_alias` y `list_aliases`)

- **`validate_alias(alias)`**:
  - Rechaza valores vacíos o no `str` y aplica `.strip()`.
  - Exige coincidencia con `^[a-zA-Z0-9_-]{1,32}$` (`ALIAS_REGEX`) para impedir *path traversal* o caracteres especiales.
  - Bloquea nombres reservados (`RESERVED_NAMES`): `codex`, `codexc`, `active`, `default`, `current`, `bin`, `skills`, `packages`, `cache`, `null`, `all`.
- **`list_aliases()`**:
  - Recorre `~/.codexc_homes/` y considera válidos los subdirectorios cuyo nombre comienza por `"codex"` (`entry.startswith("codex")`), no pertenece a `RESERVED_NAMES` y contiene un archivo `auth.json`.

### Detección de cuentas duplicadas (`cmd_add`)

Al vincular una cuenta nueva con `codexc add`:
1. Tras completar `codex login`, consulta `fetch_codex_usage(alias, force_refresh=True)` para obtener `email` y `account_id`.
2. Recorre todos los alias ya registrados y compara:
   - `account_id == other_acc` (si ambos existen), o
   - `email.lower() == other_email.lower()` (si ambos existen).
3. Si detecta coincidencia, aborta con error y elimina el directorio recién creado (`shutil.rmtree(prof_dir, ignore_errors=True)`) para impedir perfiles redundantes que consuman la misma cuota.

### Por qué `codexc` no necesita sobrescribir `$HOME`

A diferencia de otras herramientas (como `agyc`) que deben reescribir `$HOME` para aislar configuraciones de escritorio, **OpenAI Codex CLI respeta de forma nativa la variable de entorno `CODEX_HOME`**. Al exportar únicamente `CODEX_HOME=~/.codexc_homes/<alias>`, Codex CLI aísla credenciales (`auth.json`), configuración (`config.toml`) y bases de datos SQLite por perfil manteniendo intacto el `$HOME` real del usuario (clave para SSH, Git, herramientas de compilación y rutas de proyecto).

---

## 3. Lanzadores paralelos e inyección inteligente de `--yolo`

La función `sync_launchers()` genera y mantiene actualizados (usando `_write_launcher_if_changed()`, que compara contenido normalizando `\r\n` para evitar escrituras redundantes) los lanzadores según `IS_WINDOWS`:

### Lanzadores dedicados vs Wrapper global (`codex` / `codex.cmd`) y `codexc`

- **En Linux (`IS_WINDOWS == False`):**
  - **Lanzadores dedicados (`~/.local/bin/codex01`, `codex02`, ...)**: generados por `_build_bash_launcher()`, exportan `export CODEX_HOME="<prof_dir>"` y ejecutan el binario real con detección de `--yolo`.
  - **Wrapper global (`~/.local/bin/codex`)**: generado por `_build_bash_wrapper()`, solo asigna `CODEX_HOME` si `[ -z "$CODEX_HOME" ]`, resolviendo `ACTIVE_FILE` → `DEFAULT_FILE` → `"codex01"`.
  - **Enlace global (`~/.local/bin/codexc`)**: symlink hacia `bin/codexc`.
- **En Windows (`IS_WINDOWS == True`):**
  - **Lanzadores dedicados (`%LOCALAPPDATA%\codexc\bin\codex01.cmd`, `codex02.cmd`, ...)**: scripts batch con saltos CRLF (`\r\n`) que ejecutan `setlocal`, `set "CODEX_HOME=<prof_dir>"` y el bloque `_build_cmd_launcher_body(real_bin)`.
  - **Wrapper global (`%LOCALAPPDATA%\codexc\bin\codex.cmd`)**: verifica `if not defined CODEX_HOME`, lee `ACTIVE_FILE` o `DEFAULT_FILE` (con respaldo `"codex01"`) mediante `set /p ACTIVE=<...>` y asigna `CODEX_HOME` si existe el directorio del perfil antes de ejecutar `_build_cmd_launcher_body(real_bin)`.
  - **Lanzador principal (`%LOCALAPPDATA%\codexc\bin\codexc.cmd`)**: invoca `"<sys.executable>" "<current_script>" %*`.

### Resolución del binario real (`get_real_codex_bin`) y `wrap_codex_command`

Delegada a la capa `lib/platform/`:
- **Linux (`lib/platform/linux.py`):**
  1. `~/.codex/packages/standalone/current/bin/codex` (si existe y es ejecutable).
  2. `shutil.which("codex")`, excluyendo `~/.local/bin/codex` para evitar recursión infinita contra el wrapper.
  3. Ruta fallback standalone (`~/.codex/packages/standalone/releases/0.164.0-x86_64-unknown-linux-musl/bin/codex`).
- **Windows (`lib/platform/win32.py`):**
  1. `%USERPROFILE%\.codex\packages\standalone\current\bin\codex.exe` (si existe).
  2. `shutil.which` en orden `("codex.exe", "codex.cmd", "codex")` pasado por `_resolve_non_ps1_candidate(cand, local_bin_dir)`: descarta cualquier archivo dentro de `LOCAL_BIN_DIR` (`_is_inside_dir`) y evita scripts `.ps1` buscando hermanos `.exe`, `.cmd` o `.bat` en el mismo directorio (previniendo fallos de `ExecutionPolicy` en PowerShell).
  3. Rutas extra estándar: `%LOCALAPPDATA%\Author Software\nvm\.nodejs\codex.cmd` y `%APPDATA%\npm\codex.cmd`.
  4. Fallback a la ruta standalone `codex.exe`.
- **`wrap_codex_command(real_bin, args)`:** en Linux retorna `[real_bin, *args]`; en Windows envuelve archivos `.cmd`/`.bat` con `["cmd", "/c", real_bin, *args]` para que `subprocess.Popen` pueda ejecutarlos correctamente.

### Detección de subcomandos (`KNOWN_SUBS`) y manejo de flags

Tanto los lanzadores Bash en Linux como `_build_cmd_launcher_body()` en los `.cmd` de Windows procesan todos los argumentos antes de invocar al binario real:

1. **Flags reconocidas**:
   - `--yolo` o `--dangerously-bypass-approvals-and-sandbox` marcan `has_yolo` / `HAS_YOLO=1` (se preservan en los argumentos).
   - `--no-yolo` marca `has_no_yolo` / `HAS_NO_YOLO=1` y **se filtra** (no se reenvía al binario real de Codex).
   - Cualquier otro flag o argumento del usuario se conserva intacto.
2. **Detección de subcomandos (`KNOWN_SUBS_STR`)**:
   El primer argumento posicional (que no comience por `-`) se busca en la lista `KNOWN_SUBS`:
   ```text
   agents, exec, review, login, logout, mcp, plugin, app-server,
   remote-control, completion, update, doctor, sandbox, debug, apply,
   resume, queue, archive, delete, migrate-rollouts, migrate-nfs-db,
   unarchive, fork, cloud, exec-server, features, help
   ```
   Si coincide, se marca `is_subcmd` / `IS_SUBCMD=1` (`findstr /L /C:" %FIRST_POS% "` en `.cmd`).
3. **Regla de ejecución**:
   - Si no se pasó `--no-yolo`, ni `--yolo`, ni es subcomando conocido: invoca al binario real anteponiendo `--yolo` (`exec "$REAL_BIN" --yolo "${ARGS[@]}"` en Bash o `call "%REAL_BIN%" --yolo %ARGS%` en `.cmd`).
   - En cualquier otro caso: ejecuta el binario real con los argumentos originales sin añadir `--yolo`.

### Comportamiento de `resume` y `fork` entre perfiles

Tanto `resume` como `fork` están incluidos en `KNOWN_SUBS`, por lo que los lanzadores no les inyectan `--yolo` de forma automática. Debido a que cada perfil opera bajo su propio `$CODEX_HOME` con su propia base SQLite (`state_5.sqlite`) y almacenamiento de sesiones/locks, las sesiones pertenecen al perfil donde fueron creadas (`codex01` no mezcla sus hilos ni locks con `codex02`).

---

## 4. Autenticación OAuth2 y Motor Nativo `codex app-server` JSON-RPC

### Flujo de vinculación y migración inicial

- **Registro nuevo (`codexc add [alias] [--device-auth]`)**:
  1. Si se omite `alias`, calcula el primer correlativo libre `codex01`, `codex02`, ...
  2. Comprueba que el alias no exista aún ni tenga `auth.json`.
  3. Crea el directorio del perfil mediante `ensure_private_dir(prof_dir)`, copia `config.toml` con `set_private_file_permissions()` si existe en `SYSTEM_CODEX_DIR` y enlaza `skills` mediante `create_dir_link(skills_src, skills_dst)` (symlink en Linux o NTFS Junction `mklink /J` en Windows).
  4. Ejecuta `wrap_codex_command(real_bin, ["login", ...])` (añadiendo `--device-auth` para entornos headless/SSH) con `CODEX_HOME` apuntando al nuevo perfil.
  5. Si el usuario cancela o `auth.json` no se genera, elimina el directorio del perfil para no dejar residuos.
  6. Aplica `set_private_file_permissions(auth_file)`, verifica duplicados (`email` + `account_id`), sincroniza lanzadores y activa el nuevo perfil.
- **Migración automática no destructiva (`ensure_auto_migration`)**:
  Si no hay ningún perfil registrado todavía (`list_aliases()` vacío) pero existe `auth.json` en `SYSTEM_CODEX_DIR`, `codexc` lo copia a `codex01` aplicando `set_private_file_permissions()`, copia `config.toml` si existe, enlaza `skills` con `create_dir_link()`, establece `codex01` como `active` y `default`, y genera los lanzadores.

### Consulta de cuotas en vivo y renovación delegada en `codex app-server`

`fetch_codex_usage(alias, force_refresh=False, retry_on_401=True)` obtiene el estado de la cuenta:

1. **Consulta HTTP de cuotas**:
   Realiza `GET https://chatgpt.com/backend-api/codex/usage` (timeout 8s) con:
   - `Authorization: Bearer <access_token>` (leído de `auth.json`)
   - `chatgpt-account-id: <account_id>` (si está presente)
   - `User-Agent: codex-cli/0.164.0`
2. **Renovación automática ante `HTTP 401` (`attempt_native_token_refresh`)**:
   En lugar de refrescar tokens manualmente compitiendo con sesiones activas, `codexc` delega la renovación en el subproceso nativo de Codex CLI:
   - Lanza `wrap_codex_command(real_bin, ["app-server", "--listen", "stdio://"])` con `CODEX_HOME=prof_dir` (en Windows envuelve `.cmd`/`.bat` con `cmd /c`).
   - Envía por `stdin` dos peticiones JSON-RPC delimitadas por salto de línea:
     ```json
     {"id": 1, "method": "initialize", "params": {"clientInfo": {"name": "codexc", "version": "1.0.0"}}}
     {"id": 2, "method": "account/read", "params": {"refreshToken": true}}
     ```
   - Lee `stdout` sin bloqueos indefinidos bajo un límite estricto de **6.0 segundos** (`deadline = 6.0`), evaluando cada línea con `_parse_account_refresh_line()`:
     - **Windows (`IS_WINDOWS` o `select is None`)**: lanza un hilo lector demonio (`threading.Thread`, `_reader_worker`) que lee `p.stdout.readline()` y deposita los bytes en `queue.Queue` (`line_queue`); el hilo principal consume mediante `line_queue.get(timeout=min(0.2, remaining))`.
     - **Linux (`select` disponible)**: configura `os.set_blocking(fd, False)` y usa `select.select([fd], [], [], min(0.2, remaining))` + `os.read(fd, 8192)` acumulando en `buffer` (con respaldo `readline()` si el stream no expone descriptor real).
   - Cuando `_parse_account_refresh_line()` recibe la respuesta JSON-RPC con `"id": 2` y `result.account` presente, da por exitosa la renovación y reintenta `fetch_codex_usage(..., force_refresh=True, retry_on_401=False)` una única vez.
   - En el bloque `finally`, cierra `stdin` y garantiza la recolección del proceso hijo: `terminate()` → `wait(timeout=0.8)` y, si sigue vivo, `kill()` → `wait(timeout=1.0)`, evitando procesos zombis.

### Caché local, normalización y countdowns

- **Caché atómico (`TTL = 60s`)**: las métricas se escriben en `CACHE_DIR/<alias>.json.tmp.<pid>`, se protegen con `set_private_file_permissions()` y se reemplazan atómicamente con `os.replace()`.
- **Normalización de ventanas**:
  - `primary_window` (ventana de 5 horas) y `secondary_window` (ventana semanal) calculan:
    `remaining_fraction = max(0.0, min(1.0, (100.0 - float(used_percent)) / 100.0))`
  - Si `used_percent` es `None` o la ventana no viene informada, se mantiene en `None` (`N/A`) sin asumir `100%`.
- **Countdowns dinámicos**: tanto al consultar en vivo como al leer del caché dentro del TTL de 60s, recalcula `reset_after_seconds = max(0, reset_at - now_ts)` y formatea la cadena (`Xd XXh`, `Xh XXm`, `Xm` o `Disponible` si `<= 0`).

---

## 5. Comandos y Flujos Operativos

| Comando | Comportamiento verificado en `bin/codexc` |
|---|---|
| `codexc` / `codexc list` | Ejecuta `ensure_auto_migration()` y `sync_launchers()`. Muestra tabla con alias, email, plan, estado (`*ACTIVA+DEF`, `* ACTIVA`, `DEFAULT`, `LISTA`) y barras visuales 5H / Semanal. |
| `codexc list --refresh` (`-r`) | Fuerza `force_refresh=True`, ignorando el caché de 60s para consultar la API en vivo. |
| `codexc list --json` | Imprime JSON con `active_account`, `default_account` y `accounts` (metadatos de uso y ventanas, sin incluir `access_token` ni secretos de `auth.json`). |
| `codexc switch <alias>` / `codexc <alias>` | Valida el alias, actualiza `~/.codexc/active` y muestra el correo asociado. (`switch` además invoca `sync_launchers()`). |
| `codexc default <alias>` | Valida que el alias exista y actualiza `~/.codexc/default`. |
| `codexc auto` | Fuerza consulta en vivo (`force_refresh=True`) de todas las cuentas. Descarta cuentas con error de auth, `limit_reached=True`, `allowed=False`, semanal agotada (`<= 0.001`) o 5H agotada (`<= 0.001`). Selecciona la cuenta válida con mayor `remaining_fraction` en la ventana de **5 horas** y la marca en `active`. |
| `codexc quota [alias]` | Consulta en vivo (`force_refresh=True`) el detalle de 5H y Semanal (porcentaje restante, consumido y tiempo de reinicio) del alias indicado o del activo. |
| `codexc doctor` | Ejecuta migración automática y `sync_launchers()`. Verifica existencia del binario real de Codex, permisos `0700` de `CACHE_DIR`, cuenta activa/default y estado (`dir`, `auth`, `launcher` ejecutable) de cada perfil. |
| `codexc rm <alias>` | Solicita confirmación (`[s/N]`), borra `~/.codexc_homes/<alias>`, el lanzador en `~/.local/bin/<alias>` y el caché `<alias>.json`. Reasigna `active` y `default` al primer perfil restante (o los elimina si no quedan perfiles) y sincroniza lanzadores. |
| `codexc export [alias] [-o <archivo>]` | Ejecuta `cmd_export()`: exporta uno o todos los perfiles (`auth.json` y `config.toml` si existe) en un bundle JSON con `"format": "codexc-bundle-v1"`, `"exported_at"` (UTC) y `"accounts"`, protegido con `set_private_file_permissions()`. Salida por defecto: `codexc-<alias>.json` o `codexc-accounts-bundle.json`. |
| `codexc import <archivo> [--alias <nuevo>] [--overwrite]` | Ejecuta `cmd_import()`: valida `codexc-bundle-v1`, previene colisiones por alias o identidad (`_extract_auth_identity()` / `_get_existing_profile_identity()`) salvo con `--overwrite`, permite renombrar con `--alias` en bundles de 1 cuenta, escribe `auth.json`/`config.toml`, enlaza `skills/` con `create_dir_link()`, ejecuta `sync_launchers()` y configura `active`/`default` si no existían perfiles previos. |

### Portabilidad entre equipos (`codexc-bundle-v1`) y rotación de `refresh_token`

Los comandos `export` e `import` permiten migrar vinculaciones entre **Windows ↔ Ubuntu Linux** sin repetir `codexc add` en la máquina destino. El flujo recomendado consiste en exportar el bundle, transferirlo por un canal cifrado (por ejemplo `scp`), importarlo en el destino y eliminar el archivo temporal en ambos equipos.

> **Nota sobre concurrencia de sesiones:** Dado que OpenAI puede rotar el `refresh_token` al renovar un `access_token`, si ambos equipos operan simultáneamente sobre la misma cuenta importada, la renovación en una máquina puede invalidar el `refresh_token` de la otra; en tal caso se debe re-exportar e importar con `--overwrite` o asignar cuentas separadas por equipo.

---

## 6. Implementación Multiplataforma (`lib/platform/`) y Validación (`tests/test_codexc.py`)

El soporte nativo para **Linux** y **Windows 10/11** está implementado mediante la capa [`lib/platform/__init__.py`](../lib/platform/__init__.py), que expone una interfaz unificada seleccionando [`lib/platform/linux.py`](../lib/platform/linux.py) o [`lib/platform/win32.py`](../lib/platform/win32.py) según `IS_WINDOWS = os.name == "nt"`:

| Pieza / Mecanismo | Implementación en Linux (`linux.py`) | Implementación en Windows 10/11 (`win32.py`) |
|---|---|---|
| **Directorio base (`resolve_real_home`)** | `CODEX_REAL_HOME`, `os.path.expanduser("~")` (si no es `"~"` ni `"/root"`), o `"/home/aidev"`. | `CODEX_REAL_HOME` o `os.path.expanduser("~")` (`%USERPROFILE%`). |
| **Directorio de lanzadores (`get_local_bin_dir`)** | `~/.local/bin` | `%LOCALAPPDATA%\codexc\bin` (con respaldo `~/.local/bin` si `LOCALAPPDATA` no existe). |
| **Binario real (`get_real_codex_bin`)** | `~/.codex/packages/standalone/current/bin/codex`, `shutil.which("codex")` (excluyendo wrapper) o fallback standalone. | `%USERPROFILE%\.codex\...\codex.exe`, `shutil.which` (`codex.exe`, `codex.cmd`, `codex`) filtrando `.ps1` y `LOCAL_BIN_DIR` via `_resolve_non_ps1_candidate()`, o rutas de `nvm`/`npm` (`codex.cmd`). |
| **Lanzadores y wrappers (`sync_launchers`, `get_launcher_path`)** | Scripts Bash (`0755`) en `~/.local/bin/codex01`, `codex` y symlink `codexc`. | Wrappers `.cmd` (`codex01.cmd`, `codex.cmd`, `codexc.cmd`) en `%LOCALAPPDATA%\codexc\bin` con `set "CODEX_HOME=..."`, `KNOWN_SUBS`, `--yolo` y `--no-yolo`. |
| **Invocación en subprocesos (`wrap_codex_command`)** | `[real_bin, *args]` | Antepone `["cmd", "/c", real_bin, *args]` cuando `real_bin` termina en `.cmd` o `.bat`. |
| **Enlace compartido de `skills/` (`create_dir_link`)** | `os.symlink(src, dst)` hacia `~/.codex/skills`. | **NTFS Junction** mediante `cmd /c mklink /J <dst> <src>` (no requiere privilegios de Administrador ni Developer Mode). |
| **I/O no bloqueante con `app-server`** | `os.set_blocking(fd, False)` + `select.select([fd], ...)` + `os.read(fd, 8192)`. | Hilo lector demonio `threading.Thread` (`_reader_worker`) leyendo `p.stdout.readline()` hacia `queue.Queue` con timeout, manteniendo el límite de 6.0s y recolección en `finally`. |
| **Permisos y estado (`ensure_private_dir`, `get_dir_security_status`)** | `0700` para directorios privados, `0600` para archivos sensibles (`"0700"` / `"aviso"` en `doctor`). | Directorios privados bajo `%USERPROFILE%`, `os.chmod(path, 0o600)` tolerante a NTFS y estado `"NTFS privado"` / `"aviso"` en `doctor`. |

### Suite de pruebas unitarias ([`tests/test_codexc.py`](../tests/test_codexc.py))

La verificación automatizada se implementa en [`tests/test_codexc.py`](../tests/test_codexc.py) con **16 tests** usando `unittest` y directorios temporales herméticos (`CodexcTestCase`) sin tocar perfiles reales ni realizar llamadas de red reales:

- `TestValidateAliasAndList` (3 tests): validación de alias, rechazo de nombres reservados/inseguros y filtrado en `list_aliases()`.
- `TestAutoMigration` (1 test): migración no destructiva hacia `codex01` y enlace de `skills/` (`ensure_auto_migration()`).
- `TestNativeTokenRefresh` (2 tests): pruebas de `attempt_native_token_refresh()` con pipe real en hilo escritor y respuesta JSON-RPC sin cuenta.
- `TestSyncLaunchers` (2 tests): generación de wrappers `.cmd` en Windows (incluyendo ejecución real con `cmd /c` en Windows para `--yolo`, `--no-yolo` y subcomandos `exec`) y generación de scripts Bash en Linux.
- `TestFetchUsageAndRotation` (4 tests): lectura de caché dentro del TTL de 60s, flujo `HTTP 401` → `attempt_native_token_refresh()` → reintento, selección óptima en `cmd_auto` y limpieza en `cmd_rm`.
- `TestExportAndImport` (3 tests): exportación individual e importación con `--alias`, rechazo de duplicados/existentes sin `--overwrite` y actualización con `--overwrite`, y exportación completa con nombre por defecto `codexc-accounts-bundle.json`.
- `TestWin32PlatformHelpers` (1 test): verificación de que `platform_win32.get_real_codex_bin()` ignora `.ps1` y el wrapper propio en `local_bin`, resolviendo `codex.cmd` real.

Ejecución en Linux o Windows:

```bash
python -m unittest discover -s tests
```
