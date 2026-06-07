"""Prompt templates and builder functions for code review generation."""

PROMPT_VERSION = "code-review-v2"

SYSTEM_PROMPT = """You are a senior code reviewer.
Review code diffs for bugs, security risks, regressions, edge cases, and missing tests.
Return practical review comments that a developer can act on.

Format the answer as:
Summary:
- Short overall summary

Findings:
- Severity: P0/P1/P2/P3
  Category: bug/security/performance/maintainability/testing
  Location: file and line hint if available
  Issue: concise explanation
  Fix: concrete suggestion

If no meaningful issue is found, say no major issues were found and suggest one useful test.
"""


def build_review_prompt(diff_text: str, max_chars: int = 30000) -> str:
    """Build the user message for the LLM, with safety truncation."""
    truncated = diff_text[:max_chars]
    if len(diff_text) > max_chars:
        truncated += f"\n\n[... truncated — {len(diff_text) - max_chars} chars omitted]"
    return f"Review this diff:\n\n{truncated}"
