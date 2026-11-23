export type ChatMode = "agent" | "naive";

export interface ClientUser {
  id: string;
  name: string;
  riskProfile: string;
}
export type TraceKind =
  | "tool_call"
  | "retrieval"
  | "web_search"
  | "decision"
  | "answer";
export type StepStatus = "running" | "done" | "error" | "stopped";

export interface SourceRef {
  kind: "document" | "web";
  label: string;
  detail: string;
  url?: string | null;
}

export interface TraceStep {
  id: string;
  node: string;
  kind: TraceKind;
  title: string;
  detail: string;
  sources: string[];
  status: StepStatus;
  durationMs?: number;
}

export interface EtfHolding {
  componentTicker: string;
  weightPct: number;
}

export interface PortfolioPosition {
  ticker: string;
  name: string;
  type: "STOCK" | "ETF";
  sector: string | null;
  quantity: number;
  avgCostUsd: number;
  priceUsd: number;
  marketValueUsd: number;
  weightPct: number;
  unrealizedPnlUsd: number;
  priceAsOf: string | null;
  etfHoldings: EtfHolding[];
}

export interface Exposure {
  ticker: string;
  direct_usd: number;
  indirect_usd: number;
  total_usd: number;
  weight_pct: number;
}

export interface SectorExposure {
  sector: string;
  direct_usd: number;
  indirect_usd: number;
  total_usd: number;
  weight_pct: number;
}

export interface PortfolioAnalysis {
  invested_usd: number;
  total_value_usd: number;
  cash_usd: number;
  cost_usd: number;
  unrealized_pnl_usd: number;
  positions: PortfolioPosition[];
  exposures: Exposure[];
  sectors: SectorExposure[];
}

export interface HistoryMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatRequest {
  user_id: string;
  query: string;
  mode: ChatMode;
  history?: HistoryMessage[];
}

export interface ChatResponse {
  answer: string;
  mode: ChatMode;
  trace: { steps: TraceStep[] };
  sources: SourceRef[];
  insufficientData?: boolean;
  missingData?: string[];
  disclaimerRequired: boolean;
}

export type ChatEvent =
  | ({ type: "step" } & TraceStep)
  | { type: "token"; text: string }
  | ({ type: "done" } & ChatResponse)
  | { type: "error"; message: string };

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  steps: TraceStep[];
  streaming: boolean;
  error?: string;
  sources: SourceRef[];
  insufficientData?: boolean;
  missingData?: string[];
  disclaimerRequired: boolean;
  request?: ChatRequest;
}

export interface Conversation {
  id: string;
  userId: string;
  title: string;
  mode: ChatMode;
  messages: ChatMessage[];
  createdAt: string;
  updatedAt: string;
}
