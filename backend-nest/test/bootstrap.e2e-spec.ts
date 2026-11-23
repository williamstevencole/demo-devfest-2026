import { INestApplication } from '@nestjs/common';
import { mkdtempSync, rmSync } from 'node:fs';
import type { Server } from 'node:http';
import type { AddressInfo } from 'node:net';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { bootstrap } from './../src/main';
import { pushSchema } from './push-schema';

describe('Bootstrap cold path (e2e)', () => {
  let app: INestApplication;
  let tempDir: string;
  let databaseDir: string;

  beforeAll(async () => {
    tempDir = mkdtempSync(join(tmpdir(), 'bootstrap-e2e-'));
    databaseDir = join(tempDir, 'nested', 'data');
    process.env.DATABASE_URL = `file:${join(databaseDir, 'broker.sqlite')}`;
    process.env.PORT = '0';
    pushSchema(process.env.DATABASE_URL);

    app = await bootstrap();
  });

  afterAll(async () => {
    await app.close();
    rmSync(tempDir, { recursive: true, force: true });
  });

  it('boots with a nested database path and serves /api/health', async () => {
    const server = app.getHttpServer() as Server;
    const { port } = server.address() as AddressInfo;
    const response = await fetch(`http://127.0.0.1:${port}/api/health`);

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({
      status: 'ok',
      service: 'backend-nest',
    });
  });
});
