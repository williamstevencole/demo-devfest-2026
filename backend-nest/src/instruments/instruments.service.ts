import { Injectable, NotFoundException } from '@nestjs/common';
import { InstrumentResponse } from './instrument-response';
import {
  InstrumentWithHoldings,
  InstrumentsRepository,
} from './instruments.repository';

function normalizeTicker(ticker: string): string {
  return ticker.trim().toUpperCase();
}

@Injectable()
export class InstrumentsService {
  constructor(private readonly instruments: InstrumentsRepository) {}

  async getByTicker(ticker: string): Promise<InstrumentResponse> {
    const normalized = normalizeTicker(ticker);
    const row = await this.instruments.findByTicker(normalized);
    if (!row) {
      throw new NotFoundException(
        `No encontramos el instrumento ${normalized}`,
      );
    }
    return toInstrumentResponse(row);
  }
}

function toInstrumentResponse(row: InstrumentWithHoldings): InstrumentResponse {
  return {
    ticker: row.ticker,
    name: row.name,
    type: row.type,
    sector: row.sector,
    priceUsd: row.price?.priceUsd ?? null,
    priceAsOf: row.price?.asOf ?? null,
    holdings: row.etfHoldings.map((holding) => ({
      componentTicker: holding.componentTicker,
      weightPct: holding.weightPct,
      componentName: holding.component.name,
      componentSector: holding.component.sector,
    })),
  };
}
