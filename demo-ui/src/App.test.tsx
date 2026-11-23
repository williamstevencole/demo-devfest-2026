import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";

function sseResponse(payloads: unknown[]): Response {
  const encoder = new TextEncoder();
  const body = payloads
    .map((payload) => `data: ${JSON.stringify(payload)}\n\n`)
    .join("");
  const stream = new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode(body));
      controller.close();
    },
  });
  return new Response(stream, {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  });
}

function jsonResponse(payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

const portfolioPayload = {
  invested_usd: 13000,
  total_value_usd: 15500,
  cash_usd: 2500,
  cost_usd: 11500,
  unrealized_pnl_usd: 1500,
  positions: [
    {
      ticker: "VOO",
      name: "Vanguard S&P 500 ETF",
      type: "ETF",
      sector: "Broad Market",
      quantity: 15,
      avgCostUsd: 500,
      priceUsd: 550,
      marketValueUsd: 8250,
      weightPct: 63.5,
      unrealizedPnlUsd: 750,
      priceAsOf: "2026-11-17T00:00:00.000Z",
      etfHoldings: [{ componentTicker: "NVDA", weightPct: 7 }],
    },
  ],
  exposures: [
    {
      ticker: "NVDA",
      direct_usd: 3600,
      indirect_usd: 577.5,
      total_usd: 4177.5,
      weight_pct: 32.1,
    },
  ],
  sectors: [],
};

const trace = {
  steps: [
    {
      id: "s1",
      node: "load_portfolio",
      kind: "tool_call",
      title: "Portafolio de María López",
      detail: "4 posiciones, $2,500.00 en efectivo",
      sources: [],
      status: "done",
      duration_ms: 42,
    },
    {
      id: "s2",
      node: "research",
      kind: "retrieval",
      title: "Conocimiento: exposición a chips",
      detail: "2 documentos nuevos",
      sources: [
        "politicas_de_inversion_y_riesgo.md > Diversificación",
      ],
      status: "done",
      duration_ms: 18,
    },
    {
      id: "s3",
      node: "research",
      kind: "web_search",
      title: "Web: China restringe chips",
      detail: "1 fuente nueva",
      sources: ["https://example.com/chips"],
      status: "done",
      duration_ms: 30,
    },
    {
      id: "s4",
      node: "check",
      kind: "decision",
      title: "Verificar si alcanza la información",
      detail: "Faltan datos: noticia reciente.",
      sources: [],
      status: "done",
      duration_ms: 12,
    },
  ],
};

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.localStorage.clear();
  delete (Element.prototype as { scrollIntoView?: unknown }).scrollIntoView;
});

describe("App", () => {
  it("reintenta la consulta del mensaje fallido, no la última consulta", async () => {
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, init?: RequestInit) => {
        const body = JSON.parse(String(init?.body)) as { query: string };
        if (body.query === "Pregunta A" && fetchMock.mock.calls.length === 1) {
          return sseResponse([
            { type: "error", message: "El agente falló con A" },
          ]);
        }
        if (body.query === "Pregunta B") {
          return sseResponse([
            {
              type: "done",
              answer: "Respuesta B",
              mode: "agent",
              trace: { steps: [] },
              sources: [],
            },
          ]);
        }
        return sseResponse([
          {
            type: "done",
            answer: "Respuesta A",
            mode: "agent",
            trace: { steps: [] },
            sources: [],
          },
        ]);
      },
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    const input = screen.getByLabelText("Mensaje");

    fireEvent.change(input, { target: { value: "Pregunta A" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect((await screen.findByRole("alert")).textContent).toContain(
      "El agente falló con A",
    );

    fireEvent.change(input, { target: { value: "Pregunta B" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(await screen.findByText("Respuesta B")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(await screen.findByText("Respuesta A")).toBeTruthy();

    const retryBody = JSON.parse(
      String(fetchMock.mock.calls[2][1]?.body),
    ) as { query: string };
    expect(retryBody.query).toBe("Pregunta A");
  });

  it("envía como agente para María y muestra traza, reintento y disclaimer", async () => {
    const fetchMock = vi.fn(async () =>
      sseResponse([
        { type: "step", ...trace.steps[0] },
        {
          type: "token",
          text: "Tu exposición a NVDA es 25.5%.",
        },
        {
          type: "done",
          answer:
            "Tu exposición a NVDA es 25.5%.",
          mode: "agent",
          trace,
          sources: [
            {
              kind: "document",
              label:
                "politicas_de_inversion_y_riesgo.md > Diversificación",
              detail: "Política de diversificación y riesgo.",
              url: null,
            },
            {
              kind: "web",
              label: "Reuters · Restricción de chips",
              detail: "Reuters · 2026-11-17",
              url: "https://example.com/chips",
            },
          ],
          insufficient_data: true,
          missing_data: ["noticia reciente"],
          disclaimer_required: true,
        },
      ]),
    );
    vi.stubGlobal("fetch", fetchMock);

    const scrollSpy = vi.fn();
    Element.prototype.scrollIntoView = scrollSpy;
    const { container } = render(<App />);

    const input = screen.getByLabelText("Mensaje");
    fireEvent.change(input, { target: { value: "¿Me afecta China?" } });
    fireEvent.keyDown(input, { key: "Enter" });

    expect(await screen.findByText(/Tu exposición a NVDA es 25.5%/)).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/chat/stream",
      expect.objectContaining({
        body: JSON.stringify({
          user_id: "maria-lopez",
          query: "¿Me afecta China?",
          mode: "agent",
        }),
      }),
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
    expect(screen.getByText("Reintento")).toBeTruthy();
    expect(screen.getByText(/42 ms/)).toBeTruthy();
    fireEvent.click(
      screen.getByRole("button", {
        name: "Ver detalle de Web: China restringe chips",
      }),
    );
    fireEvent.click(screen.getByText("Reuters · Restricción de chips"));
    expect(
      screen.getByRole("link", { name: "https://example.com/chips" }),
    ).toBeTruthy();
    expect(screen.getByText(/no es asesoría/i)).toBeTruthy();
    expect(
      screen.getByRole("button", { name: /Nueva conversación/ }),
    ).toBeTruthy();
    expect(container.querySelector(".message-list")?.getAttribute("aria-live")).toBeNull();
    await waitFor(() => {
      expect(
        screen
          .getByText(/Tu exposición a NVDA es 25.5%/)
          .closest(".answer")
          ?.getAttribute("aria-live"),
      ).toBe("polite");
    });
    const behaviors = scrollSpy.mock.calls.map(
      ([options]) => (options as ScrollIntoViewOptions | undefined)?.behavior,
    );
    expect(behaviors).toContain("auto");
    expect(behaviors.at(-1)).toBe("smooth");
  });

  it("abre Portafolio y reemplaza el chat", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).startsWith("/api/portfolio/")) {
        return jsonResponse(portfolioPayload);
      }
      throw new Error(`Llamada inesperada: ${String(input)}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    const portfolioTab = screen.getByRole("tab", { name: "Portafolio" });
    expect((portfolioTab as HTMLButtonElement).disabled).toBe(false);
    fireEvent.click(portfolioTab);

    expect(await screen.findByText("Composición del ETF")).toBeTruthy();
    expect(
      screen.getByRole("heading", { name: "María López" }),
    ).toBeTruthy();
    expect(
      screen.getByTestId("holding-VOO-NVDA").textContent,
    ).toContain("7.0%");
    expect(screen.queryByLabelText("Mensaje")).toBeNull();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/portfolio/maria-lopez",
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );

    fireEvent.click(screen.getByRole("tab", { name: "Chat" }));
    expect(screen.getByLabelText("Mensaje")).toBeTruthy();
  });
});
