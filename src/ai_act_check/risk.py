"""Risk classes shared by the classifier and the eval harness."""

from enum import StrEnum


class RiskClass(StrEnum):
    """Risk classes under the EU AI Act, plus `unclear` for cases a human must decide."""

    PROHIBITED = "prohibited"
    HIGH_RISK = "high_risk"
    TRANSPARENCY = "transparency"
    MINIMAL = "minimal"
    UNCLEAR = "unclear"
