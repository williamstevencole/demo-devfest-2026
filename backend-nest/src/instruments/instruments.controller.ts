import { Controller, Get, Param } from '@nestjs/common';
import { InstrumentResponse } from './instrument-response';
import { InstrumentsService } from './instruments.service';

@Controller('instruments')
export class InstrumentsController {
  constructor(private readonly instruments: InstrumentsService) {}

  @Get(':ticker')
  getByTicker(@Param('ticker') ticker: string): Promise<InstrumentResponse> {
    return this.instruments.getByTicker(ticker);
  }
}
