"""Analysis Watchlist Plugin for hallucination detection and user feedback trigger.

This plugin scores agent messages against trusted facts and triggers user feedback
when scores exceed the threshold, providing quality assurance for research outputs.
"""
from ._models import (
    AnalysisComponent,
    ComponentScore,
    AnalysisScores,
    AnalysisUpdate,
    get_analysis_component_color,
)
from ._service import AnalysisService
from ._prompts import (
    COMPONENT_PARSING_PROMPT,
    MESSAGE_SCORING_PROMPT,
)
from ._plugin import AnalysisWatchlistPlugin

__all__ = [
    "AnalysisComponent",
    "ComponentScore",
    "AnalysisScores",
    "AnalysisUpdate",
    "get_analysis_component_color",
    "AnalysisService",
    "COMPONENT_PARSING_PROMPT",
    "MESSAGE_SCORING_PROMPT",
    "AnalysisWatchlistPlugin",
]
