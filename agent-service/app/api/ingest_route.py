"""Ingestion endpoint."""

from fastapi import APIRouter, HTTPException, Request

from app.errors import IngestError
from app.ingestion.ingest import ingest_settings

router = APIRouter(prefix="/api")


@router.post("/ingest")
def ingest(request: Request) -> dict[str, int]:
    """Reindex the knowledge corpus and return the chunk count."""

    container = request.app.state.container
    try:
        indexed = ingest_settings(container.settings)
    except IngestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"indexed_chunks": indexed}
