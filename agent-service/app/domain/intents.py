"""Deterministic question-intent signals shared by the naive and agent paths."""

import re
from dataclasses import dataclass

CHINA_KEYWORDS = ("china",)
CHIP_KEYWORDS = ("chip", "semiconductor", *CHINA_KEYWORDS)
RECOMMENDATION_KEYWORDS = (
    "debería",
    "deberia",
    "recomiendas",
    "recomendación",
    "recomendacion",
    "me conviene",
)
WITHDRAWAL_WORD = r"(?:retir\w*|sacar\w*|saca\w*|withdraw\w*)"
WITHDRAWAL_INTENT = re.compile(rf"\b{WITHDRAWAL_WORD}\b", re.IGNORECASE)


@dataclass(frozen=True)
class QuestionIntent:
    """Deterministic signals extracted from a user question."""

    mentions_chips: bool
    requests_recommendation: bool
    asks_withdrawal: bool


def classify_question(query: str) -> QuestionIntent:
    """Classify the deterministic aspects used by retrieval and disclaimers."""

    text = query.lower()
    return QuestionIntent(
        mentions_chips=any(keyword in text for keyword in CHIP_KEYWORDS),
        requests_recommendation=any(keyword in text for keyword in RECOMMENDATION_KEYWORDS),
        asks_withdrawal=WITHDRAWAL_INTENT.search(query) is not None,
    )
