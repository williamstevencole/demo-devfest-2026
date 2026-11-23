import json

import httpx
import pytest

from app.errors import WebSearchError
from app.integrations.web import TAVILY_URL, WebSearch


async def test_parsea_resultados_y_descarta_sin_url() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == TAVILY_URL
        assert request.headers["Authorization"] == "Bearer key"
        payload = json.loads(request.content)
        assert payload["topic"] == "news"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "title": "Nota",
                        "url": "https://www.reuters.com/nota",
                        "content": "detalle",
                        "published_date": "Sun, 17 Nov 2026 10:00:00 GMT",
                    },
                    {"title": "sin url", "url": "", "content": "x"},
                ]
            },
        )

    search = WebSearch("key", 1.0, transport=httpx.MockTransport(handler))

    results = await search.search("chips")

    assert len(results) == 1
    assert results[0].source == "www.reuters.com"
    assert results[0].published_at == "2026-11-17"
    assert results[0].snippet == "detalle"


async def test_sin_api_key_falla_tipado() -> None:
    with pytest.raises(WebSearchError):
        await WebSearch("", 1.0).search("chips")


async def test_5xx_falla_tipado() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    with pytest.raises(WebSearchError):
        await WebSearch("key", 1.0, transport=httpx.MockTransport(handler)).search("chips")


async def test_json_invalido_falla_tipado() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not json")

    with pytest.raises(WebSearchError):
        await WebSearch("key", 1.0, transport=httpx.MockTransport(handler)).search("chips")


async def test_respeta_max_results() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "results": [
                    {"title": "a", "url": "https://a.example", "content": "a"},
                    {"title": "b", "url": "https://b.example", "content": "b"},
                    {"title": "c", "url": "https://c.example", "content": "c"},
                ]
            },
        )

    results = await WebSearch("key", 1.0, transport=httpx.MockTransport(handler)).search(
        "chips", max_results=2
    )

    assert len(results) == 2


def _news_handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "results": [
                {
                    "title": "Nota vieja",
                    "url": "https://a.example/vieja",
                    "content": "renuncia",
                    "published_date": "2026-11-12",
                },
                {
                    "title": "Nota nueva",
                    "url": "https://b.example/nueva",
                    "content": "regresa",
                    "published_date": "2026-11-17T09:30:00Z",
                },
                {
                    "title": "Nota media",
                    "url": "https://c.example/media",
                    "content": "contexto",
                    "published_date": "Tue, 14 Nov 2026 08:00:00 GMT",
                },
            ]
        },
    )


async def test_ordena_noticias_por_fecha_descendente() -> None:
    search = WebSearch("key", 1.0, transport=httpx.MockTransport(_news_handler))

    results = await search.search("NVIDIA")

    assert [result.title for result in results] == [
        "Nota nueva",
        "Nota media",
        "Nota vieja",
    ]


async def test_parsea_fechas_iso() -> None:
    search = WebSearch("key", 1.0, transport=httpx.MockTransport(_news_handler))

    results = await search.search("NVIDIA")

    assert {result.published_at for result in results} == {
        "2026-11-17",
        "2026-11-14",
        "2026-11-12",
    }


async def test_default_pide_cinco_resultados() -> None:
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        return httpx.Response(200, json={"results": []})

    await WebSearch("key", 1.0, transport=httpx.MockTransport(handler)).search("NVIDIA")

    assert seen["max_results"] == 5
    assert seen["topic"] == "news"
