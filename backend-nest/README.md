# backend-nest

API de solo lectura del broker (NestJS + Prisma + SQLite). Expone datos transaccionales; no conoce al agente ni tiene lógica de IA.

## Requisitos

- Node.js 22+
- npm 10+

## Instalación

```bash
npm install
cp .env.example .env
```

## Variables de entorno

| Variable       | Default                     | Descripción                                      |
| -------------- | --------------------------- | ------------------------------------------------ |
| `PORT`         | `3001`                      | Puerto HTTP                                      |
| `DATABASE_URL` | `file:./data/broker.sqlite` | Archivo SQLite de datos                          |
| `SEED_RESET`   | `true`                      | Borra datos que no estén en la semilla al arrancar |
| `ENV_FILE`     | `.env`                      | Ruta alternativa del archivo de entorno          |

## Base de datos

```bash
npm run prisma:generate   # genera el cliente Prisma
npm run prisma:push       # sincroniza el esquema con la base SQLite
```

`npm run start` y `npm run start:dev` ejecutan `prisma db push` automáticamente antes de arrancar. La base relativa `file:./data/broker.sqlite` se resuelve dentro de `backend-nest/prisma/data/`.

## Arrancar

```bash
npm run start:dev
```

## Tests

```bash
npm test
npm run test:e2e -- --runInBand
```

## Endpoints

- `GET /api/health` → `{ "status": "ok", "service": "backend-nest" }`; comprueba la base de datos.
- `GET /api/users/:userId/portfolio` → posiciones con precio, efectivo, invertido y total; 404 si no existe.
- `GET /api/instruments/:ticker` → instrumento con holdings si es ETF; 404 si no existe. Lo usa el script de verificación.

## Datos de demo

El seed es idempotente y corre al arrancar: crea o actualiza el usuario de demostración, los instrumentos, los precios y las posiciones. Con `SEED_RESET=true` (default) también elimina usuarios y posiciones que ya no forman parte de la semilla. Usa `SEED_RESET=false` si quieres conservar datos manuales durante la demo.

Con el servicio levantado puedes verificar estas cifras desde el agente:

```bash
python agent-service/scripts/check_demo_data.py
```
