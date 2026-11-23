# demo-ui

Interfaz web del proyecto **Broker Agentic RAG**. Es una aplicación de una sola
página construida con React, TypeScript y Vite. Se comunica únicamente con
`agent-service`; nunca accede directamente a `backend-nest`.

## Funcionalidades

- **Chat con streaming**: consume eventos SSE del agente y muestra la respuesta
  mientras se genera.
- **Dos modos de respuesta**: `Agentic RAG` y `Naive RAG`, seleccionables desde
  el header.
- **Traza en vivo**: pasos expandibles con título, detalle, fuentes, estado y
  duración.
- **Fuentes**: documentos del corpus y resultados web citados por el agente.
- **Respuesta en texto**: el agente explica las cifras en Markdown; el chat no
  renderiza tarjetas estructuradas.
- **Vista de portafolio**: disponible desde el inicio; se carga bajo demanda
  desde `GET /api/portfolio/{user_id}`.
- **Historial local**: las conversaciones se guardan en `localStorage` y
  conservan el modo con el que fueron creadas.
- **Disclaimer**: aviso visible cuando la respuesta requiere aclarar que no es
  asesoría financiera.

## Stack

| Pieza | Tecnología |
| --- | --- |
| Framework | React 19 |
| Lenguaje | TypeScript |
| Bundler | Vite |
| Tests | Vitest + Testing Library |
| Estilos | CSS propio |

## Requisitos

- Node.js 22+
- `agent-service` disponible en `http://localhost:8000`

## Arranque

```bash
npm ci
npm run dev
```

Abre `http://localhost:5173`.

Vite reenvía las peticiones `/api` a `http://localhost:8000` mediante el proxy
definido en `vite.config.ts`. Por eso la UI no necesita configuración adicional
ni CORS.

## Scripts

| Comando | Descripción |
| --- | --- |
| `npm run dev` | Servidor de desarrollo con recarga en caliente |
| `npm run build` | Comprobación de tipos y build de producción |
| `npm test -- --run` | Tests en modo no interactivo |

## Flujo de una consulta

```text
Composer
  └── useChat.send
        └── streamChat (fetch SSE)
              └── POST /api/chat/stream
                    └── agent-service
```

1. `useChat` construye el cuerpo con `user_id`, `query`, `mode` y los últimos
   mensajes del historial.
2. `lib/sse.ts` abre la petición y parsea los eventos `step`, `token`, `done` y
   `error`.
3. `lib/chatState.ts` aplica cada evento al mensaje correspondiente.
4. Al recibir `done`, se guardan la respuesta, la traza, las fuentes,
   `insufficient_data`, `missing_data` y la bandera de disclaimer.

## Estructura

```text
src/
├── components/      # Header, chat, traza y portafolio
├── hooks/           # useChat
├── lib/             # SSE, estado del chat, API y formato
├── App.tsx          # composición de la página
├── main.tsx
└── types.ts
```

La aplicación usa un usuario de demostración configurado en `App.tsx`. No hay
autenticación ni selector de usuario; el foco de la demo es el flujo del agente,
no la gestión de identidades.

## Tests

```bash
npm test -- --run
```

Los tests simulan `fetch` y eventos SSE. No llaman a Gemini, Tavily ni a
servicios externos.
