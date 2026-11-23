import { afterEach, describe, expect, it, vi } from "vitest";

import { getPortfolio, mapChatResponse } from "./api";

function jsonResponse(payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("mapChatResponse", () => {
  it("mapea insufficient_data y missing_data del backend", () => {
    const response = mapChatResponse({
      answer: "No tengo el dato.",
      mode: "agent",
      trace: { steps: [] },
      insufficient_data: true,
      missing_data: ["la comisión exacta", "el plazo"],
    });

    expect(response.insufficientData).toBe(true);
    expect(response.missingData).toEqual(["la comisión exacta", "el plazo"]);
  });

  it("usa valores seguros cuando el backend no envía las banderas", () => {
    const response = mapChatResponse({
      answer: "Hola",
      mode: "agent",
      trace: { steps: [] },
    });

    expect(response.insufficientData).toBe(false);
    expect(response.missingData).toEqual([]);
  });
});

describe("getPortfolio", () => {
  it("pide el portafolio del usuario identificado", async () => {
    const payload = {
      invested_usd: 18200,
      total_value_usd: 20700,
      cash_usd: 2500,
      cost_usd: 16300,
      unrealized_pnl_usd: 1900,
      positions: [],
      exposures: [],
      sectors: [],
    };
    const fetchMock = vi.fn(async () => jsonResponse(payload));
    vi.stubGlobal("fetch", fetchMock);

    const analysis = await getPortfolio("maria-lopez");

    expect(fetchMock).toHaveBeenCalledWith("/api/portfolio/maria-lopez", {
      signal: undefined,
    });
    expect(analysis.invested_usd).toBe(18200);
  });
});
