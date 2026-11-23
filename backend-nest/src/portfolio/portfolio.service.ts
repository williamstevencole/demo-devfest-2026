import { Inject, Injectable, NotFoundException } from '@nestjs/common';
import { roundPct, roundUsd } from '../common/money';
import { PortfolioRepository } from './portfolio.repository';
import type { PortfolioReader, PortfolioRecord } from './portfolio.repository';
import { PortfolioResponse, PositionResponse } from './portfolio-response';

@Injectable()
export class PortfolioService {
  constructor(
    @Inject(PortfolioRepository) private readonly portfolios: PortfolioReader,
  ) {}

  async getPortfolio(userId: string): Promise<PortfolioResponse> {
    const record = await this.portfolios.findPortfolio(userId);
    if (!record) {
      throw new NotFoundException(`No encontramos el usuario ${userId}`);
    }
    return this.buildResponse(record);
  }

  private buildResponse(record: PortfolioRecord): PortfolioResponse {
    const cashUsd = roundUsd(record.user.cashUsd);
    const investedUsd = roundUsd(
      record.positions.reduce(
        (total, position) =>
          total + marketValue(position.quantity, position.priceUsd),
        0,
      ),
    );
    return {
      user: record.user,
      positions: record.positions.map((position) =>
        toPositionResponse(position, investedUsd),
      ),
      cashUsd,
      investedUsd,
      totalUsd: roundUsd(investedUsd + cashUsd),
    };
  }
}

function marketValue(quantity: number, priceUsd: number | null): number {
  return quantity * (priceUsd ?? 0);
}

type PositionRecord = PortfolioRecord['positions'][number];

function toPositionResponse(
  position: PositionRecord,
  investedUsd: number,
): PositionResponse {
  const priceUsd = position.priceUsd ?? 0;
  const marketValueUsd = roundUsd(
    marketValue(position.quantity, position.priceUsd),
  );
  return {
    ticker: position.ticker,
    name: position.name,
    type: position.type,
    sector: position.sector,
    quantity: position.quantity,
    avgCostUsd: position.avgCostUsd,
    priceUsd,
    marketValueUsd,
    weightPct:
      investedUsd === 0 ? 0 : roundPct((marketValueUsd / investedUsd) * 100),
    unrealizedPnlUsd: roundUsd(
      (priceUsd - position.avgCostUsd) * position.quantity,
    ),
    priceAsOf: position.priceAsOf,
    etfHoldings: position.etfHoldings,
  };
}
