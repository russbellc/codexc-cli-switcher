# codexc — OpenAI Codex CLI Multi-Account Switcher

Gestor de múltiples cuentas, aislamiento de sesiones y rotación inteligente de cuotas para OpenAI Codex CLI. Permite ejecutar múltiples instancias de Codex en paralelo sin interferencias de sesión ni colisiones de tokens.

---

## Características

- **Aislamiento por perfil (`CODEX_HOME`)**: Cada cuenta (`codex01`, `codex02`, etc.) tiene su propio `auth.json`, `config.toml`, base de datos SQLite y logs en `~/.codexc_homes/<alias>/`.
- **Lanzadores independientes**: Comandos directos `codex01`, `codex02` para trabajar en paralelo en paneles simultáneos de terminal (por ejemplo en Herdr) sin agotar la misma cuota de 5 horas.
- **Monitoreo de cuotas en tiempo real**: Consulta directa a la API de OpenAI ChatGPT para visualizar:
  - Ventana rodante de 5 horas (% disponible y tiempo exacto para reinicio).
  - Ventana semanal (% disponible y tiempo exacto para reinicio).
  - Plan de la cuenta (`PLUS`, `PRO`, `TEAM`).
- **Rotación inteligente (`codexc auto`)**: Evalúa todas las cuentas registradas y selecciona automáticamente la cuenta con mayor saldo disponible en la ventana de 5 horas.
- **Detección de cuentas duplicadas**: Evita registrar dos alias con el mismo correo electrónico de OpenAI.
- **Zero Dependencias**: Escrito en Python 3 puro utilizando únicamente la biblioteca estándar del sistema.

---

## Instalación

```bash
cd /home/aidev/proyectos/codexc-cli-switcher
./install.sh
```

El script configurará los binarios y lanzadores en `~/.local/bin/`.

---

## Comandos Principales

| Comando | Descripción |
|---|---|
| `codexc` o `codexc list` | Muestra la tabla visual con el estado de todas las cuentas y sus cuotas en tiempo real. |
| `codexc list --refresh` | Fuerza la actualización de cuotas saltándose el caché de 60 segundos. |
| `codexc list --json` | Exporta la información de cuentas y cuotas en formato JSON estructurado. |
| `codexc switch <alias>` | Cambia la cuenta activa para el comando `codex` estándar. (Atajo: `codexc <alias>`) |
| `codexc default <alias>` | Establece la cuenta predeterminada de arranque. |
| `codexc add [alias]` | Inicia el asistente de vinculación para una nueva cuenta mediante el navegador. |
| `codexc add [alias] --device-auth` | Vinculación mediante código de dispositivo para entornos sin navegador web. |
| `codexc quota [alias]` | Muestra el desglose detallado de cuotas y ventanas de reinicio. |
| `codexc auto` | Evalúa las cuentas y rota a la que tenga mayor saldo disponible en la ventana de 5h. |
| `codexc doctor` | Diagnostica el estado de salud de los perfiles, permisos y binarios. |
| `codexc rm <alias>` | Elimina un perfil de cuenta con confirmación previa. |

---

## Uso en Paralelo (Herdr)

Para ejecutar dos agentes Codex simultáneos sin compartir cuotas:
- En el **Panel 1**: ejecuta `codex01` (cuenta 1).
- En el **Panel 2**: ejecuta `codex02` (cuenta 2).

Ambos agentes operan de forma 100% aislada.
