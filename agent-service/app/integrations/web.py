"""Live web search through Tavily."""

from datetime import date, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

import httpx

from app.domain.web import WebResult
from app.errors import WebSearchError

TAVILY_URL = "https://api.tavily.com/search"
NEWS_TOPIC = "news"
NEWS_LOOKBACK_DAYS = 30
NEWS_MAX_RESULTS = 5


def _source_from_url(url: str) -> str:
    return urlparse(url).netloc or "Tavily"


def _published_date(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        pass
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        pass
    try:
        return parsedate_to_datetime(text).date().isoformat()
    except TypeError, ValueError:
        return text


def _newest_first(result: WebResult) -> tuple[bool, str]:
    """Sort newest first and leave undated results at the end."""

    return (result.published_at is not None, result.published_at or "")


class WebSearch:
    """Search the live web with Tavily."""

    def __init__(
        self,
        api_key: str,
        timeout: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._timeout = timeout
        self._transport = transport

    async def search(self, query: str, max_results: int = NEWS_MAX_RESULTS) -> list[WebResult]:
        """Return live web results for a query, newest first."""

        if not self._api_key.strip():
            raise WebSearchError("TAVILY_API_KEY is required for web search")
        payload = {
            "query": query,
            "max_results": max_results,
            "topic": NEWS_TOPIC,
            "days": NEWS_LOOKBACK_DAYS,
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, transport=self._transport
            ) as client:
                response = await client.post(TAVILY_URL, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            raise WebSearchError("Tavily request failed") from exc
        if response.status_code >= httpx.codes.BAD_REQUEST:
            raise WebSearchError(f"Tavily returned {response.status_code}")
        try:
            data = response.json()
        except ValueError as exc:
            raise WebSearchError("Tavily returned invalid JSON") from exc
        results: list[WebResult] = []
        for item in data.get("results", []):
            url = item.get("url", "")
            if not url:
                continue
            results.append(
                WebResult(
                    title=item.get("title", ""),
                    url=url,
                    snippet=item.get("content", ""),
                    published_at=_published_date(item.get("published_date")),
                    source=_source_from_url(url),
                )
            )
        results.sort(key=_newest_first, reverse=True)
        return results[:max_results]
