import { RiskProfile, User } from '@prisma/client';

export interface UserResponse {
  id: string;
  identityNumber: string;
  name: string;
  email: string;
  riskProfile: RiskProfile;
  country: string;
  cashUsd: number;
}

export function toUserResponse(user: User): UserResponse {
  return {
    id: user.id,
    identityNumber: user.identityNumber,
    name: user.name,
    email: user.email,
    riskProfile: user.riskProfile,
    country: user.country,
    cashUsd: user.cashUsd,
  };
}
