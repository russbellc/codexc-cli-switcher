# Manual de Usuario y Arquitectura Técnica — codexc

## Arquitectura de Aislamiento

OpenAI Codex CLI utiliza la variable de entorno `CODEX_HOME` para definir la ubicación de sus archivos de configuración, credenciales y bases de datos locales:

```text
~/.codexc_homes/
├── codex01/
│   ├── auth.json       (credenciales de cuenta 1, permisos 0600)
│   ├── config.toml     (configuración, MCPs, hooks)
│   ├── state_5.sqlite  (estado de sesiones de cuenta 1)
│   └── skills -> ~/.codex/skills (symlink a skills comunes)
└── codex02/
    ├── auth.json       (credenciales de cuenta 2, permisos 0600)
    ├── config.toml     (configuración independiente)
    ├── state_5.sqlite  (estado de sesiones de cuenta 2)
    └── skills -> ~/.codex/skills
```

El binario de Codex no se duplica: ambos perfiles ejecutan la instalación oficial central ubicada en `~/.codex/packages/standalone/current/bin/codex`.

## API de Cuotas de OpenAI

`codexc` consulta el endpoint oficial de backend de ChatGPT:
- **Endpoint**: `https://chatgpt.com/backend-api/codex/usage`
- **Cabeceras**:
  - `Authorization: Bearer <access_token>`
  - `chatgpt-account-id: <account_id>`
  - `User-Agent: codex-cli/0.164.0`

### Estructura de Respuesta

- `primary_window`: Representa el límite rodante de 5 horas (`limit_window_seconds: 18000`).
- `secondary_window`: Representa el límite semanal (`limit_window_seconds: 604800`).
- `plan_type`: `plus`, `pro`, `team`, etc.

## Flujo de Vinculación de Cuentas

Al ejecutar:
```bash
codexc add codex02
```
1. `codexc` crea el directorio `~/.codexc_homes/codex02` con permisos `0700`.
2. Clona la configuración base `config.toml` y enlaza los `skills` del sistema.
3. Lanza `codex login` fijando `CODEX_HOME=~/.codexc_homes/codex02`.
4. El usuario completa el flujo en el navegador (o por `--device-auth`).
5. Tras el login, `codexc` inspecciona `auth.json`, consulta el endpoint de cuota para obtener el correo, y verifica que no sea una cuenta duplicada con respecto a `codex01`.
6. Genera automáticamente el lanzador `~/.local/bin/codex02`.
