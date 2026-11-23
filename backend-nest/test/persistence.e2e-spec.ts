import { INestApplication } from '@nestjs/common';
import { Test, TestingModule } from '@nestjs/testing';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { AppModule } from './../src/app.module';
import { PrismaService } from './../src/prisma/prisma.service';

const EXPECTED_TABLES = [
  'etf_holdings',
  'instruments',
  'positions',
  'prices',
  'users',
];

type SqliteMasterRow = { name: string };

describe('Persistence (e2e)', () => {
  let app: INestApplication;
  let prisma: PrismaService;
  let tempDir: string;

  beforeAll(async () => {
    tempDir = mkdtempSync(join(tmpdir(), 'persistence-e2e-'));
    const databaseUrl = `file:${join(tempDir, 'broker.sqlite')}`;
    process.env.DATABASE_URL = databaseUrl;

    runPrismaDbPush(databaseUrl);

    const moduleFixture: TestingModule = await Test.createTestingModule({
      imports: [AppModule],
    }).compile();

    app = moduleFixture.createNestApplication();
    await app.init();
    prisma = app.get(PrismaService);
  });

  afterAll(async () => {
    await app.close();
    rmSync(tempDir, { recursive: true, force: true });
  });

  it('creates the five expected tables', async () => {
    const rows = await prisma.$queryRawUnsafe<SqliteMasterRow[]>(
      "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'",
    );
    const tableNames = rows.map((row) => row.name).sort();

    expect(tableNames).toEqual([...EXPECTED_TABLES].sort());
  });
});

function runPrismaDbPush(databaseUrl: string): void {
  execFileSync(
    join(process.cwd(), 'node_modules', '.bin', 'prisma'),
    ['db', 'push', '--skip-generate'],
    {
      cwd: process.cwd(),
      env: { ...process.env, DATABASE_URL: databaseUrl },
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'pipe'],
    },
  );
}
