import { execFileSync } from 'node:child_process';
import { resolve } from 'node:path';

const PROJECT_DIR = resolve(__dirname, '..');

export function pushSchema(databaseUrl: string): void {
  execFileSync('npx', ['prisma', 'db', 'push', '--skip-generate'], {
    cwd: PROJECT_DIR,
    env: { ...process.env, DATABASE_URL: databaseUrl },
    stdio: 'ignore',
  });
}
