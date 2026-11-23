"""Tool definitions exposed to the autonomous agent."""

import inspect
import logging
from collections.abc import Callable
from typing import Annotated, Any

from langchain_core.tools import BaseTool, tool
from langgraph.prebuilt import InjectedState

from app.agent.state import AgentState
from app.agent.tools import payloads as data

logger = logging.getLogger(__name__)


async def _safe(tool_name: str, operation: Callable[[], Any]) -> str:
    """Run a tool, returning a structured error instead of crashing the graph."""

    try:
        result = operation()
        if inspect.isawaitable(result):
            result = await result
        return result
    except Exception:
        logger.exception("La herramienta %s falló", tool_name)
        return data.as_tool_content(
            {
                "error": f"La herramienta {tool_name} falló. Intenta de nuevo.",
                "tool": tool_name,
            }
        )


def build_tools(container: Any) -> list[BaseTool]:
    """Create the agent tools bound to the service dependencies."""

    @tool
    async def search_knowledge(query: str) -> str:
        """Busca en el corpus del broker: glosario, comisiones, políticas y
        procedimientos. Úsala para preguntas conceptuales o de funcionamiento,
        no para datos personales."""

        return await _safe(
            "search_knowledge",
            lambda: data.as_tool_content(
                data.knowledge_data(container.knowledge, query, container.settings.retrieval_top_k)
            ),
        )

    @tool
    async def search_news(query: str) -> str:
        """Busca noticias de los últimos 30 días, ordenadas de la más reciente a
        la más antigua. Devuelve `latest` (el estado más reciente) y una
        `timeline`. Úsala para eventos actuales, renuncias, regresos o cualquier
        noticia que pueda afectar al mercado. Puedes llamarla hasta 3 veces por
        turno, cada vez con una consulta distinta: una para el hecho y otra para
        verificar el estado actual (¿sigue vigente?, ¿volvió?, ¿último estado?)."""

        async def run() -> str:
            return data.as_tool_content(await data.news_data(container.web, query))

        return await _safe("search_news", run)

    @tool
    async def analyze_portfolio(
        state: Annotated[AgentState, InjectedState],
    ) -> str:
        """Devuelve el análisis completo del portafolio del usuario de la
        sesión: posiciones, exposición directa e indirecta, sectores y
        concentración. Todos los campos `weight_pct` son porcentaje del dinero
        invertido, no del total con efectivo. Úsala para "analiza mi
        portafolio", "cómo está mi cartera" y también para recomendaciones
        generales de inversión, concentración y diversificación."""

        async def run() -> str:
            return data.as_tool_content(
                await data.analyze_portfolio_data(container.nest, state.get("user_id", ""))
            )

        return await _safe("analyze_portfolio", run)

    @tool
    async def estimate_withdrawal(
        amount_usd: float,
        state: Annotated[AgentState, InjectedState],
        convert_to_local: bool = False,
    ) -> str:
        """Calcula un retiro. Usa convert_to_local=true si el dinero se convierte
        a otra moneda (aplica el spread de 0.75%); false si el retiro es en
        dólares. Si el usuario no dice la moneda, asume USD y menciona también
        el costo de convertir que devuelve la herramienta. Devuelve efectivo
        usado, venta necesaria, comisiones, spread, neto y plazos. Úsala solo
        cuando pregunten por retirar dinero o por el efectivo disponible; no la
        uses para recomendaciones generales de inversión."""

        async def run() -> str:
            return data.as_tool_content(
                await data.withdrawal_data(
                    container.nest,
                    state.get("user_id", ""),
                    amount_usd,
                    convert_to_local=convert_to_local,
                )
            )

        return await _safe("estimate_withdrawal", run)

    @tool
    async def simulate_sale(
        ticker: str,
        state: Annotated[AgentState, InjectedState],
        quantity: float | None = None,
    ) -> str:
        """Simula vender un ticker, completo o una cantidad, y devuelve el
        portafolio resultante y el cambio de exposición directa e indirecta.
        Úsala solo para "¿y si vendo X?" o para decisiones sobre vender un
        ticker concreto. No la uses para recomendaciones generales de inversión
        ni para "¿en qué invierto?"."""

        async def run() -> str:
            return data.as_tool_content(
                await data.sale_data(
                    container.nest,
                    state.get("user_id", ""),
                    ticker,
                    quantity=quantity,
                )
            )

        return await _safe("simulate_sale", run)

    @tool
    async def scenario_impact(
        target: str,
        state: Annotated[AgentState, InjectedState],
        moves_pct: list[float] | None = None,
    ) -> str:
        """Devuelve la exposición directa+indirecta a un ticker o sector y el
        impacto en USD de caídas porcentuales. `weight_invested_pct` es
        porcentaje del dinero invertido, no del total con efectivo. Úsala
        siempre que pregunte "¿me afecta...?" o pida el impacto de una noticia
        en su dinero."""

        async def run() -> str:
            return data.as_tool_content(
                await data.scenario_data(
                    container.nest,
                    state.get("user_id", ""),
                    target,
                    moves_pct=moves_pct,
                )
            )

        return await _safe("scenario_impact", run)

    return [
        search_knowledge,
        search_news,
        analyze_portfolio,
        estimate_withdrawal,
        simulate_sale,
        scenario_impact,
    ]
