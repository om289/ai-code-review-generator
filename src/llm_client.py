"""LLM client with retry logic, timeout, and structured error handling."""

from __future__ import annotations

import logging
import time

from openai import APIConnectionError, APITimeoutError, OpenAI, RateLimitError

from src.config import Settings
from src.models import AppError
from src.prompts import PROMPT_VERSION, SYSTEM_PROMPT, build_review_prompt

logger = logging.getLogger("code_review")


class LLMTimeoutError(AppError):
    def __init__(self) -> None:
        super().__init__("The AI model took too long to respond. Please try again.", 504)


class LLMRateLimitError(AppError):
    def __init__(self) -> None:
        super().__init__("AI service rate limit reached. Please wait a moment and retry.", 429)


class LLMAPIError(AppError):
    def __init__(self, detail: str = "") -> None:
        msg = "AI service is temporarily unavailable."
        if detail:
            msg += f" ({detail})"
        super().__init__(msg, 502)


class ReviewClient:
    """Wraps the OpenAI-compatible API with retry, timeout, and error handling."""

    RETRYABLE_STATUS_CODES = {429, 500, 502, 503}

    def __init__(self, cfg: Settings) -> None:
        if not cfg.has_api_key:
            raise AppError("Set AI_API_KEY before running reviews.", status_code=503)
        self._client = OpenAI(api_key=cfg.AI_API_KEY, base_url=cfg.AI_BASE_URL)
        self._model = cfg.AI_MODEL
        self._timeout = cfg.REQUEST_TIMEOUT
        self._max_retries = cfg.LLM_MAX_RETRIES
        self._temperature = cfg.LLM_TEMPERATURE

    def generate_review(self, diff_text: str, max_chars: int = 30000) -> tuple[str, str]:
        """Send a diff to the LLM and return (review_text, model_name).

        Retries transient failures with exponential backoff.
        """
        user_message = build_review_prompt(diff_text, max_chars=max_chars)
        last_error: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                logger.info(
                    "LLM request attempt=%d model=%s diff_chars=%d",
                    attempt,
                    self._model,
                    len(diff_text),
                )
                t0 = time.monotonic()
                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    temperature=self._temperature,
                    timeout=self._timeout,
                )
                elapsed = time.monotonic() - t0
                content = response.choices[0].message.content or ""
                logger.info("LLM response received elapsed=%.2fs chars=%d", elapsed, len(content))
                return content, self._model

            except APITimeoutError:
                logger.warning("LLM timeout attempt=%d", attempt)
                last_error = LLMTimeoutError()
            except RateLimitError:
                logger.warning("LLM rate limited attempt=%d", attempt)
                last_error = LLMRateLimitError()
            except APIConnectionError as exc:
                logger.warning("LLM connection error attempt=%d error=%s", attempt, exc)
                last_error = LLMAPIError(str(exc))
            except Exception as exc:
                logger.exception("LLM unexpected error attempt=%d", attempt)
                last_error = LLMAPIError(str(exc))

            if attempt < self._max_retries:
                backoff = 2 ** (attempt - 1)
                logger.info("Retrying in %ds...", backoff)
                time.sleep(backoff)

        raise last_error  # type: ignore[misc]

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def prompt_version(self) -> str:
        return PROMPT_VERSION
