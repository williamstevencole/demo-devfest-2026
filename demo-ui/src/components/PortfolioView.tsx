import type {
  ClientUser,
  Exposure,
  PortfolioAnalysis,
  PortfolioPosition,
  SectorExposure,
} from "../types";
import { money, signedMoney } from "../lib/format";

const CHART_COLORS = [
  "#d8b45f",
  "#a8a08a",
  "#7f8f84",
  "#c08b72",
  "#8d8f9c",
  "#b4a38c",
  "#6f7d84",
  "#a07d8c",
];
const CASH_COLOR = "#93b79a";
const ETF_VISIBLE_HOLDINGS = 6;

function visibleEtfHoldings(position: PortfolioPosition) {
  return [...position.etfHoldings]
    .sort((a, b) => b.weightPct - a.weightPct)
    .slice(0, ETF_VISIBLE_HOLDINGS);
}

const RISK_LABELS: Record<string, string> = {
  CONSERVATIVE: "Perfil conservador",
  MODERATE: "Perfil moderado",
  AGGRESSIVE: "Perfil agresivo",
};

function sharePct(value: number, total: number): number {
  return total > 0 ? (value / total) * 100 : 0;
}

function formatPct(value: number): string {
  return `${value.toFixed(1)}%`;
}

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

interface DonutSlice {
  label: string;
  name: string;
  value: number;
  percent: number;
  color: string;
  cost?: number;
  gain?: number;
}

function DonutChart({
  slices,
  total,
}: {
  slices: DonutSlice[];
  total: number;
}) {
  const radius = 46;
  const circumference = 2 * Math.PI * radius;
  const gap = 2;
  let offset = 0;

  return (
    <div className="portfolio-donut-wrap">
      <div className="portfolio-donut-shell">
        <svg
          className="portfolio-donut"
          viewBox="0 0 120 120"
          role="img"
          aria-label="Distribución del portafolio"
        >
          <circle
            className="portfolio-donut-track"
            cx="60"
            cy="60"
            r={radius}
            fill="none"
            strokeWidth="11"
          />
          {slices.map((slice) => {
            const length = (slice.percent / 100) * circumference;
            const visible = Math.max(length - gap, 0);
            const dash = `${visible} ${circumference - visible}`;
            const circle = (
              <circle
                key={slice.label}
                data-testid={`donut-slice-${slice.label}`}
                cx="60"
                cy="60"
                r={radius}
                fill="none"
                stroke={slice.color}
                strokeWidth="11"
                strokeDasharray={dash}
                strokeDashoffset={-offset}
                strokeLinecap="butt"
                transform="rotate(-90 60 60)"
              />
            );
            offset += length;
            return circle;
          })}
          <text x="60" y="55" textAnchor="middle" className="portfolio-donut-label">
            Total
          </text>
          <text x="60" y="70" textAnchor="middle" className="portfolio-donut-value">
            {money.format(total)}
          </text>
        </svg>
      </div>
      <ul className="portfolio-legend">
        {slices.map((slice) => (
          <li
            key={slice.label}
            className="portfolio-legend-row"
            data-testid={`distribution-${slice.label}`}
          >
            <span
              className="portfolio-legend-dot"
              style={{ background: slice.color }}
            />
            <span className="portfolio-legend-copy">
              <span className="portfolio-legend-label">{slice.label}</span>
              <span className="portfolio-legend-name">{slice.name}</span>
              {slice.cost !== undefined && (
                <span className="portfolio-legend-meta">
                  Costo {money.format(slice.cost)} ·{" "}
                  <em
                    className={
                      (slice.gain ?? 0) >= 0 ? "is-gain" : "is-loss"
                    }
                  >
                    {signedMoney(slice.gain ?? 0)}
                  </em>
                </span>
              )}
            </span>
            <span className="portfolio-legend-numbers">
              <strong>{money.format(slice.value)}</strong>
              <em>{formatPct(slice.percent)}</em>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function distributionSlices(analysis: PortfolioAnalysis): DonutSlice[] {
  const positions: DonutSlice[] = [...analysis.positions]
    .sort((a, b) => b.marketValueUsd - a.marketValueUsd)
    .map((position, index) => {
      const cost = position.quantity * position.avgCostUsd;
      return {
        label: position.ticker,
        name: position.name,
        value: position.marketValueUsd,
        percent: sharePct(position.marketValueUsd, analysis.total_value_usd),
        color: CHART_COLORS[index % CHART_COLORS.length],
        cost,
        gain: position.marketValueUsd - cost,
      };
    });

  positions.push({
    label: "Efectivo",
    name: "Efectivo disponible",
    value: analysis.cash_usd,
    percent: sharePct(analysis.cash_usd, analysis.total_value_usd),
    color: CASH_COLOR,
  });
  return positions;
}

function ExposureRow({ exposure }: { exposure: Exposure }) {
  return (
    <li className="portfolio-exposure" data-testid={`exposure-${exposure.ticker}`}>
      <div className="portfolio-exposure-head">
        <span className="portfolio-ticker-pill">{exposure.ticker}</span>
        <span className="portfolio-exposure-value">
          {money.format(exposure.total_usd)} <em>{formatPct(exposure.weight_pct)}</em>
        </span>
      </div>
      <div className="portfolio-exposure-bar" aria-hidden="true">
        <span
          style={{
            width: `${Math.min(Math.max(exposure.weight_pct, 0), 100)}%`,
          }}
        />
      </div>
      <div className="portfolio-exposure-split">
        {exposure.direct_usd > 0 && (
          <span>
            <i className="portfolio-split-dot is-direct" /> Directo{" "}
            {money.format(exposure.direct_usd)}
          </span>
        )}
        {exposure.indirect_usd > 0 && (
          <span>
            <i className="portfolio-split-dot is-indirect" /> Indirecto{" "}
            {money.format(exposure.indirect_usd)}
          </span>
        )}
      </div>
    </li>
  );
}

function SectorRow({ sector }: { sector: SectorExposure }) {
  return (
    <li className="portfolio-exposure" data-testid={`sector-${sector.sector}`}>
      <div className="portfolio-exposure-head">
        <span className="portfolio-sector-name">{sector.sector}</span>
        <span className="portfolio-exposure-value">
          {money.format(sector.total_usd)} <em>{formatPct(sector.weight_pct)}</em>
        </span>
      </div>
      <div className="portfolio-exposure-bar is-sector" aria-hidden="true">
        <span
          style={{
            width: `${Math.min(Math.max(sector.weight_pct, 0), 100)}%`,
          }}
        />
      </div>
      <div className="portfolio-exposure-split">
        {sector.direct_usd > 0 && (
          <span>
            <i className="portfolio-split-dot is-direct" /> Directo{" "}
            {money.format(sector.direct_usd)}
          </span>
        )}
        {sector.indirect_usd > 0 && (
          <span>
            <i className="portfolio-split-dot is-indirect" /> Indirecto{" "}
            {money.format(sector.indirect_usd)}
          </span>
        )}
      </div>
    </li>
  );
}

function EtfCompositionBar({ position }: { position: PortfolioPosition }) {
  const holdings = visibleEtfHoldings(position);
  const known = holdings.reduce((sum, holding) => sum + holding.weightPct, 0);
  const other = Math.max(0, 100 - known);
  const segments = [
    ...holdings.map((holding, index) => ({
      label: holding.componentTicker,
      percent: holding.weightPct,
      color: CHART_COLORS[index % CHART_COLORS.length],
    })),
    ...(other > 0
      ? [{ label: "Otros", percent: other, color: "var(--surface-3)" }]
      : []),
  ];

  return (
    <div
      className="portfolio-etf-bar"
      role="img"
      aria-label={`Composición de ${position.ticker}`}
    >
      {segments.map((segment) => (
        <span
          key={segment.label}
          data-testid={`etf-segment-${position.ticker}-${segment.label}`}
          style={{ width: `${segment.percent}%`, background: segment.color }}
          title={`${segment.label}: ${formatPct(segment.percent)}`}
        />
      ))}
    </div>
  );
}

function EtfCard({ position }: { position: PortfolioPosition }) {
  const holdings = visibleEtfHoldings(position);
  const maxWeight = Math.max(...holdings.map((holding) => holding.weightPct), 1);
  const known = holdings.reduce((sum, holding) => sum + holding.weightPct, 0);
  const other = Math.max(0, 100 - known);
  const otherValue = (position.marketValueUsd * other) / 100;
  const positionCost = position.quantity * position.avgCostUsd;
  const positionGain = position.marketValueUsd - positionCost;
  const otherCost = (positionCost * other) / 100;

  return (
    <article className="portfolio-etf" data-testid={`etf-${position.ticker}`}>
      <header className="portfolio-etf-head">
        <div className="portfolio-etf-brand">
          <span className="portfolio-etf-symbol">{position.ticker}</span>
          <span className="portfolio-etf-name">{position.name}</span>
          <span className="portfolio-etf-meta">
            Costo {money.format(positionCost)} ·{" "}
            <em className={positionGain >= 0 ? "is-gain" : "is-loss"}>
              {signedMoney(positionGain)}
            </em>
          </span>
        </div>
        <span className="portfolio-etf-value">
          {money.format(position.marketValueUsd)}
        </span>
      </header>

      <EtfCompositionBar position={position} />

      {holdings.length > 0 ? (
        <ul className="portfolio-holdings">
          {holdings.map((holding, index) => {
            const contribution =
              (position.marketValueUsd * holding.weightPct) / 100;
            const holdingCost = (positionCost * holding.weightPct) / 100;
            const holdingGain = contribution - holdingCost;
            return (
              <li
                key={holding.componentTicker}
                data-testid={`holding-${position.ticker}-${holding.componentTicker}`}
              >
                <span className="portfolio-holding-rank">{index + 1}</span>
                <span className="portfolio-holding-ticker">
                  <i
                    className="portfolio-holding-dot"
                    style={{
                      background:
                        CHART_COLORS[index % CHART_COLORS.length],
                    }}
                  />
                  {holding.componentTicker}
                </span>
                <span className="portfolio-holding-bar" aria-hidden="true">
                  <span
                    style={{
                      width: `${(holding.weightPct / maxWeight) * 100}%`,
                    }}
                  />
                </span>
                <span className="portfolio-holding-weight">
                  {formatPct(holding.weightPct)}
                </span>
                <span className="portfolio-holding-value">
                  {money.format(contribution)}
                </span>
                <span className="portfolio-holding-cost">
                  Costo {money.format(holdingCost)} ·{" "}
                  <em className={holdingGain >= 0 ? "is-gain" : "is-loss"}>
                    {signedMoney(holdingGain)}
                  </em>
                </span>
              </li>
            );
          })}
          {other > 0 && (
            <li
              className="portfolio-holding-other"
              data-testid={`holding-${position.ticker}-Otros`}
            >
              <span className="portfolio-holding-rank">—</span>
              <span className="portfolio-holding-ticker">
                <i className="portfolio-holding-dot is-other" />
                Otros
              </span>
              <span
                className="portfolio-holding-bar is-muted"
                aria-hidden="true"
              >
                <span style={{ width: `${other}%` }} />
              </span>
              <span className="portfolio-holding-weight">
                {formatPct(other)}
              </span>
              <span className="portfolio-holding-value">
                {money.format(otherValue)}
              </span>
              <span className="portfolio-holding-cost">
                Costo {money.format(otherCost)} ·{" "}
                <em
                  className={
                    otherValue - otherCost >= 0 ? "is-gain" : "is-loss"
                  }
                >
                  {signedMoney(otherValue - otherCost)}
                </em>
              </span>
            </li>
          )}
        </ul>
      ) : (
        <p className="portfolio-empty">Sin composición registrada.</p>
      )}
    </article>
  );
}

interface PortfolioViewProps {
  user: ClientUser;
  analysis: PortfolioAnalysis | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}

export function PortfolioView({
  user,
  analysis,
  loading,
  error,
  onRetry,
}: PortfolioViewProps) {
  const etfTickers = new Set(
    (analysis?.positions ?? [])
      .filter((position) => position.type === "ETF")
      .map((position) => position.ticker),
  );
  const companyExposures =
    analysis?.exposures.filter(
      (exposure) => !etfTickers.has(exposure.ticker),
    ) ?? [];

  return (
    <section className="portfolio-view" aria-label="Portafolio">
      <header className="portfolio-hero">
        <div className="portfolio-avatar" aria-hidden="true">
          {initials(user.name)}
        </div>
        <div className="portfolio-identity">
          <span className="portfolio-eyebrow">Portafolio</span>
          <h2>{user.name}</h2>
          <span className="portfolio-risk">
            {RISK_LABELS[user.riskProfile] ?? user.riskProfile}
          </span>
        </div>
        <div className="portfolio-hero-total">
          <span>Valor total</span>
          <strong>
            {analysis ? money.format(analysis.total_value_usd) : "—"}
          </strong>
        </div>
      </header>

      {loading && <p className="portfolio-state">Cargando portafolio…</p>}

      {error && !loading && (
        <div className="portfolio-state is-error">
          <p>{error}</p>
          <button type="button" onClick={onRetry}>
            Reintentar
          </button>
        </div>
      )}

      {!loading && !error && !analysis && (
        <p className="portfolio-state">No hay datos del portafolio.</p>
      )}

      {!loading && !error && analysis && (
        <>
          <div className="portfolio-metrics">
            <article className="portfolio-metric is-cost">
              <span>Costo</span>
              <strong>{money.format(analysis.cost_usd ?? 0)}</strong>
              <small>Lo que aportaste</small>
            </article>
            <article className="portfolio-metric is-invested">
              <span>Valor actual</span>
              <strong>{money.format(analysis.invested_usd)}</strong>
              <small>{analysis.positions.length} posiciones</small>
            </article>
            <article
              className={`portfolio-metric ${
                (analysis.unrealized_pnl_usd ?? 0) >= 0 ? "is-gain" : "is-loss"
              }`}
            >
              <span>Ganancia no realizada</span>
              <strong>
                {signedMoney(analysis.unrealized_pnl_usd ?? 0)}
              </strong>
              <small>Aún no vendida</small>
            </article>
            <article className="portfolio-metric is-cash">
              <span>Poder de compra</span>
              <strong>{money.format(analysis.cash_usd)}</strong>
              <small>Efectivo disponible</small>
            </article>
          </div>

          <section className="portfolio-card portfolio-card-distribution">
            <header className="portfolio-card-head">
              <div className="portfolio-card-title">
                <h3>Distribución</h3>
                <p>¿Dónde está tu dinero?</p>
              </div>
              <span className="portfolio-card-hint">% del total</span>
            </header>
            <div className="portfolio-distribution">
              <DonutChart
                slices={distributionSlices(analysis)}
                total={analysis.total_value_usd}
              />
            </div>
          </section>

          <div className="portfolio-columns">
            <section className="portfolio-card portfolio-card-exposure">
              <header className="portfolio-card-head">
                <div className="portfolio-card-title">
                  <h3>Exposición por empresa</h3>
                  <p>Directo más lo que llega vía ETFs</p>
                </div>
                <span className="portfolio-card-hint">% del invertido</span>
              </header>
              <ul className="portfolio-exposure-list">
                {companyExposures.map((exposure) => (
                  <ExposureRow key={exposure.ticker} exposure={exposure} />
                ))}
              </ul>
            </section>

            <section className="portfolio-card portfolio-card-exposure">
              <header className="portfolio-card-head">
                <div className="portfolio-card-title">
                  <h3>Sectores</h3>
                  <p>Expuesto a través de los ETFs incluidos</p>
                </div>
                <span className="portfolio-card-hint">% del invertido</span>
              </header>
              <ul className="portfolio-exposure-list">
                {analysis.sectors.map((sector) => (
                  <SectorRow key={sector.sector} sector={sector} />
                ))}
              </ul>
              {analysis.sectors.some(
                (sector) => sector.sector === "Sin detalle",
              ) && (
                <p className="portfolio-note">
                  “Sin detalle” es la parte de los ETFs cuyos holdings no están
                  desglosados en el corpus; no es un sector.
                </p>
              )}
            </section>
          </div>

          <section className="portfolio-card portfolio-card-etfs">
            <header className="portfolio-card-head">
              <div className="portfolio-card-title">
                <h3>Composición del ETF</h3>
                <p>Peso de cada empresa dentro del ETF</p>
              </div>
              <span className="portfolio-card-hint">Principales posiciones</span>
            </header>
            <div className="portfolio-etfs">
              {analysis.positions
                .filter(
                  (position) =>
                    position.type === "ETF" && position.etfHoldings.length > 0,
                )
                .map((position) => (
                  <EtfCard key={position.ticker} position={position} />
                ))}
            </div>
          </section>
        </>
      )}
    </section>
  );
}
