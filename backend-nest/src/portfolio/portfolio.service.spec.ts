import { InstrumentType, RiskProfile } from '@prisma/client';
import { PortfolioReader, PortfolioRecord } from './portfolio.repository';
import { PortfolioService } from './portfolio.service';

const MARIA: PortfolioRecord = {
  user: {
    id: 'maria-lopez',
    identityNumber: 'DEMO-0000-12345',
    name: 'María López',
    email: 'maria.lopez@example.com',
    riskProfile: RiskProfile.MODERATE,
    country: 'Honduras',
    cashUsd: 2500,
  },
  positions: [
    position('NVDA', 20, 150, 180, null),
    position('VOO', 15, 500, 550, [
      {
        componentTicker: 'NVDA',
        weightPct: 7,
        componentName: 'NVIDIA Corporation',
        componentSector: 'Technology',
      },
      {
        componentTicker: 'AAPL',
        weightPct: 6.5,
        componentName: 'Apple Inc.',
        componentSector: 'Technology',
      },
      {
        componentTicker: 'MSFT',
        weightPct: 6,
        componentName: 'Microsoft Corporation',
        componentSector: 'Technology',
      },
      {
        componentTicker: 'AMZN',
        weightPct: 3.5,
        componentName: 'Amazon.com, Inc.',
        componentSector: 'Consumer Discretionary',
      },
      {
        componentTicker: 'GOOGL',
        weightPct: 3,
        componentName: 'Alphabet Inc.',
        componentSector: 'Communication Services',
      },
    ]),
    position('AAPL', 5, 200, 230, null),
  ],
};

const repository: PortfolioReader = {
  findPortfolio: (userId) =>
    Promise.resolve(userId === 'maria-lopez' ? MARIA : null),
};

const service = new PortfolioService(repository);

function position(
  ticker: string,
  quantity: number,
  avgCostUsd: number,
  priceUsd: number,
  etfHoldings:
    | {
        componentTicker: string;
        weightPct: number;
        componentName: string;
        componentSector: string | null;
      }[]
    | null,
) {
  return {
    ticker,
    name: ticker,
    type:
      ticker === 'NVDA' || ticker === 'AAPL'
        ? InstrumentType.STOCK
        : InstrumentType.ETF,
    sector: 'Technology',
    quantity,
    avgCostUsd,
    priceUsd,
    priceAsOf: new Date('2026-11-17T00:00:00.000Z'),
    etfHoldings: etfHoldings ?? [],
  };
}

describe('PortfolioService', () => {
  it('calcula María', async () => {
    const portfolio = await service.getPortfolio('maria-lopez');
    expect(portfolio.investedUsd).toBe(13000);
    expect(portfolio.totalUsd).toBe(15500);
    expect(portfolio.cashUsd).toBe(2500);
    const nvda = portfolio.positions.find((item) => item.ticker === 'NVDA');
    expect(nvda?.marketValueUsd).toBe(3600);
    expect(nvda?.weightPct).toBe(27.7);
    expect(nvda?.unrealizedPnlUsd).toBe(600);
  });

  it('lanza 404 para un usuario inexistente', async () => {
    await expect(service.getPortfolio('nadie')).rejects.toMatchObject({
      status: 404,
    });
  });
});
