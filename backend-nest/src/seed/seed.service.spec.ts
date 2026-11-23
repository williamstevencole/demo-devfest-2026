import { RiskProfile } from '@prisma/client';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { PrismaService } from '../prisma/prisma.service';
import { SeedService } from './seed.service';

const PROJECT_DIR = resolve(__dirname, '..', '..');

describe('SeedService', () => {
  let prisma: PrismaService;
  let service: SeedService;
  let workDir: string;

  beforeAll(async () => {
    workDir = mkdtempSync(join(tmpdir(), 'broker-seed-'));
    const databaseUrl = `file:${join(workDir, 'seed.sqlite')}`;
    process.env.DATABASE_URL = databaseUrl;
    execFileSync('npx', ['prisma', 'db', 'push', '--skip-generate'], {
      cwd: PROJECT_DIR,
      env: { ...process.env, DATABASE_URL: databaseUrl },
    });
    prisma = new PrismaService();
    await prisma.$connect();
    service = new SeedService(prisma);
  });

  afterAll(async () => {
    await prisma.$disconnect();
    rmSync(workDir, { recursive: true, force: true });
  });

  it('siembra un usuario y no duplica al repetir', async () => {
    await service.run();
    await service.run();
    expect(await prisma.user.count()).toBe(1);
    expect(await prisma.position.count()).toBe(3);
  });

  it('elimina usuarios y posiciones que ya no están en la semilla', async () => {
    await prisma.user.create({
      data: {
        id: 'viejo',
        identityNumber: '0000-0000-00000',
        name: 'Usuario viejo',
        email: 'viejo@example.com',
        riskProfile: RiskProfile.CONSERVATIVE,
        country: 'Honduras',
        cashUsd: 0,
      },
    });
    await prisma.position.create({
      data: {
        userId: 'viejo',
        ticker: 'NVDA',
        quantity: 1,
        avgCostUsd: 1,
      },
    });

    await service.run();

    expect(await prisma.user.findUnique({ where: { id: 'viejo' } })).toBeNull();
    expect(
      await prisma.position.findMany({ where: { userId: 'viejo' } }),
    ).toHaveLength(0);
  });

  it('elimina posiciones sembradas que ya no están en la semilla', async () => {
    await prisma.position.create({
      data: {
        userId: 'maria-lopez',
        ticker: 'KO',
        quantity: 1,
        avgCostUsd: 1,
      },
    });

    await service.run();

    expect(
      await prisma.position.findUnique({
        where: { userId_ticker: { userId: 'maria-lopez', ticker: 'KO' } },
      }),
    ).toBeNull();
  });

  it('conserva datos manuales cuando SEED_RESET=false', async () => {
    process.env.SEED_RESET = 'false';
    try {
      await prisma.user.create({
        data: {
          id: 'manual',
          identityNumber: '1111-1111-11111',
          name: 'Usuario manual',
          email: 'manual@example.com',
          riskProfile: RiskProfile.CONSERVATIVE,
          country: 'Honduras',
          cashUsd: 0,
        },
      });

      await service.run();

      expect(
        await prisma.user.findUnique({ where: { id: 'manual' } }),
      ).not.toBeNull();
    } finally {
      delete process.env.SEED_RESET;
    }
  });

  it('siembra el efectivo y las posiciones de María', async () => {
    await service.run();
    const maria = await prisma.user.findUnique({
      where: { id: 'maria-lopez' },
    });
    const rows = await prisma.position.findMany({
      where: { userId: 'maria-lopez' },
    });
    expect(maria?.cashUsd).toBe(2500);
    expect(rows).toHaveLength(3);
  });
});
