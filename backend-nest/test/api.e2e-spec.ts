import { INestApplication } from '@nestjs/common';
import { Test, TestingModule } from '@nestjs/testing';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import request from 'supertest';
import { App } from 'supertest/types';
import { AppModule } from './../src/app.module';
import { pushSchema } from './push-schema';

describe('Read-only API contract (e2e)', () => {
  let app: INestApplication<App>;
  let tempDir: string;

  beforeAll(async () => {
    tempDir = mkdtempSync(join(tmpdir(), 'api-e2e-'));
    process.env.DATABASE_URL = `file:${join(tempDir, 'broker.sqlite')}`;
    pushSchema(process.env.DATABASE_URL);

    const moduleFixture: TestingModule = await Test.createTestingModule({
      imports: [AppModule],
    }).compile();

    app = moduleFixture.createNestApplication();
    app.setGlobalPrefix('api');
    await app.init();
  });

  afterAll(async () => {
    await app.close();
    rmSync(tempDir, { recursive: true, force: true });
  });

  it('health responde ok', async () => {
    await request(app.getHttpServer()).get('/api/health').expect(200);
  });

  it('instrumentos y ETFs responden', async () => {
    await request(app.getHttpServer()).get('/api/instruments/VOO').expect(200);
    await request(app.getHttpServer()).get('/api/instruments/BND').expect(200);
    await request(app.getHttpServer()).get('/api/instruments/XXXX').expect(404);
  });

  it('portafolios calculan totales exactos', async () => {
    const maria = await request(app.getHttpServer())
      .get('/api/users/maria-lopez/portfolio')
      .expect(200);
    expect(maria.body).toMatchObject({ investedUsd: 13000, totalUsd: 15500 });

    await request(app.getHttpServer())
      .get('/api/users/carlos-mendez/portfolio')
      .expect(404);
  });

  it('no expone endpoints de escritura', async () => {
    await request(app.getHttpServer()).post('/api/users').expect(404);
    await request(app.getHttpServer()).post('/api/orders').expect(404);
  });
});
