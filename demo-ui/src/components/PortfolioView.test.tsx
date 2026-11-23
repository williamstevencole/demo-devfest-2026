import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ClientUser, PortfolioAnalysis } from "../types";
import { PortfolioView } from "./PortfolioView";

afterEach(cleanup);

const user: ClientUser = {
  id: "maria-lopez",
  name: "María López",
  riskProfile: "MODERATE",
};

const analysis: PortfolioAnalysis = {
  invested_usd: 13000,
  total_value_usd: 15500,
  cash_usd: 2500,
  cost_usd: 11500,
  unrealized_pnl_usd: 1500,
  positions: [
    {
      ticker: "NVDA",
      name: "NVIDIA Corporation",
      type: "STOCK",
      sector: "Technology",
      quantity: 20,
      avgCostUsd: 150,
      priceUsd: 180,
      marketValueUsd: 3600,
      weightPct: 27.7,
      unrealizedPnlUsd: 600,
      priceAsOf: "2026-11-17T00:00:00.000Z",
      etfHoldings: [],
    },
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
      etfHoldings: [
        { componentTicker: "NVDA", weightPct: 7 },
        { componentTicker: "AAPL", weightPct: 6.5 },
        { componentTicker: "MSFT", weightPct: 6 },
        { componentTicker: "AMZN", weightPct: 3.5 },
        { componentTicker: "GOOGL", weightPct: 3 },
        { componentTicker: "META", weightPct: 2.5 },
        { componentTicker: "AVGO", weightPct: 2.5 },
        { componentTicker: "TSLA", weightPct: 2 },
        { componentTicker: "BRK.B", weightPct: 1.6 },
        { componentTicker: "JPM", weightPct: 1.3 },
      ],
    },
    {
      ticker: "AAPL",
      name: "Apple Inc.",
      type: "STOCK",
      sector: "Technology",
      quantity: 5,
      avgCostUsd: 200,
      priceUsd: 230,
      marketValueUsd: 1150,
      weightPct: 8.8,
      unrealizedPnlUsd: 150,
      priceAsOf: "2026-11-17T00:00:00.000Z",
      etfHoldings: [],
    },
  ],
  exposures: [
    {
      ticker: "VOO",
      direct_usd: 8250,
      indirect_usd: 0,
      total_usd: 8250,
      weight_pct: 63.5,
    },
    {
      ticker: "NVDA",
      direct_usd: 3600,
      indirect_usd: 577.5,
      total_usd: 4177.5,
      weight_pct: 32.1,
    },
    {
      ticker: "AAPL",
      direct_usd: 1150,
      indirect_usd: 536.25,
      total_usd: 1686.25,
      weight_pct: 13,
    },
    {
      ticker: "MSFT",
      direct_usd: 0,
      indirect_usd: 495,
      total_usd: 495,
      weight_pct: 3.8,
    },
  ],
  sectors: [
    {
      sector: "Technology",
      direct_usd: 4750,
      indirect_usd: 2805,
      total_usd: 7555,
      weight_pct: 58.1,
    },
    {
      sector: "Financials",
      direct_usd: 0,
      indirect_usd: 1031.25,
      total_usd: 1031.25,
      weight_pct: 7.9,
    },
    {
      sector: "Health Care",
      direct_usd: 0,
      indirect_usd: 866.25,
      total_usd: 866.25,
      weight_pct: 6.7,
    },
  ],
};

describe("PortfolioView", () => {
  it("muestra distribución, exposición y composición de ETFs", () => {
    render(
      <PortfolioView
        user={user}
        analysis={analysis}
        loading={false}
        error={null}
        onRetry={() => undefined}
      />,
    );

    expect(screen.getByText("María López")).toBeTruthy();
    expect(screen.getByText("Valor actual")).toBeTruthy();
    expect(screen.getByText("Poder de compra")).toBeTruthy();
    expect(screen.getByText("Costo")).toBeTruthy();
    expect(screen.getByText("Ganancia no realizada")).toBeTruthy();
    expect(screen.getByText("$11,500.00")).toBeTruthy();
    expect(screen.getByText("+$1,500.00")).toBeTruthy();
    expect(screen.getByText("Distribución")).toBeTruthy();
    expect(screen.getByText("Sectores")).toBeTruthy();
    expect(
      screen.getByTestId("sector-Technology").textContent,
    ).toContain("58.1%");
    expect(screen.queryByText(/no es un sector/i)).toBeNull();
    expect(
      screen.getByTestId("distribution-VOO").textContent,
    ).toContain("$8,250.00");
    expect(
      screen.getByTestId("distribution-VOO").textContent,
    ).toContain("Costo $7,500.00");
    expect(
      screen.getByTestId("distribution-VOO").textContent,
    ).toContain("+$750.00");
    expect(
      screen.getByTestId("distribution-Efectivo").textContent,
    ).toContain("$2,500.00");
    expect(
      screen.getByTestId("exposure-NVDA").textContent,
    ).toContain("32.1%");
    expect(screen.getByTestId("etf-VOO")).toBeTruthy();
    expect(screen.getByTestId("donut-slice-VOO")).toBeTruthy();
    expect(screen.getByTestId("donut-slice-Efectivo")).toBeTruthy();
    expect(screen.getByTestId("etf-segment-VOO-NVDA")).toBeTruthy();
    expect(screen.getByTestId("etf-segment-VOO-Otros")).toBeTruthy();
    expect(
      screen.getByTestId("holding-VOO-NVDA").textContent,
    ).toContain("7.0%");
    expect(
      screen.getByTestId("holding-VOO-NVDA").textContent,
    ).toContain("$577.50");
    expect(
      screen.getByTestId("holding-VOO-NVDA").textContent,
    ).toContain("Costo $525.00");
    expect(
      screen.getByTestId("holding-VOO-NVDA").textContent,
    ).toContain("+$52.50");
    expect(
      screen.getByTestId("holding-VOO-Otros").textContent,
    ).toContain("71.5%");
    expect(
      screen.getByTestId("holding-VOO-Otros").textContent,
    ).toContain("$5,898.75");
    expect(
      screen.getByTestId("holding-VOO-Otros").textContent,
    ).toContain("Costo $5,362.50");
    expect(
      screen.getByTestId("holding-VOO-Otros").textContent,
    ).toContain("+$536.25");
    expect(screen.getByTestId("etf-VOO").textContent).toContain(
      "Costo $7,500.00",
    );
    expect(screen.queryByText(/límite/i)).toBeNull();
  });

  it("muestra carga y error con reintento", () => {
    const onRetry = vi.fn();
    const { rerender } = render(
      <PortfolioView
        user={user}
        analysis={null}
        loading
        error={null}
        onRetry={onRetry}
      />,
    );

    expect(screen.getByText("Cargando portafolio…")).toBeTruthy();

    rerender(
      <PortfolioView
        user={user}
        analysis={null}
        loading={false}
        error="No pude cargar tu portafolio."
        onRetry={onRetry}
      />,
    );

    expect(screen.getByText("No pude cargar tu portafolio.")).toBeTruthy();
    fireEvent.click(screen.getByText("Reintentar"));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
