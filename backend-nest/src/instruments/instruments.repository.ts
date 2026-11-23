import { Injectable } from '@nestjs/common';
import { Prisma } from '@prisma/client';
import { PrismaService } from '../prisma/prisma.service';

export type InstrumentWithHoldings = Prisma.InstrumentGetPayload<{
  include: {
    price: true;
    etfHoldings: {
      include: { component: { select: { name: true; sector: true } } };
    };
  };
}>;

@Injectable()
export class InstrumentsRepository {
  constructor(private readonly prisma: PrismaService) {}

  findByTicker(ticker: string): Promise<InstrumentWithHoldings | null> {
    return this.prisma.instrument.findUnique({
      where: { ticker },
      include: {
        price: true,
        etfHoldings: {
          include: { component: { select: { name: true, sector: true } } },
          orderBy: { weightPct: 'desc' },
        },
      },
    });
  }
}
