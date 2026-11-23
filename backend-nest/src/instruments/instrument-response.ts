import { InstrumentType } from '@prisma/client';

export interface EtfHoldingResponse {
  componentTicker: string;
  weightPct: number;
  componentName?: string;
  componentSector?: string | null;
}

export interface InstrumentResponse {
  ticker: string;
  name: string;
  type: InstrumentType;
  sector: string | null;
  priceUsd: number | null;
  priceAsOf: Date | null;
  holdings?: EtfHoldingResponse[];
}
