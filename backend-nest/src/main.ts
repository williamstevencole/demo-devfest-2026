import { INestApplication } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { NestFactory } from '@nestjs/core';
import { config as loadEnv } from 'dotenv';
import { resolve } from 'node:path';
import { AppModule } from './app.module';
import { ensureDatabaseDirectory } from './prisma/database-directory';
import { DEFAULT_DATABASE_URL } from './prisma/prisma.constants';

const DEFAULT_PORT = 3001;
const SCHEMA_DIR = resolve(__dirname, '..', 'prisma');
const ENV_FILE = process.env.ENV_FILE ?? '.env';

loadEnv({ path: ENV_FILE });

export async function bootstrap(): Promise<INestApplication> {
  const databaseUrl = process.env.DATABASE_URL ?? DEFAULT_DATABASE_URL;
  ensureDatabaseDirectory(databaseUrl, SCHEMA_DIR);

  const app = await NestFactory.create(AppModule);
  const config = app.get(ConfigService);

  app.setGlobalPrefix('api');

  const port = Number(config.get<number>('PORT') ?? DEFAULT_PORT);
  await app.listen(port, '0.0.0.0');

  return app;
}

if (require.main === module) {
  void bootstrap();
}
