import { useState } from "react";

import type { SourceRef, TraceKind, TraceStep } from "../types";
import { StepDetail } from "./StepDetail";
import { StepGlyph } from "./StepGlyph";

const KIND_LABELS: Record<TraceKind, string> = {
  tool_call: "Datos",
  retrieval: "Documentos",
  web_search: "Web",
  decision: "Decisión",
  answer: "Respuesta",
};

function formatDuration(step: TraceStep): string {
  return step.durationMs == null ? "" : `${Math.round(step.durationMs)} ms`;
}

function needsRetry(step: TraceStep, insufficientData: boolean): boolean {
  return (
    insufficientData &&
    step.kind === "decision" &&
    step.title.startsWith("Verificar")
  );
}

function uniqueSources(sources: string[]): string[] {
  return Array.from(new Set(sources.filter(Boolean)));
}

function findSource(source: string, sources: SourceRef[]): SourceRef | undefined {
  return sources.find(
    (candidate) => candidate.label === source || candidate.url === source,
  );
}

interface AgentTraceProps {
  steps: TraceStep[];
  sources?: SourceRef[];
  insufficientData?: boolean;
}

export function AgentTrace({
  steps,
  sources = [],
  insufficientData = false,
}: AgentTraceProps) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  if (steps.length === 0) return null;

  const toggle = (id: string) => {
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const running = steps.some((step) => step.status === "running");

  return (
    <section className="trace" aria-label="Actividad del agente">
          <div className="trace-head">
            <span className="trace-head-title">Actividad del agente</span>
            <span className={`trace-head-status${running ? " is-running" : ""}`}>
              {running ? "Trabajando…" : `${steps.length} pasos`}
            </span>
          </div>

          <ol className="trace-list">
            {steps.map((step, index) => {
              const isOpen = expanded.has(step.id);
              const stepSources = uniqueSources(step.sources);

              return (
                <li
                  key={step.id}
                  className={`trace-item is-${step.status} kind-${step.kind}${isOpen ? " is-open" : ""}`}
                  data-testid={`step-${step.id}`}
                  data-status={step.status}
                  data-kind={step.kind}
                >
                  <div className="trace-rail">
                    <span className={`trace-dot kind-${step.kind}`}>
                      {step.status === "done" ? (
                        <svg
                          className="trace-check"
                          viewBox="0 0 24 24"
                          width="12"
                          height="12"
                          aria-hidden="true"
                        >
                          <path d="m5 12.5 4.5 4.5L19 7.5" />
                        </svg>
                      ) : (
                        <StepGlyph kind={step.kind} />
                      )}
                      {step.status === "running" && (
                        <span className="spinner" aria-hidden="true" />
                      )}
                    </span>
                    {index < steps.length - 1 && <span className="trace-line" />}
                  </div>

                  <div className="trace-content">
                    <button
                      type="button"
                      className="trace-toggle"
                      aria-expanded={isOpen}
                      aria-label={`Ver detalle de ${step.title}`}
                      onClick={() => toggle(step.id)}
                    >
                      <span className="trace-copy">
                        <span className="trace-kind-row">
                          <span className="trace-kind">
                            {KIND_LABELS[step.kind]}
                          </span>
                          {needsRetry(step, insufficientData) && (
                            <span className="trace-retry">Reintento</span>
                          )}
                          {formatDuration(step) && (
                            <span className="trace-duration">
                              {formatDuration(step)}
                            </span>
                          )}
                        </span>
                        <span className="trace-label">{step.title}</span>
                      </span>
                      <svg
                        className="trace-chevron"
                        viewBox="0 0 24 24"
                        width="14"
                        height="14"
                        aria-hidden="true"
                      >
                        <path d="m8 5 7 7-7 7" />
                      </svg>
                    </button>

                    {isOpen && (
                      <>
                        <StepDetail step={step} />
                        {stepSources.length > 0 && (
                          <div className="trace-findings">
                            <span className="trace-findings-title">
                              {step.kind === "answer"
                                ? "Fuentes citadas"
                                : "Lo que encontró"}
                            </span>
                            <ul
                              className="trace-sources"
                              aria-label={`Fuentes de ${step.title}`}
                            >
                              {stepSources.map((source) => {
                                const ref = findSource(source, sources);
                                return (
                                  <li key={source}>
                                    {ref ? (
                                      <div className="trace-source">
                                        <span className="trace-source-label">
                                          {ref.label}
                                        </span>
                                        <p className="trace-source-detail">
                                          {ref.detail}
                                        </p>
                                        {ref.url && (
                                          <a
                                            className="trace-source-link"
                                            href={ref.url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                          >
                                            {ref.url}
                                          </a>
                                        )}
                                      </div>
                                    ) : (
                                      <span className="trace-source-raw">
                                        {source}
                                      </span>
                                    )}
                                  </li>
                                );
                              })}
                            </ul>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                </li>
              );
            })}
          </ol>
    </section>
  );
}
