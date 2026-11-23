import type {
  ChatResponse,
  PortfolioAnalysis,
  SourceRef,
  TraceKind,
  TraceStep,
} from "../types";

interface WireTraceStep {
  id: string;
  node: string;
  kind: TraceKind;
  title: string;
  detail: string;
  sources?: string[];
  status: TraceStep["status"];
  duration_ms?: number;
}

interface WireChatResponse {
  answer: string;
  mode: ChatResponse["mode"];
  trace?: { steps?: WireTraceStep[] };
  sources?: SourceRef[];
  insufficient_data?: boolean;
  missing_data?: string[];
  disclaimer_required?: boolean;
}

function ensureOk(response: Response): void {
  if (!response.ok) {
    throw new Error(`El servidor respondió ${response.status}`);
  }
}

export function mapTraceStep(step: WireTraceStep): TraceStep {
  const { duration_ms: durationMs, sources, ...rest } = step;
  return {
    ...rest,
    sources: sources ?? [],
    durationMs,
  };
}

export function mapChatResponse(wire: WireChatResponse): ChatResponse {
  return {
    answer: wire.answer,
    mode: wire.mode,
    trace: { steps: (wire.trace?.steps ?? []).map(mapTraceStep) },
    sources: wire.sources ?? [],
    insufficientData: wire.insufficient_data === true,
    missingData: wire.missing_data ?? [],
    disclaimerRequired: wire.disclaimer_required === true,
  };
}

export async function getPortfolio(
  userId: string,
  signal?: AbortSignal,
): Promise<PortfolioAnalysis> {
  const response = await fetch(
    `/api/portfolio/${encodeURIComponent(userId)}`,
    { signal },
  );
  ensureOk(response);
  return (await response.json()) as PortfolioAnalysis;
}
