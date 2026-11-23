import { Injectable, OnApplicationBootstrap } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import {
  SEED_ETF_HOLDINGS,
  SEED_INSTRUMENTS,
  SEED_POSITIONS,
  SEED_PRICES,
  SEED_USERS,
} from './seed.data';

@Injectable()
export class SeedService implements OnApplicationBootstrap {
  constructor(private readonly prisma: PrismaService) {}

  async onApplicationBootstrap(): Promise<void> {
    await this.run();
  }

  async run(): Promise<void> {
    const reset = (process.env.SEED_RESET ?? 'true').toLowerCase() !== 'false';

    await this.prisma.$transaction(async (tx) => {
      if (reset) {
        const seededUserIds = SEED_USERS.map((user) => user.id);
        const seededTickers = SEED_INSTRUMENTS.map(
          (instrument) => instrument.ticker,
        );
        await tx.position.deleteMany({});
        await tx.etfHolding.deleteMany({});
        await tx.price.deleteMany({});
        await tx.user.deleteMany({
          where: { id: { notIn: seededUserIds } },
        });
        await tx.instrument.deleteMany({
          where: { ticker: { notIn: seededTickers } },
        });
      }
      for (const user of SEED_USERS) {
        await tx.user.upsert({
          where: { id: user.id },
          update: user,
          create: user,
        });
      }
      for (const instrument of SEED_INSTRUMENTS) {
        await tx.instrument.upsert({
          where: { ticker: instrument.ticker },
          update: instrument,
          create: instrument,
        });
      }
      for (const price of SEED_PRICES) {
        await tx.price.upsert({
          where: { ticker: price.ticker },
          update: { priceUsd: price.priceUsd, asOf: price.asOf },
          create: price,
        });
      }
      for (const position of SEED_POSITIONS) {
        await tx.position.upsert({
          where: {
            userId_ticker: { userId: position.userId, ticker: position.ticker },
          },
          update: {
            quantity: position.quantity,
            avgCostUsd: position.avgCostUsd,
          },
          create: position,
        });
      }
      for (const holding of SEED_ETF_HOLDINGS) {
        await tx.etfHolding.upsert({
          where: {
            etfTicker_componentTicker: {
              etfTicker: holding.etfTicker,
              componentTicker: holding.componentTicker,
            },
          },
          update: { weightPct: holding.weightPct },
          create: holding,
        });
      }
    });
  }
}
