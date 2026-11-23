import { existsSync, mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { ensureDatabaseDirectory } from './database-directory';

describe('ensureDatabaseDirectory', () => {
  let workDir: string;

  beforeEach(() => {
    workDir = mkdtempSync(join(tmpdir(), 'database-directory-'));
  });

  afterEach(() => {
    rmSync(workDir, { recursive: true, force: true });
  });

  it('crea el directorio anidado antes de conectar', () => {
    const databaseDir = join(workDir, 'nested', 'data');
    ensureDatabaseDirectory(
      `file:${join(databaseDir, 'broker.sqlite')}`,
      workDir,
    );
    expect(existsSync(databaseDir)).toBe(true);
  });
});
