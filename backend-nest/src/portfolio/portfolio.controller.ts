import { Controller, Get, Param } from '@nestjs/common';
import { PortfolioResponse } from './portfolio-response';
import { PortfolioService } from './portfolio.service';

@Controller('users')
export class PortfolioController {
  constructor(private readonly portfolios: PortfolioService) {}

  @Get(':userId/portfolio')
  getPortfolio(@Param('userId') userId: string): Promise<PortfolioResponse> {
    return this.portfolios.getPortfolio(userId);
  }
}
