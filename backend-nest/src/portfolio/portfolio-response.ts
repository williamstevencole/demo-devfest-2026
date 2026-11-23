import { InstrumentType } from '@prisma/client';
import { EtfHoldingResponse } from '../instruments/instrument-response';
import { UserResponse } from '../users/user-response';

export interface PositionResponse {
  ticker: string;
  name: string;
  type: InstrumentType;
  sector: string | null;
  quantity: number;
  avgCostUsd: number;
  priceUsd: number;
  marketValueUsd: number;
  weightPct: number;
  unrealizedPnlUsd: number;
  priceAsOf: Date | null;
  etfHoldings: EtfHoldingResponse[];
}

export interface PortfolioResponse {
  user: UserResponse;
  positions: PositionResponse[];
  cashUsd: number;
  investedUsd: number;
  totalUsd: number;
}
