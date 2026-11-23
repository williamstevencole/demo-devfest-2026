import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { TraceStep } from "../types";
import { AgentTrace } from "./AgentTrace";

afterEach(cleanup);

const traceStep = (overrides: Partial<TraceStep>): TraceStep => ({
  id: "s1",
  node: "load_portfolio",
  kind: "tool_call",
  title: "Portafolio de María López",
  detail: "4 posiciones, $2,500 en efectivo",
  sources: [],
  status: "done",
  ...overrides,
});

describe("AgentTrace", () => {
  it("renderiza cada tipo de paso con estado, detalle y duración", () => {
    render(
      <AgentTrace
        steps={[
          traceStep({ id: "s1", kind: "tool_call", title: "Portafolio" }),
          traceStep({
            id: "s2",
            kind: "retrieval",
            title: "Conocimiento: diversificación",
            durationMs: 42,
          }),
          traceStep({
            id: "s3",
            kind: "web_search",
            title: "Web: China y chips",
          }),
          traceStep({
            id: "s4",
            kind: "decision",
            title: "Cobertura de evidencia",
            detail: "1/3 aspectos cubiertos; faltan: noticia",
          }),
          traceStep({
            id: "s5",
            kind: "answer",
            title: "Respuesta",
            status: "running",
          }),
        ]}
      />,
    );

    expect(screen.getByTestId("step-s1").getAttribute("data-kind")).toBe(
      "tool_call",
    );
    expect(screen.getByTestId("step-s2").getAttribute("data-kind")).toBe(
      "retrieval",
    );
    expect(screen.getByTestId("step-s3").getAttribute("data-kind")).toBe(
      "web_search",
    );
    expect(screen.getByTestId("step-s4").getAttribute("data-kind")).toBe(
      "decision",
    );
    expect(screen.getByTestId("step-s5").getAttribute("data-status")).toBe(
      "running",
    );
    expect(screen.getByText(/42 ms/)).toBeTruthy();
    expect(screen.queryByText(/faltan: noticia/)).toBeNull();
    expect(
      screen.getByTestId("step-s5").querySelector(".spinner"),
    ).not.toBeNull();
  });

  it("muestra solo la acción cuando el paso está cerrado", () => {
    render(
      <AgentTrace
        steps={[
          traceStep({
            id: "s2",
            kind: "retrieval",
            title: "Buscar en el conocimiento del broker: «ETF»",
            detail: "Consulta: «ETF» · 4 documentos encontrados",
          }),
        ]}
      />,
    );

    expect(
      screen.getByText("Buscar en el conocimiento del broker: «ETF»"),
    ).toBeTruthy();
    expect(screen.queryByText(/4 documentos encontrados/)).toBeNull();
  });

  it("al expandir muestra lo que encontró con su resumen", () => {
    render(
      <AgentTrace
        steps={[
          traceStep({
            id: "s3",
            kind: "web_search",
            title: "Buscar noticias: «Jensen Huang»",
            detail: "Consulta: «Jensen Huang» · 1 fuente · 2026-11-12",
            sources: ["https://example.com/huang"],
          }),
        ]}
        sources={[
          {
            kind: "web",
            label: "Jensen Huang Resigns as Nvidia CEO",
            detail:
              "www.wired.com · 2026-11-12 — Nvidia announced a leadership transition.",
            url: "https://example.com/huang",
          },
        ]}
      />,
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Ver detalle de Buscar noticias: «Jensen Huang»",
      }),
    );

    expect(screen.getByText("Lo que encontró")).toBeTruthy();
    expect(screen.getByText("Jensen Huang Resigns as Nvidia CEO")).toBeTruthy();
    expect(
      screen.getByText(
        "www.wired.com · 2026-11-12 — Nvidia announced a leadership transition.",
      ),
    ).toBeTruthy();
    const link = screen.getByRole("link", {
      name: "https://example.com/huang",
    });
    expect(link.getAttribute("href")).toBe("https://example.com/huang");
  });

  it("expande un paso y muestra sus fuentes", () => {
    render(
      <AgentTrace
        steps={[
          traceStep({
            id: "s2",
            kind: "retrieval",
            title: "Conocimiento: diversificación",
            detail: "2 documentos nuevos",
            sources: [
              "politicas_de_inversion_y_riesgo.md > Diversificación",
              "productos_disponibles.md > ETFs",
            ],
          }),
        ]}
      />,
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Ver detalle de Conocimiento: diversificación",
      }),
    );
    expect(screen.getByTestId("step-detail-s2")).toBeTruthy();
    expect(screen.getByTestId("step-detail-s2").textContent).toContain(
      "2 documentos nuevos",
    );
    expect(
      screen.getByText(
        "politicas_de_inversion_y_riesgo.md > Diversificación",
      ),
    ).toBeTruthy();
  });

  it("no duplica fuentes repetidas dentro de un paso", () => {
    render(
      <AgentTrace
        steps={[
          traceStep({
            id: "s2",
            kind: "retrieval",
            title: "Conocimiento: diversificación",
            sources: [
              "politicas_de_inversion_y_riesgo.md > Diversificación",
              "politicas_de_inversion_y_riesgo.md > Diversificación",
            ],
          }),
        ]}
      />,
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Ver detalle de Conocimiento: diversificación",
      }),
    );
    expect(
      screen.getAllByText("politicas_de_inversion_y_riesgo.md > Diversificación"),
    ).toHaveLength(1);
  });

  it("despliega el detalle de una fuente al abrirla", () => {
    render(
      <AgentTrace
        steps={[
          traceStep({
            id: "s2",
            kind: "retrieval",
            title: "Conocimiento local",
            sources: ["glosario_de_mercado.md > ETF"],
          }),
        ]}
        sources={[
          {
            kind: "document",
            label: "glosario_de_mercado.md > ETF",
            detail: "Un ETF es un fondo que se negocia en bolsa.",
          },
        ]}
      />,
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Ver detalle de Conocimiento local",
      }),
    );

    expect(
      screen.getByText("Un ETF es un fondo que se negocia en bolsa."),
    ).toBeTruthy();
  });

  it("muestra y enlaza una fuente web dentro del paso", () => {
    render(
      <AgentTrace
        steps={[
          traceStep({
            id: "s3",
            kind: "web_search",
            title: "Web: chips",
            sources: ["https://example.com/chips"],
          }),
        ]}
        sources={[
          {
            kind: "web",
            label: "Reuters · Chips",
            detail: "Reuters · 2026-11-17",
            url: "https://example.com/chips",
          },
        ]}
      />,
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Ver detalle de Web: chips" }),
    );

    expect(screen.getByText("Reuters · Chips")).toBeTruthy();
    expect(screen.getByText("Reuters · 2026-11-17")).toBeTruthy();
    const link = screen.getByRole("link", {
      name: "https://example.com/chips",
    });
    expect(link.getAttribute("href")).toBe("https://example.com/chips");
  });

  it("muestra un paso detenido sin check ni spinner", () => {
    render(
      <AgentTrace
        steps={[traceStep({ id: "s6", kind: "answer", status: "stopped" })]}
      />,
    );

    const step = screen.getByTestId("step-s6");
    expect(step.getAttribute("data-status")).toBe("stopped");
    expect(step.querySelector(".trace-check")).toBeNull();
    expect(step.querySelector(".spinner")).toBeNull();
  });

  it("marca reintento cuando la respuesta es insuficiente", () => {
    render(
      <AgentTrace
        insufficientData
        steps={[
          traceStep({
            id: "s4",
            kind: "decision",
            title: "Verificar si alcanza la información",
            detail: "Faltan datos: noticia reciente.",
          }),
        ]}
      />,
    );

    expect(screen.getByText("Reintento")).toBeTruthy();
  });

  it("no marca reintento cuando la cobertura está completa", () => {
    render(
      <AgentTrace
        steps={[
          traceStep({
            id: "s4",
            kind: "decision",
            title: "Cobertura de evidencia",
            detail: "3/3 aspectos cubiertos; faltan: ninguno.",
          }),
        ]}
      />,
    );

    expect(screen.queryByText("Reintento")).toBeNull();
  });

  it("vuelve a colapsar el paso al pulsar de nuevo", () => {
    render(
      <AgentTrace
        steps={[traceStep({ id: "s4", kind: "decision", title: "Cobertura" })]}
      />,
    );

    const toggle = screen.getByRole("button", {
      name: "Ver detalle de Cobertura",
    });
    fireEvent.click(toggle);
    expect(screen.getByTestId("step-detail-s4")).toBeTruthy();

    fireEvent.click(toggle);
    expect(screen.queryByTestId("step-detail-s4")).toBeNull();
  });
});
