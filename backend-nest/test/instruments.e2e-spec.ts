import { INestApplication } from '@nestjs/common';
import { Test, TestingModule } from '@nestjs/testing';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import request from 'supertest';
import { App } from 'supertest/types';
import { AppModule } from './../src/app.module';
import { pushSchema } from './push-schema';

describe('InstrumentsController (e2e)', () => {
  let app: INestApplication<App>;
  let tempDir: string;

  beforeAll(async () => {
    tempDir = mkdtempSync(join(tmpdir(), 'instruments-e2e-'));
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

  it('VOO incluye sus diez principales holdings', async () => {
    const response = await request(app.getHttpServer())
      .get('/api/instruments/voo')
      .expect(200);
    const body = response.body as {
      holdings: {
        componentTicker: string;
        weightPct: number;
        componentName: string;
        componentSector: string | null;
      }[];
    };
    expect(body.holdings).toHaveLength(10);
    expect(body.holdings[0]).toEqual({
      componentTicker: 'NVDA',
      weightPct: 7,
      componentName: 'NVIDIA Corporation',
      componentSector: 'Technology',
    });
  });

  it('BND no tiene holdings de acciones', async () => {
    const response = await request(app.getHttpServer())
      .get('/api/instruments/BND')
      .expect(200);
    const body = response.body as { holdings: unknown[] };
    expect(body.holdings).toEqual([]);
  });

  it('devuelve 404 si el instrumento no existe', async () => {
    await request(app.getHttpServer()).get('/api/instruments/XXXX').expect(404);
  });
});
