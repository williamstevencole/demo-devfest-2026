import { mkdirSync } from 'node:fs';
import { dirname, isAbsolute, resolve } from 'node:path';

export function ensureDatabaseDirectory(
  databaseUrl: string,
  schemaDir: string,
): void {
  const filePath = databaseUrl.replace(/^file:/, '');
  const absolutePath = isAbsolute(filePath)
    ? filePath
    : resolve(schemaDir, filePath);
  mkdirSync(dirname(absolutePath), { recursive: true });
}
