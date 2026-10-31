# codexc — OpenAI Codex CLI Multi-Account Switcher

> **Administrador multi-cuenta para OpenAI Codex CLI en Linux**  
> Perfiles `$CODEX_HOME` aislados | Monitoreo de cuotas 5H y Semanal en vivo | Modo `--yolo` automático | Múltiples paneles en paralelo

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform: Linux](https://img.shields.io/badge/Platform-Ubuntu%20Linux-orange.svg)](https://kernel.org)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![Codex: CLI](https://img.shields.io/badge/OpenAI-Codex%20CLI-brightgreen.svg)](https://openai.com)
[![Aislamiento: CODEX__HOME](https://img.shields.io/badge/Aislamiento-CODEX__HOME-blueviolet.svg)](#arquitectura)

---

## ¿Qué es codexc?

`codexc` convierte OpenAI Codex CLI en una estación de trabajo **multi-cuenta y de desarrollo paralelo**. Nació para resolver una limitación crítica durante el desarrollo intensivo con modelos de razonamiento profundo (como `gpt-6.1-sol` o `gpt-5.6-sol`): las cuotas de una sola cuenta de ChatGPT Plus o Pro se agotan en pocas horas.

**La solución:** gestionar múltiples cuentas (`codex01`, `codex02`, etc.) con entornos y bases de datos completamente aislados mediante `$CODEX_HOME`. Esto permite trabajar en **múltiples paneles del terminal simultáneamente** (por ejemplo en Herdr, tmux o zellij) sin colisiones de sesiones, sin sobrescritura de tokens y sin bloqueos de confirmación.

---

## Características

- 🔒 **Aislamiento total por `$CODEX_HOME`** — Cada cuenta posee su propio `auth.json`, `config.toml`, base de datos SQLite de rollouts/sesiones y locks en `~/.codexc_homes/<alias>/`. Dos terminales concurrentes nunca compiten ni interfieren entre sí.
- ⚡ **Lanzadores directos con `--yolo` por defecto** — Escribe `codex01` o `codex02` y comienza a trabajar de inmediato con auto-aprobación de herramientas. Detecta inteligentemente subcomandos (`doctor`, `login`, etc.) para no inyectar flags duplicadas.
- 📊 **Panel de cuotas en tiempo real** — Consulta en vivo a la API oficial de OpenAI (`/backend-api/codex/usage`) con barras visuales para la **ventana rodante de 5 horas** y el **límite semanal**, junto con cuenta regresiva para reinicio.
- 🔄 **Rotación inteligente (`codexc auto`)** — Evalúa el consumo actual y conmuta automáticamente el comando global `codex` hacia la cuenta con mayor porcentaje disponible en la ventana de 5 horas.
- 🛡️ **Renovación segura vía `app-server`** — Delegación nativa al protocolo interno de Codex (`account/read` con `refreshToken=true`), comunicación no bloqueante con `select.select` + `os.read()`, y recolección estricta de subprocesos (cero procesos zombis).
- 🛑 **Anti-duplicados y seguridad estricta** — Previene registrar dos veces la misma cuenta OpenAI bajo alias distintos. Directorios protegidos con permisos `0700` y credenciales con `0600`.
- 🤖 **Skill para agentes autónomos** — Incluye skill lista para que agentes de IA coordinen el cambio de cuentas de forma desatendida.
- 📦 **Zero Dependencias Externas** — Escrito en Python 3 puro utilizando únicamente la biblioteca estándar del sistema.

---

## Instalación Rápida

```bash
git clone https://github.com/russbellc/codexc-cli-switcher.git
cd codexc-cli-switcher
chmod +x install.sh
./install.sh
```

Luego recarga la configuración de tu terminal:

```bash
source ~/.bashrc
```

### Requisitos

- Sistema operativo Linux (x86_64) — testeado en Ubuntu Linux.
- [OpenAI Codex CLI](https://github.com/openai/codex) instalado.
- Python 3.10+.
- Al menos una suscripción activa a ChatGPT Plus, Pro o Team.

---

## Uso

### 1. Registrar cuentas

Vincula tu cuenta actual o agrega nuevas cuentas interactivamente:

```bash
codexc add           # Asigna automáticamente codex01 (o el siguiente correlativo)
codexc add codex02   # Asigna un alias específico
```

> **Para servidores remotos sin interfaz gráfica:**
> ```bash
> codexc add codex02 --device-auth
> ```

### 2. Entrar a Codex en paralelo

Inicia sesiones directamente en cualquier panel sin configurar variables de entorno manualmente:

```bash
codex01              # Abre Codex con la cuenta 1 (modo --yolo activo)
codex02              # Abre Codex con la cuenta 2 (modo --yolo activo)
```

Si deseas iniciar con confirmaciones interactivas manuales (sin `--yolo`):
```bash
codex01 --no-yolo
```

### 3. Ver estado y cuotas en tiempo real

Ejecuta `codexc` (o `codexc list`) para obtener el reporte visual:

```bash
codexc
```

**Ejemplo de salida:**

```text
PANEL DE CUENTAS DE OPENAI CODEX (CODEXC SWITCHER)
Desarrollo en paralelo: consumo de tokens en ventana de 5 Horas y Semanal.

┌───────────┬──────────────────────────────┬──────────┬───────────────┬────────────────────────────────┬────────────────────────────────┐
│ ALIAS     │ CUENTA / EMAIL               │ PLAN     │ ESTADO        │ 5 HORAS (DISPONIBLE / RESET)   │ SEMANAL (DISPONIBLE / RESET)   │
├───────────┼──────────────────────────────┼──────────┼───────────────┼────────────────────────────────┼────────────────────────────────┤
│   codex01 │ meeker-emcee-8d@icloud.com   │ PLUS     │   DEFAULT     │ 5H:  [████████]  96% (1h 35m)  │ Sem: [████░░░░]  47% (4d 10h)  │
├───────────┼──────────────────────────────┼──────────┼───────────────┼────────────────────────────────┼────────────────────────────────┤
│ * codex02 │ mcastroja01@ucvvirtual.ed... │ PLUS     │ * ACTIVA      │ 5H:  [████████]  98% (4h 15m)  │ Sem: [█████░░░]  67% (4d 12h)  │
└───────────┴──────────────────────────────┴──────────┴───────────────┴────────────────────────────────┴────────────────────────────────┘

Atajos rápidos para desarrollo en paralelo:
  • Ejecución directa fija:  codex01 | codex02 (aisladas sin tocarse)
  • Cambiar cuenta activa:   codexc switch <alias> (o 'codexc <alias>')
  • Agregar nueva cuenta:    codexc add [alias] (asigna correlativo en automático)
  • Rotación automática:     codexc auto (selecciona la cuenta con mayor saldo)
  • Diagnóstico de perfiles: codexc doctor
```

Para forzar la consulta en vivo ignorando el caché de 60 segundos:
```bash
codexc list --refresh
```

### 4. Rotación inteligente de cuentas

Cuando tu sesión principal alcance un límite de cuota o desees conmutar al perfil con mayor margen:

```bash
codexc auto
```

El selector analiza los porcentajes restantes de la ventana de 5 horas y apunta el comando global `codex` a la cuenta más óptima.

### 5. Diagnóstico y salud del entorno

Verifica la integridad de los binarios, permisos de archivos, enlaces simbólicos y perfiles registrados:

```bash
codexc doctor
```

---

## Flujo en Múltiples Paneles (Herdr / tmux / zellij)

Gracias al aislamiento por `$CODEX_HOME`, cada instancia de terminal opera de manera 100% independiente:

```text
┌─────────────────────────────────┐   ┌─────────────────────────────────┐
│       TERMINAL / PANEL 1        │   │       TERMINAL / PANEL 2        │
│  Comando: codex01               │   │  Comando: codex02               │
│  CODEX_HOME: ~/.codexc_homes/   │   │  CODEX_HOME: ~/.codexc_homes/   │
│              codex01/           │   │              codex02/           │
│  Token: meeker-emcee-8d@...     │   │  Token: mcastroja01@...         │
│  Base de datos SQLite propia    │   │  Base de datos SQLite propia    │
└─────────────────────────────────┘   └─────────────────────────────────┘
                 │                                     │
                 └──────────────────┬──────────────────┘
                                    ▼
                Binario oficial compartido de Codex CLI
           (~/.codex/packages/standalone/current/bin/codex)
```

**Esquema en Herdr o multiplexor de terminales:**
- **Panel Izquierdo:** Editor / Logs / Monitoreo del backend.
- **Panel Central:** `codex01` implementando funcionalidades o refactorizaciones.
- **Panel Derecho:** `codex02` realizando code review, auditorías o testing cruzado en paralelo.

---

## Comandos Disponibles

| Comando | Descripción |
|---|---|
| `codexc` / `codexc list` | Tabla visual con el estado de todas las cuentas y cuotas en tiempo real. |
| `codexc list --refresh` | Fuerza la consulta directa a OpenAI invalidando el caché local. |
| `codexc list --json` | Exporta la lista de perfiles y métricas en formato JSON estructurado. |
| `codex01` / `codex02` / ... | Lanza Codex fijado a ese perfil con `--yolo` habilitado por defecto. |
| `codex` | Ejecuta Codex usando la cuenta actualmente marcada como `ACTIVA`. |
| `codexc switch <alias>` | Cambia la cuenta activa (atajo: `codexc <alias>`). |
| `codexc default <alias>` | Establece la cuenta predeterminada de inicio. |
| `codexc auto` | Evalúa las cuotas y selecciona la cuenta con mayor saldo en la ventana de 5h. |
| `codexc add [alias]` | Inicia el asistente de vinculación OAuth en el navegador. |
| `codexc add [alias] --device-auth` | Vinculación sin navegador mediante código de verificación. |
| `codexc quota [alias]` | Muestra el desglose detallado de cuotas y resets de una cuenta. |
| `codexc doctor` | Diagnostica la instalación, binarios, symlinks y permisos del sistema. |
| `codexc rm <alias>` | Elimina un perfil y sus datos locales con confirmación de seguridad. |

---

## Arquitectura

### 1. Estructura de Aislamiento de Perfiles

OpenAI Codex CLI utiliza la variable de entorno `CODEX_HOME` para almacenar toda su información de ejecución. `codexc` organiza los entornos en:

```text
~/.codexc/
├── active                        ← Guarda el alias activo para el wrapper 'codex'
├── default                       ← Guarda el alias predeterminado
└── cache/                        ← Caché privado de cuotas (permisos 0700)
    ├── codex01.json
    └── codex02.json

~/.codexc_homes/
├── codex01/                      ← Permisos 0700
│   ├── auth.json                 ← Credenciales y tokens OAuth (permisos 0600)
│   ├── config.toml               ← Configuración TOML del perfil
│   ├── state_5.sqlite            ← Base de datos de estado y sesiones
│   ├── goals_1.sqlite            ← Base de datos de tareas y objetivos
│   ├── logs_2.sqlite             ← Registro de logs del agente
│   └── skills -> ~/.codex/skills ← Enlace simbólico a las skills globales
└── codex02/
    ├── auth.json                 ← Credenciales independientes
    ├── config.toml
    └── ...
```

### 2. Renovación de Tokens Nativa y Sin Condiciones de Carrera

En lugar de reescribir tokens manualmente desde procesos externos (lo que provocaría colisiones y sobreescrituras en sesiones concurrentes), `codexc` implementa una estrategia de **renovación delegada oficial**:

1. Lanza el protocolo interno `codex app-server --listen stdio://` bajo el `CODEX_HOME` del perfil objetivo.
2. Envía un apretón de manos inicial (`initialize`) seguido de la solicitud `account/read` con `{"refreshToken": true}`.
3. El propio motor interno de Codex gestiona los locks de SQLite, contacta a OpenAI y actualiza `auth.json` atómicamente.
4. `codexc` monitorea la comunicación mediante I/O no bloqueante (`select.select` con límite de 6 segundos) y garantiza la recolección (`SIGTERM` → `SIGKILL` + `wait()`) para evitar procesos huérfanos o zombis.

### 3. Lanzadores Inteligentes con Detección de Subcomandos

Los binarios generados en `~/.local/bin/` (`codex01`, `codex02` y el wrapper `codex`) incorporan lógica para:
- Inyectar `--yolo` automáticamente si el usuario no especificó argumentos o si pasó prompts y opciones comunes (`--model`, `-m`, `-c`, etc.).
- Omitir `--yolo` si se invoca un subcomando nativo de Codex (`doctor`, `login`, `features`, `app-server`, etc.), previniendo errores de sintaxis del CLI.
- Respetar la bandera explícita `--no-yolo` cuando se desee operar en modo guiado tradicional.

---

## Origen y Desarrollo

Este proyecto fue desarrollado y auditado en una sesión de pair-programming colaborativa entre **OpenAI Codex** (ejecutando con `gpt-6.1-sol`) y **Antigravity (DZ)** el 27–28 de Octubre de 2026.

- **Repositorio oficial:** [https://github.com/russbellc/codexc-cli-switcher](https://github.com/russbellc/codexc-cli-switcher)
- **Plataforma:** Linux x86_64
- **Herramienta de coordinación:** Herdr Terminal Multiplexer
- **Auditoría de concurrencia:** Suite de pruebas `/tmp/codexc_final_revalidation.py` con 9/9 pruebas en verde y validación estricta de concurrencia.

---

## Documentación Adicional

Para detalles avanzados sobre configuración, parámetros de red, integración con scripts de CI/CD y resolución de problemas, consulta el [Manual Completo de Usuario](docs/MANUAL.md).

---

## Licencia

Distribuido bajo la licencia MIT. Consulta el archivo [LICENSE](LICENSE) para más información.
