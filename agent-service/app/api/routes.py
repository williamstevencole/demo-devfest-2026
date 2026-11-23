"""API routes for the agent service."""

import asyncio
import logging
from contextlib import suppress
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.api.schemas import ChatRequest, ChatResponse
from app.api.sse import ChatEvent, format_sse
from app.domain.analysis import analyze_portfolio
from app.domain.response import analysis_payload
from app.errors import NestUnavailableError
from app.services.chat_service import ChatService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

NEST_DOWN_MESSAGE = "No pudimos consultar el portafolio. Verifica que backend-nest esté disponible."
INTERNAL_MESSAGE = "Error interno del agente."


@router.get("/health")
async def health(request: Request) -> dict[str, Any]:
    """Report agent readiness and Nest availability."""

    container = request.app.state.container
    try:
        nest_ready = await container.nest.health()
    except NestUnavailableError:
        nest_ready = False
    return {
        "status": "ready" if nest_ready else "degraded",
        "agent": True,
        "nest": nest_ready,
    }


@router.get("/portfolio/{user_id}")
async def portfolio(user_id: str, request: Request) -> dict[str, Any]:
    """Return the deterministic portfolio analysis for the identified user."""

    container = request.app.state.container
    try:
        data = await container.nest.get_portfolio(user_id)
    except NestUnavailableError as exc:
        raise HTTPException(status_code=503, detail=NEST_DOWN_MESSAGE) from exc
    if data is None:
        raise HTTPException(status_code=404, detail="No encontramos ese portafolio.")
    return analysis_payload(analyze_portfolio(data))


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request) -> ChatResponse:
    """Answer a chat request and return the full trace."""

    service: ChatService = request.app.state.container.chat
    try:
        return await service.ask(
            body.user_id,
            body.query,
            body.mode,
            [message.model_dump() for message in body.history],
        )
    except NestUnavailableError as exc:
        logger.warning("Nest no está disponible: %s", exc)
        raise HTTPException(status_code=503, detail=NEST_DOWN_MESSAGE) from exc
    except Exception as exc:
        logger.exception("Error interno en /api/chat")
        raise HTTPException(status_code=500, detail=INTERNAL_MESSAGE) from exc


async def _stream_events(service: ChatService, body: ChatRequest):
    queue: asyncio.Queue[str | None] = asyncio.Queue()

    async def produce() -> None:
        try:
            async for event in service.stream(
                body.user_id,
                body.query,
                body.mode,
                [message.model_dump() for message in body.history],
            ):
                await queue.put(format_sse(event))
        except NestUnavailableError:
            logger.warning("Nest no está disponible en /api/chat/stream")
            await queue.put(format_sse(ChatEvent("error", {"message": NEST_DOWN_MESSAGE})))
        except Exception:
            logger.exception("Error interno en /api/chat/stream")
            await queue.put(format_sse(ChatEvent("error", {"message": INTERNAL_MESSAGE})))
        finally:
            await queue.put(None)

    task = asyncio.create_task(produce())
    try:
        # Flush headers immediately and keep the connection warm while the model
        # works. Some proxies drop an SSE request that stays silent too long.
        yield ": connected\n\n"
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=15)
            except TimeoutError:
                yield ": keep-alive\n\n"
                continue
            if item is None:
                break
            yield item
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


@router.post("/chat/stream")
async def chat_stream(body: ChatRequest, request: Request) -> StreamingResponse:
    """Stream chat steps and tokens as server-sent events."""

    service: ChatService = request.app.state.container.chat
    return StreamingResponse(_stream_events(service, body), media_type="text/event-stream")
