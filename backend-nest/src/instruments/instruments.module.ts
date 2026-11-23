import { Module } from '@nestjs/common';
import { PrismaModule } from '../prisma/prisma.module';
import { InstrumentsController } from './instruments.controller';
import { InstrumentsRepository } from './instruments.repository';
import { InstrumentsService } from './instruments.service';

@Module({
  imports: [PrismaModule],
  controllers: [InstrumentsController],
  providers: [InstrumentsRepository, InstrumentsService],
})
export class InstrumentsModule {}
