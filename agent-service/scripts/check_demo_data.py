#!/usr/bin/env python3
"""Verifica las cifras sembradas de la demo consultando backend-nest.

Uso:
    python agent-service/scripts/check_demo_data.py

Lee la URL de Nest desde NEST_BASE_URL (default http://localhost:3001).
Termina con código 0 si todo coincide y 1 si algo falla o Nest no responde.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

DEFAULT_BASE_URL = "http://localhost:3001"
TIMEOUT_SECONDS = 5.0


class NestUnavailableError(RuntimeError):
    """Nest no respondió a la petición."""


def base_url() -> str:
    return os.environ.get("NEST_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def fetch_json(path: str) -> Any:
    url = f"{base_url()}{path}"
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"GET {url} respondió HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise NestUnavailableError(
            f"No se pudo conectar con backend-nest en {base_url()} ({exc}). "
            "¿Está levantado con `npm run start:dev`?"
        ) from exc


def check_equal(label: str, expected: Any, received: Any) -> bool:
    if received == expected:
        print(f"[OK]   {label}: {received}")
        return True
    print(f"[FAIL] {label}: esperado {expected!r}, recibido {received!r}")
    return False


def check_portfolio(user_id: str, invested: float, total: float) -> bool:
    portfolio = fetch_json(f"/api/users/{user_id}/portfolio")
    ok = check_equal(
        f"{user_id} investedUsd",
        invested,
        portfolio.get("investedUsd"),
    )
    ok &= check_equal(
        f"{user_id} totalUsd",
        total,
        portfolio.get("totalUsd"),
    )
    return ok


def check_holdings(ticker: str, expected_count: int) -> bool:
    instrument = fetch_json(f"/api/instruments/{ticker}")
    holdings = instrument.get("holdings")
    if holdings is None:
        print(f"[FAIL] {ticker} holdings: la respuesta no incluye 'holdings'")
        return False
    return check_equal(f"{ticker} holdings", expected_count, len(holdings))


def main() -> int:
    print(f"Verificando datos de demo en {base_url()} ...")
    try:
        checks = [
            check_portfolio("maria-lopez", 13000, 15500),
            check_holdings("VOO", 10),
            check_holdings("BND", 0),
        ]
    except NestUnavailableError as exc:
        print(f"[FAIL] {exc}")
        return 1
    except RuntimeError as exc:
        print(f"[FAIL] {exc}")
        return 1

    if all(checks):
        print("Todo correcto: los datos de demo coinciden.")
        return 0
    print("Hay comprobaciones fallidas.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
