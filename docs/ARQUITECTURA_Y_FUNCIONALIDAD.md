# Arquitectura y Funcionalidad de `codexc`

> **Documento técnico de referencia** — Basado en la implementación actual de `bin/codexc`, `install.sh` y `skills/codexc/SKILL.md`.  
> **Plataforma actual:** Linux x86_64 | **Python:** 3.10+ (biblioteca estándar, cero dependencias externas)

---

## 1. Visión general y mapa de componentes

`codexc` es un administrador multi-cuenta y aislador de perfiles para **OpenAI Codex CLI**. Su objetivo es permitir el uso simultáneo y sin colisiones de múltiples suscripciones (por ejemplo `codex01`, `codex02`, ...) en paneles paralelos, monitorear el consumo de cuotas en tiempo real y rotar automáticamente la cuenta activa.

| Componente | Ubicación en repo / sistema | Responsabilidad |
|---|---|---|
| **CLI principal** | [`bin/codexc`](../bin/codexc) → `~/.local/bin/codexc` | Script Python 3 puro (1143 líneas) que gestiona perfiles, cuotas, caché, renovación nativa de tokens, lanzadores y diagnósticos. |
| **Lanzadores fijos** | `~/.local/bin/codex01`, `codex02`, ... | Scripts Bash generados automáticamente por `sync_launchers()`. Fijan `CODEX_HOME` al perfil correspondiente e inyectan `--yolo` de forma inteligente. |
| **Wrapper global** | `~/.local/bin/codex` | Script Bash administrado por `codexc`. Si `CODEX_HOME` no está definido, resuelve el perfil desde `active` → `default` → `codex01` y aplica la misma lógica de `--yolo`. |
| **Instalador** | [`install.sh`](../install.sh) | Script Bash en 5 pasos: valida Python 3 y Codex CLI, crea directorios base con permisos `0700`, enlaza `codexc` en `~/.local/bin`, instala la skill y ejecuta `codexc doctor`. |
| **Skill para agentes** | [`skills/codexc/SKILL.md`](../skills/codexc/SKILL.md) | Instrucciones operativas para que agentes autónomos consulten saldos (`list --json`, `quota`), roten cuentas (`auto`, `switch`) y usen lanzadores paralelos. |

---

## 2. Modelo de almacenamiento y aislamiento nativo por `$CODEX_HOME`

### Estructura de directorios y archivos

`codexc` toma como raíz real `REAL_HOME = os.environ.get("CODEX_REAL_HOME") or "/home/aidev"` y organiza el estado y los perfiles en dos árboles separados:

```text
$CODEX_REAL_HOME/
├── .codexc/                          # Estado global y caché de codexc
│   ├── active                        # Alias actualmente activo para el wrapper 'codex'
│   ├── default                       # Alias predeterminado de respaldo
│   └── cache/                        # Permisos 0700
│       ├── codex01.json              # Caché atómico de cuotas (permisos 0600, TTL 60s)
│       └── codex02.json
│
├── .codexc_homes/                    # Permisos 0700 — Perfiles aislados de Codex CLI
│   ├── codex01/                      # Permisos 0700 (creado por codexc)
│   │   ├── auth.json                 # Credenciales OAuth2 de OpenAI (permisos 0600)
│   │   ├── config.toml               # Configuración TOML copiada/propia del perfil (0600)
│   │   ├── skills -> ~/.codex/skills # Symlink a las skills globales compartidas
│   │   └── (archivos de Codex CLI)   # state_5.sqlite, goals_1.sqlite, logs_2.sqlite, sesiones, locks
│   └── codex02/
│       └── ...
│
└── .local/bin/
    ├── codexc -> .../bin/codexc      # Symlink al script principal
    ├── codex                         # Wrapper global dinámico
    ├── codex01                       # Lanzador dedicado para codex01
    └── codex02                       # Lanzador dedicado para codex02
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

La función `sync_launchers()` genera y mantiene actualizados (solo reescribiendo si cambia el contenido) los scripts Bash en `~/.local/bin/`:

### Lanzadores dedicados (`codex01`, `codex02`, ...) vs Wrapper global (`codex`)

- **Lanzadores dedicados**: exportan incondicionalmente `export CODEX_HOME="$CODEX_REAL_HOME/.codexc_homes/<alias>"`. Permiten abrir múltiples paneles simultáneos (p. ej. `codex01` en el panel 1 y `codex02` en el panel 2) sin interferencia.
- **Wrapper `codex`**: solo asigna `CODEX_HOME` si `[ -z "$CODEX_HOME" ]`, resolviendo el alias en cascada:
  1. Contenido de `~/.codexc/active`
  2. Contenido de `~/.codexc/default`
  3. Fallback literal `"codex01"`
  Si el directorio resultante existe, exporta `CODEX_HOME` antes de invocar al binario real.

### Resolución del binario real (`get_real_codex_bin`)

Busca el ejecutable oficial de Codex CLI en este orden:
1. `~/.codex/packages/standalone/current/bin/codex` (si existe y es ejecutable).
2. `shutil.which("codex")`, excluyendo explícitamente `~/.local/bin/codex` para evitar recursión infinita contra el propio wrapper.
3. Ruta fallback standalone (`~/.codex/packages/standalone/releases/0.164.0-x86_64-unknown-linux-musl/bin/codex`).

### Detección de subcomandos (`KNOWN_SUBS`) y manejo de flags

Tanto los lanzadores dedicados como el wrapper `codex` procesan todos los argumentos (`"$@"`) antes de ejecutar el binario real:

1. **Flags reconocidas**:
   - `--yolo` o `--dangerously-bypass-approvals-and-sandbox` marcan `has_yolo=true` (se preservan en `ARGS`).
   - `--no-yolo` marca `has_no_yolo=true` y **se filtra** (no se reenvía al binario real de Codex).
   - Cualquier otro flag o argumento del usuario se conserva intacto en `ARGS`.
2. **Detección de subcomandos**:
   El primer argumento posicional (que no comience por `-`) se busca en la lista `KNOWN_SUBS`:
   ```text
   agents, exec, review, login, logout, mcp, plugin, app-server,
   remote-control, completion, update, doctor, sandbox, debug, apply,
   resume, queue, archive, delete, migrate-rollouts, migrate-nfs-db,
   unarchive, fork, cloud, exec-server, features, help
   ```
   Si coincide, se marca `is_subcmd=true`.
3. **Regla de ejecución**:
   - Si `has_no_yolo=false`, `has_yolo=false` e `is_subcmd=false`: ejecuta `exec "$REAL_BIN" --yolo "${ARGS[@]}"`.
   - En cualquier otro caso: ejecuta `exec "$REAL_BIN" "${ARGS[@]}"`.

### Comportamiento de `resume` y `fork` entre perfiles

Tanto `resume` como `fork` están incluidos en `KNOWN_SUBS`, por lo que los lanzadores no les inyectan `--yolo` de forma automática. Debido a que cada perfil opera bajo su propio `$CODEX_HOME` con su propia base SQLite (`state_5.sqlite`) y almacenamiento de sesiones/locks, las sesiones pertenecen al perfil donde fueron creadas (`codex01` no mezcla sus hilos ni locks con `codex02`).

---

## 4. Autenticación OAuth2 y Motor Nativo `codex app-server` JSON-RPC

### Flujo de vinculación y migración inicial

- **Registro nuevo (`codexc add [alias] [--device-auth]`)**:
  1. Si se omite `alias`, calcula el primer correlativo libre `codex01`, `codex02`, ...
  2. Comprueba que el alias no exista aún ni tenga `auth.json`.
  3. Crea `~/.codexc_homes/<alias>` con modo `0700`, copia `~/.codex/config.toml` (`0600`) si existe y crea el symlink `skills -> ~/.codex/skills` si existe.
  4. Ejecuta `codex login` (añadiendo `--device-auth` para entornos headless/SSH) con `CODEX_HOME` apuntando al nuevo perfil.
  5. Si el usuario cancela o `auth.json` no se genera, elimina el directorio del perfil para no dejar residuos.
  6. Aplica `chmod 0600` a `auth.json`, verifica duplicados (`email` + `account_id`), sincroniza lanzadores y activa el nuevo perfil.
- **Migración automática no destructiva (`ensure_auto_migration`)**:
  Si no hay ningún perfil registrado todavía (`list_aliases()` vacío) pero existe `~/.codex/auth.json`, `codexc` lo copia a `codex01` (`0600`), copia `config.toml` (`0600`) si existe, enlaza `skills`, establece `codex01` como `active` y `default`, y genera los lanzadores.

### Consulta de cuotas en vivo y renovación delegada en `codex app-server`

`fetch_codex_usage(alias, force_refresh=False, retry_on_401=True)` obtiene el estado de la cuenta:

1. **Consulta HTTP de cuotas**:
   Realiza `GET https://chatgpt.com/backend-api/codex/usage` (timeout 8s) con:
   - `Authorization: Bearer <access_token>` (leído de `auth.json`)
   - `chatgpt-account-id: <account_id>` (si está presente)
   - `User-Agent: codex-cli/0.164.0`
2. **Renovación automática ante `HTTP 401` (`attempt_native_token_refresh`)**:
   En lugar de refrescar tokens manualmente compitiendo con sesiones activas, `codexc` delega la renovación en el subproceso nativo de Codex CLI:
   - Lanza `[real_bin, "app-server", "--listen", "stdio://"]` con `CODEX_HOME=prof_dir`.
   - Envía por `stdin` dos peticiones JSON-RPC delimitadas por salto de línea:
     ```json
     {"id": 1, "method": "initialize", "params": {"clientInfo": {"name": "codexc", "version": "1.0.0"}}}
     {"id": 2, "method": "account/read", "params": {"refreshToken": true}}
     ```
   - Lee `stdout` de forma no bloqueante: configura `os.set_blocking(fd, False)` y usa `select.select([fd], [], [], min(0.2, remaining))` + `os.read(fd, 8192)` acumulando en `buffer` (con fallback a `readline()` si el stream no expone descriptor real) bajo un límite estricto de **6.0 segundos**.
   - Cuando recibe la respuesta JSON-RPC con `"id": 2` y `result.account` presente, da por exitosa la renovación y reintenta `fetch_codex_usage(..., force_refresh=True, retry_on_401=False)` una única vez.
   - En el bloque `finally`, garantiza la recolección del proceso hijo: `terminate()` → `wait(timeout=0.8)` y, si sigue vivo, `kill()` → `wait(timeout=1.0)`, evitando procesos zombis.

### Caché local, normalización y countdowns

- **Caché atómico (`TTL = 60s`)**: las métricas se escriben en `~/.codexc/cache/<alias>.json.tmp.<pid>`, se protegen con `chmod 0600` y se reemplazan atómicamente con `os.replace()`.
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

---

## 6. Guía de Portabilidad a Windows (Blueprint para futura versión Windows)

Esta sección documenta los equivalentes exactos requeridos para portar `codexc` a **Windows 10/11** manteniendo la misma arquitectura de aislamiento por `CODEX_HOME`:

| Pieza / Mecanismo | Implementación actual en Linux | Equivalente exacto en Windows 10/11 |
|---|---|---|
| **Directorio base del usuario (`REAL_HOME`)** | `CODEX_REAL_HOME` o `/home/aidev`; rutas `~/.codexc`, `~/.codexc_homes`, `~/.local/bin`. | `CODEX_REAL_HOME` o `%USERPROFILE%` (`os.path.expanduser("~")`); rutas `%USERPROFILE%\.codexc` y `%USERPROFILE%\.codexc_homes`. |
| **Binario oficial de Codex CLI** | `~/.codex/packages/standalone/current/bin/codex` o `shutil.which("codex")`. | `codex.exe` (instalación standalone) o `codex.cmd` (instalación global vía `npm`). **Importante:** resolver explícitamente `.exe`/`.cmd` evitando invocar `codex.ps1`, que suele fallar en PowerShell por restricciones de `ExecutionPolicy`. |
| **Lanzadores paralelos y wrapper** | Scripts Bash ejecutables (`chmod 0755`) en `~/.local/bin/codex01`, `codex02`, `codex` usando `export CODEX_HOME=...` y arreglo `ARGS`. | Scripts `.cmd` / `.bat` (`codex01.cmd`, `codex02.cmd`, `codex.cmd`) en `%USERPROFILE%\.local\bin` o `%LOCALAPPDATA%\codexc\bin` (añadido al `PATH` del usuario), usando `set "CODEX_HOME=..."` y replicando la lógica de detección `KNOWN_SUBS`, `--yolo` y `--no-yolo`. |
| **Enlace compartido de `skills/`** | `os.symlink(skills_src, skills_dst)` hacia `~/.codex/skills`. | **NTFS Junction** mediante `cmd /c mklink /J "<dst>" "<src>"` (a diferencia de los symlinks simbólicos en Windows, un *Junction* de directorio no requiere privilegios de Administrador ni Developer Mode). |
| **I/O no bloqueante con `codex app-server`** | `os.set_blocking(fd, False)` + `select.select([fd], ...)` + `os.read(fd, 8192)`. | **`select.select` NO funciona sobre pipes ni descriptores de subprocesos en Windows** (solo sobre sockets). Se debe reemplazar por un hilo lector (`threading.Thread`) que lea líneas de `p.stdout` y las deposite en `queue.Queue` (o `asyncio.create_subprocess_exec` con `asyncio.wait_for`), conservando el timeout de 6s y la terminación/limpieza en `finally`. |
| **Permisos de seguridad (`0700` / `0600`)** | `os.makedirs(..., mode=0o700)` y `os.chmod(..., 0o600)`. | En Windows `os.chmod` solo controla el bit de solo lectura. Proteger los archivos heredando permisos privados bajo `%USERPROFILE%` y, opcionalmente, aplicar ACLs NTFS explícitas mediante `icacls "<ruta>" /inheritance:r /grant:r "%USERNAME%:F"`. |
