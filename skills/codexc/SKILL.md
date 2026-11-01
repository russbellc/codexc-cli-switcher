---
name: codexc
description: Consultar cuentas y cuotas de OpenAI Codex y ejecutar cambios o rotación mediante codexc. Usar para consultas de saldo (5H y semanal), autenticación o selección de cuenta de Codex.
---

# Cuentas y cuotas de Codex

Usar el administrador local `codexc` ubicado en `~/.local/bin/codexc` (o `/home/aidev/proyectos/codexc-cli-switcher`).
Consultar `codexc --help` para ver los subcomandos disponibles.

## Consultar estado y cuotas

- `codexc list`: resumen en tabla de cuentas, correo, plan, estado (ACTIVA / DEFAULT) y saldos (5 Horas y Semanal).
- `codexc list --json`: salida JSON estructurada con todos los metadatos.
- `codexc list --refresh`: fuerza la consulta en vivo a OpenAI renovando tokens vía `app-server` si es necesario.
- `codexc quota [alias]`: detalle específico de las ventanas de 5H y semanal con cuenta regresiva.
- `codexc doctor`: diagnóstico de binario central, permisos (`0700` dirs, `0600` auth), symlinks y perfiles.

## Cambiar cuenta o rotación

- `codexc switch <alias>` (o `codexc <alias>`): cambia la cuenta activa que utiliza el comando global `codex`.
- `codexc auto`: selecciona automáticamente la cuenta con mayor saldo de cuota disponible en la ventana de 5 horas.
- `codexc default <alias>`: fija la cuenta por defecto.
- `codexc add [alias]`: inicia el flujo de autenticación OAuth en navegador para vincular una cuenta nueva.
- `codexc remove <alias>`: desvincula y elimina el perfil indicado.

## Sesiones fijas en paralelo

Los lanzadores directos instalados en `~/.local/bin/`:
- `codex01`: abre OpenAI Codex fijado a la Cuenta 1 en `~/.codexc_homes/codex01` con `--yolo` por defecto.
- `codex02`: abre OpenAI Codex fijado a la Cuenta 2 en `~/.codexc_homes/codex02` con `--yolo` por defecto.

Ambos operan de forma simultánea e independiente sin competir por archivos de credenciales, SQLite ni tokens.
