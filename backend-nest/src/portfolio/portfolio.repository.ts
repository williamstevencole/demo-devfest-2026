import { Injectable } from '@nestjs/common';
import { InstrumentType } from '@prisma/client';
import { PrismaService } from '../prisma/prisma.service';
import { toUserResponse, UserResponse } from '../users/user-response';

export interface PortfolioPositionRecord {
  ticker: string;
  name: string;
  type: InstrumentType;
  sector: string | null;
  quantity: number;
  avgCostUsd: number;
  priceUsd: number | null;
  priceAsOf: Date | null;
  etfHoldings: {
    componentTicker: string;
    weightPct: number;
    componentName: string;
    componentSector: string | null;
  }[];
}

export interface PortfolioRecord {
  user: UserResponse;
  positions: PortfolioPositionRecord[];
}

export interface PortfolioReader {
  findPortfolio(userId: string): Promise<PortfolioRecord | null>;
}

@Injectable()
export class PortfolioRepository implements PortfolioReader {
  constructor(private readonly prisma: PrismaService) {}

  async findPortfolio(userId: string): Promise<PortfolioRecord | null> {
    const user = await this.prisma.user.findUnique({
      where: { id: userId },
      include: {
        positions: {
          include: {
            instrument: {
              include: {
                price: true,
                etfHoldings: {
                  include: {
                    component: { select: { name: true, sector: true } },
                  },
                  orderBy: { weightPct: 'desc' },
                },
              },
            },
          },
          orderBy: { ticker: 'asc' },
        },
      },
    });
    if (!user) {
      return null;
    }
    return {
      user: toUserResponse(user),
      positions: user.positions.map((position) => ({
        ticker: position.ticker,
        name: position.instrument.name,
        type: position.instrument.type,
        sector: position.instrument.sector,
        quantity: position.quantity,
        avgCostUsd: position.avgCostUsd,
        priceUsd: position.instrument.price?.priceUsd ?? null,
        priceAsOf: position.instrument.price?.asOf ?? null,
        etfHoldings: position.instrument.etfHoldings.map((holding) => ({
          componentTicker: holding.componentTicker,
          weightPct: holding.weightPct,
          componentName: holding.component.name,
          componentSector: holding.component.sector,
        })),
      })),
    };
  }
}
