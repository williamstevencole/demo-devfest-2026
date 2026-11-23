"""Minimal HTTP client for the Nest broker API."""

from typing import TypeVar

import httpx
from pydantic import BaseModel

from app.domain.models import Portfolio
from app.errors import NestUnavailableError

HEALTH_PATH = "/api/health"
HEALTH_TIMEOUT_SECONDS = 2.0
PORTFOLIO_PATH = "/api/users/{user_id}/portfolio"

ModelT = TypeVar("ModelT", bound=BaseModel)


class NestClient:
    """Read-only client for backend-nest."""

    def __init__(
        self,
        base_url: str,
        timeout: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout, transport=transport)

    async def _get(self, path: str, model: type[ModelT]) -> ModelT | None:
        try:
            response = await self._client.get(path)
        except httpx.HTTPError as exc:
            raise NestUnavailableError(f"Nest request failed: {path}") from exc
        if response.status_code == httpx.codes.NOT_FOUND:
            return None
        if response.status_code >= httpx.codes.BAD_REQUEST:
            raise NestUnavailableError(f"Nest returned {response.status_code} for {path}")
        try:
            return model.model_validate(response.json())
        except ValueError as exc:
            raise NestUnavailableError(f"Invalid payload from {path}") from exc

    async def get_portfolio(self, user_id: str) -> Portfolio | None:
        """Return a portfolio, or None when the user does not exist."""

        return await self._get(PORTFOLIO_PATH.format(user_id=user_id), Portfolio)

    async def health(self) -> bool:
        """Return whether Nest answers its own health endpoint."""

        try:
            response = await self._client.get(HEALTH_PATH, timeout=HEALTH_TIMEOUT_SECONDS)
        except httpx.HTTPError as exc:
            raise NestUnavailableError("Nest health check failed") from exc
        return response.status_code == httpx.codes.OK

    async def aclose(self) -> None:
        """Release the underlying HTTP connection pool."""

        await self._client.aclose()
