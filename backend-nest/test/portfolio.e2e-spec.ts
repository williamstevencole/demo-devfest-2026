import { INestApplication } from '@nestjs/common';
import { Test, TestingModule } from '@nestjs/testing';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import request from 'supertest';
import { App } from 'supertest/types';
import { AppModule } from './../src/app.module';
import { pushSchema } from './push-schema';

describe('PortfolioController (e2e)', () => {
  let app: INestApplication<App>;
  let tempDir: string;

  beforeAll(async () => {
    tempDir = mkdtempSync(join(tmpdir(), 'portfolio-e2e-'));
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

  it('devuelve el portafolio de María', async () => {
    const response = await request(app.getHttpServer())
      .get('/api/users/maria-lopez/portfolio')
      .expect(200);
    expect(response.body).toMatchObject({
      cashUsd: 2500,
      investedUsd: 13000,
      totalUsd: 15500,
    });
    const body = response.body as { positions: unknown[] };
    expect(body.positions).toHaveLength(3);
  });

  it('devuelve 404 para un usuario inexistente', async () => {
    await request(app.getHttpServer())
      .get('/api/users/nadie/portfolio')
      .expect(404);
  });
});
