"""Offline RAGAS evaluation for the pure corpus RAG path.

This evaluates NaiveChat only: no graph, no portfolio tools and no web.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from langchain_core.embeddings import Embeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from sentence_transformers import SentenceTransformer

try:
    from ragas.dataset_schema import SingleTurnSample
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper
    from ragas.metrics import (
        AnswerRelevancy,
        ContextPrecision,
        ContextRecall,
        Faithfulness,
    )
except ModuleNotFoundError as exc:  # pragma: no cover - dependency guard
    raise SystemExit(
        "RAGAS no está instalado. Ejecuta: "
        "cd agent-service && .venv/bin/pip install -r requirements-eval.txt"
    ) from exc

from app.config import get_settings
from app.ingestion.ingest import build_embedding_function
from app.ingestion.knowledge import KnowledgeTool
from app.ingestion.store import KnowledgeStore
from app.llm import create_chat_model
from app.naive.chat import NaiveChat

EVAL_DIR = Path(__file__).resolve().parent
QUESTIONS_PATH = EVAL_DIR / "questions.json"
RESULTS_DIR = EVAL_DIR / "results"

METRICS = [
    Faithfulness(),
    AnswerRelevancy(strictness=1),
    ContextPrecision(),
    ContextRecall(),
]
METRIC_NAMES = [metric.name for metric in METRICS]


class LocalSentenceEmbeddings(Embeddings):
    """LangChain embeddings backed by the same local model used by Chroma."""

    def __init__(self, model_name: str) -> None:
        self._model = SentenceTransformer(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(texts, normalize_embeddings=True).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self._model.encode([text], normalize_embeddings=True)[0].tolist()


def _load_questions(limit: int | None, only: str | None = None) -> list[dict[str, str]]:
    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    if only:
        questions = [item for item in questions if item["id"] == only]
    return questions[:limit] if limit else questions


async def _collect_samples(
    chat: NaiveChat, questions: list[dict[str, str]]
) -> tuple[list[SingleTurnSample], list[dict[str, Any]]]:
    samples: list[SingleTurnSample] = []
    rows: list[dict[str, Any]] = []

    for item in questions:
        result = await chat.run(item["question"])
        contexts = [document.text for document in result.documents]
        samples.append(
            SingleTurnSample(
                user_input=item["question"],
                retrieved_contexts=contexts,
                response=result.answer,
                reference=item["reference"],
            )
        )
        rows.append(
            {
                "id": item["id"],
                "question": item["question"],
                "answer": result.answer,
                "contexts": contexts,
            }
        )
        print(f"✓ {item['id']}: {len(contexts)} contextos recuperados")

    return samples, rows


def _configure_metrics(
    judge: LangchainLLMWrapper,
    embeddings: LangchainEmbeddingsWrapper,
) -> None:
    for metric in METRICS:
        metric.llm = judge
        if hasattr(metric, "embeddings"):
            metric.embeddings = embeddings


async def _score_samples(
    samples: list[SingleTurnSample],
    raise_exceptions: bool,
) -> list[dict[str, Any]]:
    scored: list[dict[str, Any]] = []
    for sample in samples:
        row: dict[str, Any] = {"user_input": sample.user_input}
        for metric in METRICS:
            try:
                row[metric.name] = await metric._single_turn_ascore(sample, callbacks=[])
            except Exception as exc:  # pragma: no cover - provider failures
                if raise_exceptions:
                    raise
                print(f"  ! {metric.name}: {type(exc).__name__}: {exc}")
                row[metric.name] = None
        scored.append(row)
    return scored


def _print_scores(scores: list[dict[str, Any]]) -> dict[str, float]:
    print("\n--- RAGAS ---")
    print(f"{'pregunta':42} " + " ".join(f"{name:>18}" for name in METRIC_NAMES))
    for row in scores:
        values = []
        for name in METRIC_NAMES:
            value = row.get(name)
            values.append("n/a" if value is None else f"{value:.3f}")
        print(f"{row['user_input'][:42]:42} " + " ".join(f"{v:>18}" for v in values))

    means: dict[str, float] = {}
    for name in METRIC_NAMES:
        values = [row[name] for row in scores if row.get(name) is not None]
        means[name] = round(sum(values) / len(values), 3) if values else 0.0
    print("\nPromedios:")
    for name, value in means.items():
        print(f"  {name}: {value}")
    return means


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Evalúa solo las primeras N preguntas.",
    )
    parser.add_argument(
        "--only",
        type=str,
        default=None,
        help="Evalúa solo la pregunta con este id (ej. retiro).",
    )
    parser.add_argument(
        "--raise-exceptions",
        action="store_true",
        help="Falla si una métrica no puede calcularse.",
    )
    args = parser.parse_args()

    settings = get_settings()
    store = KnowledgeStore(settings.chroma_dir, build_embedding_function(settings))
    chat = NaiveChat(KnowledgeTool(store), create_chat_model(settings), settings)

    questions = _load_questions(args.limit, args.only)
    samples, rows = asyncio.run(_collect_samples(chat, questions))

    judge_llm = ChatGoogleGenerativeAI(
        model=settings.chat_model,
        google_api_key=settings.google_api_key,
        temperature=0,
    )
    judge = LangchainLLMWrapper(judge_llm)
    embeddings = LangchainEmbeddingsWrapper(LocalSentenceEmbeddings(settings.embedding_model))
    _configure_metrics(judge, embeddings)

    scores = asyncio.run(_score_samples(samples, args.raise_exceptions))
    means = _print_scores(scores)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output = {
        "timestamp": timestamp,
        "model": settings.chat_model,
        "embedding_model": settings.embedding_model,
        "scope": "naive_rag_corpus_only",
        "means": means,
        "questions": rows,
        "scores": scores,
    }
    output_path = RESULTS_DIR / f"ragas-{timestamp}.json"
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"\nResultados guardados en {output_path}")


if __name__ == "__main__":
    main()
