import { Module } from '@nestjs/common';
import { PrismaModule } from '../prisma/prisma.module';
import { PortfolioController } from './portfolio.controller';
import { PortfolioRepository } from './portfolio.repository';
import { PortfolioService } from './portfolio.service';

@Module({
  imports: [PrismaModule],
  controllers: [PortfolioController],
  providers: [PortfolioRepository, PortfolioService],
})
export class PortfolioModule {}
