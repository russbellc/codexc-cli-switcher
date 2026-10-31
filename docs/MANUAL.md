# Manual Completo de `codexc`
## OpenAI Codex CLI Multi-Account Switcher

> **Versión:** v1.2 | **Fecha:** Octubre 2026  
> **Plataforma:** Linux x86_64 (Ubuntu / Debian / RHEL / Arch)  
> **Compatibilidad:** OpenAI Codex CLI (standalone & bundled)

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
| **Sistema Operativo** | Linux x86_64 | Probado en Ubuntu 20.04/22.04/24.04/26.04 |
| **Python** | 3.10+ | No requiere pip ni librerías de terceros |
| **Codex CLI** | 0.160.0+ | Instalado en el sistema |
| **Cuentas ChatGPT** | Plus, Pro o Team | Al menos una cuenta activa |

### Instalación Automática

```bash
git clone https://github.com/russbellc/codexc-cli-switcher.git
cd codexc-cli-switcher
chmod +x install.sh
./install.sh
source ~/.bashrc
```

### Instalación Manual

Si prefieres realizar la configuración paso a paso:

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

---

## 4. Comandos de Referencia

### `codexc` o `codexc list`
Muestra la tabla interactiva de perfiles registrados con barras de progreso visuales para las ventanas de 5 horas y semanal.

```text
┌───────────┬──────────────────────────────┬──────────┬───────────────┬────────────────────────────────┬────────────────────────────────┐
│ ALIAS     │ CUENTA / EMAIL               │ PLAN     │ ESTADO        │ 5 HORAS (DISPONIBLE / RESET)   │ SEMANAL (DISPONIBLE / RESET)   │
├───────────┼──────────────────────────────┼──────────┼───────────────┼────────────────────────────────┼────────────────────────────────┤
│   codex01 │ meeker-emcee-8d@icloud.com   │ PLUS     │   DEFAULT     │ 5H:  [████████]  96% (1h 35m)  │ Sem: [████░░░░]  47% (4d 10h)  │
├───────────┼──────────────────────────────┼──────────┼───────────────┼────────────────────────────────┼────────────────────────────────┤
│ * codex02 │ mcastroja01@ucvvirtual.ed... │ PLUS     │ * ACTIVA      │ 5H:  [████████]  98% (4h 15m)  │ Sem: [█████░░░]  67% (4d 12h)  │
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
- Existencia y permisos del binario central de Codex.
- Integridad y permisos (`0700` y `0600`) de los perfiles.
- Existencia y consistencia de los lanzadores en `~/.local/bin/`.
- Estado del symlink y los directorios de caché.

### `codexc rm <alias>`
Elimina de forma segura un perfil y su directorio asociado en `~/.codexc_homes/`, solicitando confirmación explícita para evitar pérdida accidental de datos.

---

## 5. Aislamiento de Perfiles por `$CODEX_HOME`

OpenAI Codex CLI respeta de manera nativa la variable de entorno `CODEX_HOME`. `codexc` aprovecha este diseño para estructurar el sistema de archivos de forma limpia:

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

### ¿Por qué compartir `skills/`?
Las skills y herramientas de asistencia (como `interface-design`, `crear-modulo` o `context7`) son utilidades compartidas. Al enlazarlas simbólicamente desde `~/.codex/skills`, cualquier nueva skill instalada estará disponible de inmediato en todos los perfiles de `codexc` sin duplicación de almacenamiento.

---

## 6. Ejecución en Múltiples Paneles en Paralelo

El mayor beneficio del aislamiento radica en el **desarrollo concurrente**. En herramientas de multipaneleo como **Herdr**, tmux o zellij:

```text
┌──────────────────────────────────────┬──────────────────────────────────────┐
│ HERDR PANE 1                         │ HERDR PANE 2                         │
│ $ codex01                            │ $ codex02                            │
│                                      │                                      │
│ Cuenta: meeker-emcee-8d@icloud.com   │ Cuenta: mcastroja01@ucvvirtual.edu   │
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

Los lanzadores generados por `codexc` resuelven esto de forma inteligente:

1. **Inyección transparente:** Al escribir `codex01`, el script ejecuta internamente:
   ```bash
   exec codex --yolo "$@"
   ```
2. **Detección de subcomandos:** Subcomandos nativos como `doctor`, `login`, `features` o `app-server` rechazan la bandera `--yolo`. El lanzador detecta si el primer argumento es un subcomando conocido y **omite** `--yolo` automáticamente para evitar errores.
3. **Opción `--no-yolo`:** Si en una sesión específica deseas supervisión paso a paso:
   ```bash
   codex01 --no-yolo
   ```
   El lanzador suprime el modo `--yolo` e inicia Codex con las solicitudes de aprobación habituales.

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
- Comunicación mediante `os.set_blocking(fd, False)` y `select.select`.
- Timeout estricto de 6 segundos con acumulador de fragmentos en memoria.
- Limpieza incondicional en bloque `finally`: envía `SIGTERM`, espera 0.8s y, de persistir, ejecuta `SIGKILL` seguido de `wait()` para no dejar procesos zombis en la tabla del sistema operativo.
- **Validación:** 9 de 9 pruebas unitarias aprobadas en la suite de auditoría técnica.

---

## 10. Seguridad y Permisos del Sistema de Archivos

Las credenciales de acceso a ChatGPT contienen tokens capaces de realizar acciones en tu cuenta. Por esta razón, `codexc` aplica una política de **privilegio mínimo**:

1. **Directorios de perfiles (`0700`):** `~/.codexc_homes/` y cada una de sus carpetas hijas solo son legibles y ejecutables por el usuario propietario (`rwx------`).
2. **Archivos de credenciales (`0600`):** Cada archivo `auth.json` se guarda con permisos estrictos de lectura/escritura únicamente para el dueño (`rw-------`).
3. **Caché privada (`0700`):** `~/.codexc/cache` previene que otros usuarios del sistema local puedan inspeccionar las métricas o metadatos de las cuentas.
4. **Validación estricta de alias:** Los nombres de perfiles se validan contra la expresión regular `^[a-zA-Z0-9_-]{1,32}$`, bloqueando cualquier intento de inyección de rutas (`path traversal`) o caracteres especiales.

---

## 11. Diagnóstico, Troubleshooting y `codexc doctor`

Si en algún momento experimentas un comportamiento inesperado, ejecuta:

```bash
codexc doctor
```

El diagnóstico comprueba:
- [x] Si el ejecutable original de Codex existe y responde.
- [x] Que los permisos de las carpetas de perfiles sean `0700`.
- [x] Que los archivos `auth.json` tengan permisos `0600`.
- [x] Que los lanzadores en `~/.local/bin/` apunten a los perfiles correctos.
- [x] Que no existan symlinks rotos ni directorios de caché huérfanos.

### Problemas comunes y soluciones

#### 1. "Error 401 Unauthorized" al consultar cuotas
- **Causa:** El `access_token` expiró y el `refresh_token` requiere renovación.
- **Solución:** Ejecuta `codexc list --refresh`. `codexc` invocará automáticamente la renovación nativa por `app-server`. Si tu sesión fue cerrada desde la web de OpenAI, ejecuta `codexc add <alias>` para volver a vincularla.

#### 2. Mi terminal no encuentra el comando `codex01`
- **Causa:** `~/.local/bin` no está presente en tu variable `$PATH`.
- **Solución:**
  ```bash
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
  source ~/.bashrc
  ```

#### 3. Quiero ingresar a una cuenta sin modo `--yolo`
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
- Suite de pruebas `/tmp/codexc_final_revalidation.py` completada al 100% (9/9 pruebas aprobadas).

---

## Licencia

Distribuido bajo la licencia MIT.  
Copyright (c) 2026 Mikail Russbell Castro Jara.
