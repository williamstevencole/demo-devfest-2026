import type { TraceKind, TraceStep } from "../types";

const KIND_NAMES: Record<TraceKind, string> = {
  tool_call: "Datos",
  retrieval: "Documentos",
  web_search: "Noticias",
  decision: "Decisión",
  answer: "Respuesta",
};

export function StepDetail({ step }: { step: TraceStep }) {
  return (
    <div className="step-panel" data-testid={`step-detail-${step.id}`}>
      <p className="step-detail">{step.detail}</p>
      <dl className="step-meta">
        <div>
          <dt>Nodo</dt>
          <dd>{step.node}</dd>
        </div>
        <div>
          <dt>Tipo</dt>
          <dd>{KIND_NAMES[step.kind]}</dd>
        </div>
      </dl>
    </div>
  );
}
