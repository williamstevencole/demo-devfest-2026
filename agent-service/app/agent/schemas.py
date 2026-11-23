"""Structured verdict produced by the sufficiency checker."""

from typing import Literal

from pydantic import BaseModel, Field

ConflictType = Literal[
    "none",
    "outdated",
    "complementary",
    "opinion",
    "misinformation",
    "unresolved",
]


class SufficiencyCheck(BaseModel):
    """Whether the tool results are enough to answer the current question."""

    sufficient: bool = Field(
        description="True only when the available results support a safe answer."
    )
    stale_evidence: bool = Field(
        default=False,
        description=(
            "True when a newer source could change the answer or the current "
            "state of an event was not verified."
        ),
    )
    conflict_type: ConflictType = Field(
        default="none",
        description=(
            "How conflicting sources were handled. Use 'unresolved' when it is "
            "impossible to tell which source is the current one."
        ),
    )
    missing: list[str] = Field(
        default_factory=list,
        description="Concrete data still missing when sufficient is false.",
    )
    next_query: str | None = Field(
        default=None,
        description="Concrete query the agent should try next, if any.",
    )
    next_tool: str | None = Field(
        default=None,
        description="Tool name that should provide the missing data, if known.",
    )
