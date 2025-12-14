"""Models for the Analysis Watchlist Plugin."""

from __future__ import annotations
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .....messages import BaseAgentEvent
from ..._models import MessageType


def get_analysis_component_color(label: str) -> str:
    """Deterministic color assignment based on label hash."""
    colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A", "#98D8C8",
              "#F3A683", "#778BEB", "#E77F67", "#CF6A87", "#786FA6"]
    return colors[hash(label) % len(colors)]


class AnalysisComponent(BaseModel):
    # Individual watchlist criterion for monitoring agent conversations.

    label: str = Field(..., description="Short identifier for this component (e.g., 'committee-membership')")
    description: str = Field(..., description="Full explanation of what this component checks for")
    color: str = Field(..., description="Hex color for UI badge display")

    @field_validator("label")
    @classmethod
    def validate_label(cls, v: str) -> str:
        # Label must not be empty
        if not v or not v.strip():
            raise ValueError("label cannot be empty")
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        # Description must not be empty
        if not v or not v.strip():
            raise ValueError("description cannot be empty")
        return v.strip()


class ComponentScore(BaseModel):
    # Scoring result for one analysis component.

    score: int = Field(..., ge=1, le=10, description="Score on 1-10 scale")
    reasoning: str = Field(default="", description="One sentence explanation (empty if score < threshold)")

    @field_validator("reasoning")
    @classmethod
    def validate_reasoning(cls, v: str) -> str:
        # Allow empty reasoning for low scores (< trigger threshold)
        return v.strip() if v else ""


class AnalysisScores(BaseModel):
    # Complete scoring result for a message across all analysis components.

    scores: dict[str, ComponentScore] = Field(
        ...,
        description="Mapping of component label to its score object"
    )


class AnalysisUpdate(BaseAgentEvent):
    """Event emitted when analysis scoring completes for a message node."""

    source: str = "analysis_watchlist"
    type: Literal[MessageType.ANALYSIS_UPDATE] = MessageType.ANALYSIS_UPDATE
    node_id: str = Field(..., description="Message node ID that was scored")
    scores: dict[str, ComponentScore] = Field(..., description="All component scores for this message")
    triggered_components: list[str] = Field(
        ...,
        description="List of component labels where score >= threshold"
    )
    timestamp: datetime = Field(default_factory=datetime.now)

    @field_validator("node_id")
    @classmethod
    def validate_node_id(cls, v: str) -> str:
        # Node ID must not be empty
        if not v or not v.strip():
            raise ValueError("node_id cannot be empty")
        return v.strip()

    def to_text(self) -> str:
        """Return a text representation of the analysis update."""
        triggered_str = ", ".join(self.triggered_components) if self.triggered_components else "none"
        return f"Analysis for {self.node_id}: triggered=[{triggered_str}], scores={len(self.scores)}"
