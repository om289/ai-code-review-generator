"""Flask routes — web UI and JSON API endpoints."""

from __future__ import annotations

import logging
import os
import re
import uuid

from flask import Blueprint, Response, jsonify, render_template, request

from src.config import settings
from src.database import (
    get_run,
    load_history,
    metrics_summary,
    save_feedback,
    save_run,
)
from src.llm_client import ReviewClient
from src.models import AppError, ReviewRequest
from src.prompts import PROMPT_VERSION

logger = logging.getLogger("code_review")

bp = Blueprint("main", __name__)


def _sanitize_input(text: str) -> str:
    """Pass text unchanged. Sanitizing diffs by stripping <...> destroys code (e.g. templates, comparisons)."""
    return text


def _request_id() -> str:
    return uuid.uuid4().hex[:10]


def _check_api_key() -> None:
    """If APP_API_KEY is configured, require X-API-Key header on API routes."""
    if not settings.API_KEY:
        return
    provided = request.headers.get("X-API-Key", "")
    if provided != settings.API_KEY:
        raise AppError("Invalid or missing API key.", status_code=401)


# ---------------------------------------------------------------------------
# Web routes
# ---------------------------------------------------------------------------

@bp.route("/", methods=["GET", "POST"])
def index():
    sample_diff = ""
    if settings.SAMPLE_DIFF_PATH.exists():
        sample_diff = settings.SAMPLE_DIFF_PATH.read_text(encoding="utf-8")

    diff_text = request.form.get("diff_text", sample_diff)
    review = None
    error = None
    run_id = None
    req_id = _request_id()

    if request.method == "POST":
        try:
            diff_text = _sanitize_input(diff_text)
            req = ReviewRequest(diff_text=diff_text, max_chars=settings.MAX_DIFF_CHARS)
            req.validate()

            client = ReviewClient(settings)
            review_text, model_name = client.generate_review(
                req.diff_text, max_chars=settings.MAX_DIFF_CHARS
            )
            review = review_text
            run_id = save_run(
                source="web",
                model_name=model_name,
                prompt_version=PROMPT_VERSION,
                diff_text=req.diff_text,
                output=review_text,
            )
            logger.info("review_complete request_id=%s run_id=%s", req_id, run_id)
        except AppError as exc:
            error = str(exc)
        except Exception as exc:
            logger.exception("Unexpected error request_id=%s", req_id)
            error = f"Unexpected error: {exc}"

    return render_template(
        "index.html",
        diff_text=diff_text,
        review=review,
        error=error,
        run_id=run_id,
        model=settings.AI_MODEL,
        history=load_history(),
        metrics=metrics_summary(),
    )


@bp.post("/feedback")
def feedback_form():
    run_id = request.form.get("run_id", "")
    rating = int(request.form.get("rating", "0"))
    comment = _sanitize_input(request.form.get("comment", ""))
    save_feedback(run_id, rating, comment)
    return Response("Feedback saved. You can go back to the app.", mimetype="text/plain")


# ---------------------------------------------------------------------------
# JSON API routes
# ---------------------------------------------------------------------------

@bp.post("/api/review")
def api_review():
    _check_api_key()
    data = request.get_json(silent=True) or {}
    diff_text = _sanitize_input(data.get("diff_text", ""))

    req = ReviewRequest(diff_text=diff_text, max_chars=settings.MAX_DIFF_CHARS)
    req.validate()

    client = ReviewClient(settings)
    review_text, model_name = client.generate_review(
        req.diff_text, max_chars=settings.MAX_DIFF_CHARS
    )
    run_id = save_run(
        source="api",
        model_name=model_name,
        prompt_version=PROMPT_VERSION,
        diff_text=req.diff_text,
        output=review_text,
    )
    return jsonify({
        "run_id": run_id,
        "model_name": model_name,
        "prompt_version": PROMPT_VERSION,
        "review": review_text,
    })


@bp.get("/api/runs")
def api_runs():
    _check_api_key()
    limit = min(int(request.args.get("limit", 25)), 100)
    return jsonify({"runs": load_history(limit=limit)})


@bp.get("/api/runs/<run_id>")
def api_run(run_id: str):
    _check_api_key()
    record = get_run(run_id)
    if not record:
        return jsonify({"error": "Run not found"}), 404
    return jsonify(record)


@bp.post("/api/feedback")
def api_feedback():
    _check_api_key()
    data = request.get_json(silent=True) or {}
    feedback = save_feedback(
        data.get("run_id", ""),
        int(data.get("rating", 0)),
        _sanitize_input(data.get("comment", "")),
    )
    return jsonify(feedback), 201


@bp.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "model": settings.AI_MODEL,
        "api_key_configured": settings.has_api_key,
        "prompt_version": PROMPT_VERSION,
    })


@bp.get("/metrics")
def metrics():
    return jsonify(metrics_summary())


@bp.get("/export/<run_id>.txt")
def export_run(run_id: str):
    record = get_run(run_id)
    if not record:
        return Response("Run not found", status=404)
    text = f"""AI Code Review Export
Run ID: {record["id"]}
Created: {record["created_at"]}
Source: {record["source"]}
Model: {record["model_name"]}
Prompt Version: {record["prompt_version"]}

{record["output"]}
"""
    return Response(
        text,
        mimetype="text/plain",
        headers={"Content-Disposition": f"attachment; filename=code-review-{run_id}.txt"},
    )


# ---------------------------------------------------------------------------
# Error handler (registered by the app factory)
# ---------------------------------------------------------------------------

def register_error_handlers(app):
    """Register error handlers on the Flask app."""

    @app.errorhandler(AppError)
    def handle_app_error(exc: AppError):
        if request.path.startswith("/api/"):
            return jsonify({"error": str(exc)}), exc.status_code
        sample_diff = ""
        if settings.SAMPLE_DIFF_PATH.exists():
            sample_diff = settings.SAMPLE_DIFF_PATH.read_text(encoding="utf-8")
        return render_template(
            "index.html",
            diff_text=request.form.get("diff_text", sample_diff),
            review=None,
            error=str(exc),
            run_id=None,
            model=settings.AI_MODEL,
            history=load_history(),
            metrics=metrics_summary(),
        ), exc.status_code
