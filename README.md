# Broker Agentic RAG

Copiloto de inversiones que compara **Naive RAG** y **Agentic RAG** sobre el
mismo corpus, el mismo modelo y el mismo portafolio. Muestra cómo un agente con
herramientas consulta datos del broker, recupera conocimiento local y busca
noticias en vivo, dejando una traza visible de cada decisión.

Todo el cálculo financiero son funciones puras y deterministas: el modelo decide
qué herramientas usar y redacta la respuesta, pero no inventa cifras. Es una demo
educativa, no un producto financiero.

## Qué hay aquí

- `backend-nest/` — API de datos del broker (NestJS + Prisma + SQLite). No tiene
  lógica de IA.
- `agent-service/` — el agente, el RAG y los cálculos (Python + FastAPI +
  LangGraph).
- `demo-ui/` — la interfaz web (React + Vite). Habla solo con el agente.

## Puesta en marcha

Necesitas Node.js 22+ con npm 10+, Python 3.14 y dos claves de API:
`GOOGLE_API_KEY` (Google AI Studio) y `TAVILY_API_KEY` (Tavily).

La aplicación se ejecuta en tres terminales, en este orden.

### 1. API de datos

```bash
cd backend-nest
npm install
cp .env.example .env
npm run prisma:generate
npm run prisma:push
npm run start:dev
```

Queda disponible en `http://localhost:3001`. El seed corre al arrancar y crea
el usuario de demostración, los instrumentos, los precios y las posiciones.

```bash
curl http://localhost:3001/api/health
```

### 2. Agente

```bash
cd agent-service
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
```

Completa `agent-service/.env` con `GOOGLE_API_KEY` y `TAVILY_API_KEY`.
Después indexa el corpus y arranca el servicio:

```bash
make ingest
make dev
```

Queda disponible en `http://localhost:8000`.

```bash
curl http://localhost:8000/api/health
```

### 3. Interfaz web

```bash
cd demo-ui
npm ci
npm run dev
```

Abre `http://localhost:5173`.
