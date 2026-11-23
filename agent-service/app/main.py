"""FastAPI application factory and container lifecycle."""

from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, Request

from app.agent.graph import build_agent_graph
from app.api.ingest_route import router as ingest_router
from app.api.routes import health as health_handler
from app.api.routes import router
from app.config import Settings, get_settings
from app.ingestion.ingest import build_embedding_function
from app.ingestion.knowledge import KnowledgeTool
from app.ingestion.store import KnowledgeStore
from app.integrations.nest import NestClient
from app.integrations.web import WebSearch
from app.llm import create_chat_model
from app.naive.chat import NaiveChat
from app.services.chat_service import ChatService


@dataclass
class AppContainer:
    """Dependencies shared by the request handlers."""

    settings: Settings
    nest: NestClient
    knowledge: KnowledgeTool | None = None
    web: WebSearch | None = None
    llm: Any = None
    graph: Any = None
    naive: NaiveChat | None = None
    chat: ChatService | None = None


ContainerFactory = Callable[[Settings], AppContainer]


def build_container(settings: Settings) -> AppContainer:
    """Create the production dependency container."""

    timeout = settings.http_timeout_seconds
    store = KnowledgeStore(settings.chroma_dir, build_embedding_function(settings))
    knowledge = KnowledgeTool(store)
    llm = create_chat_model(settings)
    container = AppContainer(
        settings=settings,
        nest=NestClient(settings.nest_base_url, timeout),
        knowledge=knowledge,
        web=WebSearch(settings.tavily_api_key, timeout),
        llm=llm,
    )
    container.graph = build_agent_graph(container)
    container.naive = NaiveChat(knowledge, llm, settings)
    container.chat = ChatService(container.graph, container.naive)
    return container


def create_app(container_factory: ContainerFactory | None = None) -> FastAPI:
    """Build the FastAPI app with an injectable dependency container."""

    factory = container_factory or build_container

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.container = factory(get_settings())
        yield
        close = getattr(app.state.container.nest, "aclose", None)
        if close is not None:
            await close()

    app = FastAPI(title="Broker Agent Service", lifespan=lifespan)
    app.include_router(router)
    app.include_router(ingest_router)

    @app.get("/health", include_in_schema=False)
    async def root_health(request: Request) -> dict[str, Any]:
        """Alias for platforms that probe the root health path."""

        return await health_handler(request)

    return app


app = create_app()
