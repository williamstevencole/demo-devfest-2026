import { describe, expect, it } from "vitest";

import type { ChatMessage } from "../types";
import { applyEvent, finishRunningSteps } from "./chatState";

function emptyAssistant(): ChatMessage {
  return {
    id: "a1",
    role: "assistant",
    content: "",
    steps: [],
    streaming: true,
    sources: [],
    disclaimerRequired: false,
  };
}

describe("applyEvent", () => {
  it("aplica un paso y un token", () => {
    let message = emptyAssistant();
    message = applyEvent(message, {
      type: "step",
      id: "s1",
      node: "load_portfolio",
      kind: "tool_call",
      title: "Portafolio",
      detail: "4 posiciones",
      sources: [],
      status: "done",
    });
    message = applyEvent(message, { type: "token", text: "Hola" });

    expect(message.steps[0].kind).toBe("tool_call");
    expect(message.content).toBe("Hola");
  });

  it("hace upsert de pasos por id y conserva durationMs", () => {
    const started = applyEvent(emptyAssistant(), {
      type: "step",
      id: "s1",
      node: "load_portfolio",
      kind: "tool_call",
      title: "Portafolio",
      detail: "cargando",
      sources: [],
      status: "running",
    });
    const finished = applyEvent(started, {
      type: "step",
      id: "s1",
      node: "load_portfolio",
      kind: "tool_call",
      title: "Portafolio",
      detail: "4 posiciones",
      sources: [],
      status: "done",
      durationMs: 42,
    });

    expect(finished.steps).toHaveLength(1);
    expect(finished.steps[0]).toMatchObject({
      status: "done",
      durationMs: 42,
    });
  });

  it("done guarda respuesta, traza final, fuentes y disclaimer", () => {
    const source = {
      kind: "document" as const,
      label: "políticas.md > Concentración",
      detail: "Diversificación y riesgo",
    };
    const done = applyEvent(emptyAssistant(), {
      type: "done",
      answer: "Tu exposición es 25.5%.",
      mode: "agent",
      trace: {
        steps: [
          {
            id: "s2",
            node: "respond",
            kind: "answer",
            title: "Respuesta",
            detail: "Sintetizó la respuesta",
            sources: ["políticas.md > Concentración"],
            status: "done",
            durationMs: 10,
          },
        ],
      },
      sources: [source],
      insufficientData: true,
      missingData: ["noticia reciente"],
      disclaimerRequired: true,
    });

    expect(done.content).toBe("Tu exposición es 25.5%.");
    expect(done.insufficientData).toBe(true);
    expect(done.missingData).toEqual(["noticia reciente"]);
    expect(done.steps[0].kind).toBe("answer");
    expect(done.sources).toEqual([source]);
    expect(done.disclaimerRequired).toBe(true);
    expect(done.streaming).toBe(false);
  });

  it("done sin traza final cierra los pasos activos", () => {
    const running = applyEvent(emptyAssistant(), {
      type: "step",
      id: "s1",
      node: "respond",
      kind: "answer",
      title: "Redactando",
      detail: "streaming",
      sources: [],
      status: "running",
    });

    const done = applyEvent(running, {
      type: "done",
      answer: "Listo",
      mode: "agent",
      trace: { steps: [] },
      sources: [],
      disclaimerRequired: false,
    });

    expect(done.steps[0].status).toBe("done");
    expect(done.streaming).toBe(false);
  });

  it("error cierra los pasos en ejecución sin dejar spinner", () => {
    const running = applyEvent(emptyAssistant(), {
      type: "step",
      id: "s1",
      node: "load_portfolio",
      kind: "tool_call",
      title: "Portafolio",
      detail: "cargando",
      sources: [],
      status: "running",
    });

    const failed = applyEvent(running, {
      type: "error",
      message: "El portafolio no está disponible",
    });

    expect(failed.steps[0].status).toBe("error");
    expect(failed.streaming).toBe(false);
    expect(failed.error).toBe("El portafolio no está disponible");
  });

  it("finishRunningSteps cierra solo los pasos activos", () => {
    const withSteps: ChatMessage = {
      ...emptyAssistant(),
      steps: [
        {
          id: "s1",
          node: "load_portfolio",
          kind: "tool_call",
          title: "Portafolio",
          detail: "listo",
          sources: [],
          status: "done",
        },
        {
          id: "s2",
          node: "respond",
          kind: "answer",
          title: "Redactando",
          detail: "streaming",
          sources: [],
          status: "running",
        },
      ],
    };

    expect(
      finishRunningSteps(withSteps, "done").steps.map((step) => step.status),
    ).toEqual(["done", "done"]);
    expect(
      finishRunningSteps(withSteps, "error").steps.map((step) => step.status),
    ).toEqual(["done", "error"]);
    expect(
      finishRunningSteps(withSteps, "stopped").steps.map((step) => step.status),
    ).toEqual(["done", "stopped"]);
  });
});
