import { InstrumentType, Prisma, RiskProfile } from '@prisma/client';

export const SEED_AS_OF = new Date('2026-11-17T00:00:00.000Z');

export const SEED_USERS: Prisma.UserUncheckedCreateInput[] = [
  {
    id: 'maria-lopez',
    identityNumber: 'DEMO-0000-12345',
    name: 'María López',
    email: 'maria.lopez@example.com',
    riskProfile: RiskProfile.MODERATE,
    country: 'Honduras',
    cashUsd: 2500,
  },
];

export const SEED_INSTRUMENTS: Prisma.InstrumentUncheckedCreateInput[] = [
  {
    ticker: 'NVDA',
    name: 'NVIDIA Corporation',
    type: InstrumentType.STOCK,
    sector: 'Technology',
  },
  {
    ticker: 'AAPL',
    name: 'Apple Inc.',
    type: InstrumentType.STOCK,
    sector: 'Technology',
  },
  {
    ticker: 'VOO',
    name: 'Vanguard S&P 500 ETF',
    type: InstrumentType.ETF,
    sector: 'Broad Market',
  },
  {
    ticker: 'KO',
    name: 'The Coca-Cola Company',
    type: InstrumentType.STOCK,
    sector: 'Consumer Staples',
  },
  {
    ticker: 'BND',
    name: 'Vanguard Total Bond Market ETF',
    type: InstrumentType.ETF,
    sector: 'Fixed Income',
  },
  {
    ticker: 'MSFT',
    name: 'Microsoft Corporation',
    type: InstrumentType.STOCK,
    sector: 'Technology',
  },
  {
    ticker: 'AMZN',
    name: 'Amazon.com, Inc.',
    type: InstrumentType.STOCK,
    sector: 'Consumer Discretionary',
  },
  {
    ticker: 'META',
    name: 'Meta Platforms, Inc.',
    type: InstrumentType.STOCK,
    sector: 'Communication Services',
  },
  {
    ticker: 'GOOGL',
    name: 'Alphabet Inc.',
    type: InstrumentType.STOCK,
    sector: 'Communication Services',
  },
  {
    ticker: 'AVGO',
    name: 'Broadcom Inc.',
    type: InstrumentType.STOCK,
    sector: 'Technology',
  },
  {
    ticker: 'TSLA',
    name: 'Tesla, Inc.',
    type: InstrumentType.STOCK,
    sector: 'Consumer Discretionary',
  },
  {
    ticker: 'COST',
    name: 'Costco Wholesale Corporation',
    type: InstrumentType.STOCK,
    sector: 'Consumer Staples',
  },
  {
    ticker: 'NFLX',
    name: 'Netflix, Inc.',
    type: InstrumentType.STOCK,
    sector: 'Communication Services',
  },
  {
    ticker: 'BRK.B',
    name: 'Berkshire Hathaway Inc.',
    type: InstrumentType.STOCK,
    sector: 'Financials',
  },
  {
    ticker: 'JPM',
    name: 'JPMorgan Chase & Co.',
    type: InstrumentType.STOCK,
    sector: 'Financials',
  },
];

export const SEED_PRICES: Prisma.PriceUncheckedCreateInput[] = [
  { ticker: 'NVDA', priceUsd: 180, asOf: SEED_AS_OF },
  { ticker: 'AAPL', priceUsd: 230, asOf: SEED_AS_OF },
  { ticker: 'VOO', priceUsd: 550, asOf: SEED_AS_OF },
  { ticker: 'KO', priceUsd: 62, asOf: SEED_AS_OF },
  { ticker: 'BND', priceUsd: 73, asOf: SEED_AS_OF },
];

export const SEED_POSITIONS: Prisma.PositionUncheckedCreateInput[] = [
  { userId: 'maria-lopez', ticker: 'NVDA', quantity: 20, avgCostUsd: 150 },
  { userId: 'maria-lopez', ticker: 'VOO', quantity: 15, avgCostUsd: 500 },
  { userId: 'maria-lopez', ticker: 'AAPL', quantity: 5, avgCostUsd: 200 },
];

export const SEED_ETF_HOLDINGS: Prisma.EtfHoldingUncheckedCreateInput[] = [
  { etfTicker: 'VOO', componentTicker: 'NVDA', weightPct: 7 },
  { etfTicker: 'VOO', componentTicker: 'AAPL', weightPct: 6.5 },
  { etfTicker: 'VOO', componentTicker: 'MSFT', weightPct: 6 },
  { etfTicker: 'VOO', componentTicker: 'AMZN', weightPct: 3.5 },
  { etfTicker: 'VOO', componentTicker: 'GOOGL', weightPct: 3 },
  { etfTicker: 'VOO', componentTicker: 'META', weightPct: 2.5 },
  { etfTicker: 'VOO', componentTicker: 'AVGO', weightPct: 2.5 },
  { etfTicker: 'VOO', componentTicker: 'TSLA', weightPct: 2 },
  { etfTicker: 'VOO', componentTicker: 'BRK.B', weightPct: 1.6 },
  { etfTicker: 'VOO', componentTicker: 'JPM', weightPct: 1.3 },
];
