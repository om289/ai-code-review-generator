"""Data models for code review requests and results."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


class AppError(Exception):
    """Application-level error with an HTTP status code."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass
class ReviewRequest:
    """Validated review request."""

    diff_text: str
    max_chars: int = 30000

    def __post_init__(self) -> None:
        self.diff_text = self.diff_text.strip()

    def validate(self) -> None:
        if not self.diff_text:
            raise AppError("Please provide a non-empty code diff.")
        if len(self.diff_text) > self.max_chars:
            raise AppError(
                f"Diff is too long ({len(self.diff_text)} chars). "
                f"Limit is {self.max_chars} characters."
            )


@dataclass
class ReviewFinding:
    """A single finding from a code review."""

    severity: str = ""
    category: str = ""
    location: str = ""
    issue: str = ""
    fix: str = ""


@dataclass
class ReviewResult:
    """Complete review result."""

    summary: str = ""
    raw_output: str = ""
    model_name: str = ""
    prompt_version: str = ""
    findings: list[ReviewFinding] = field(default_factory=list)

    @staticmethod
    def _sanitize_text(text: str) -> str:
        """Strip potential HTML/script tags from text."""
        return re.sub(r"<[^>]+>", "", text)
