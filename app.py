"""AI Code Review Comment Generator — Application factory and CLI."""

import argparse
import json
import logging
import sys
from pathlib import Path

from flask import Flask

from src.config import load_dotenv, settings
from src.database import init_db
from src.llm_client import ReviewClient
from src.models import ReviewRequest
from src.prompts import PROMPT_VERSION
from src.routes import bp, register_error_handlers


def _setup_logging() -> None:
    """Configure structured logging."""
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    if settings.LOG_FORMAT == "json":
        fmt = '{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}'
    else:
        fmt = "%(asctime)s %(levelname)s %(name)s %(message)s"

    logging.basicConfig(level=level, format=fmt, force=True)


def create_app() -> Flask:
    """Flask application factory."""
    load_dotenv()
    _setup_logging()

    app = Flask(__name__)
    app.config["SECRET_KEY"] = settings.SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = settings.MAX_CONTENT_LENGTH

    # Security headers
    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response

    app.register_blueprint(bp)
    register_error_handlers(app)

    init_db()

    logger = logging.getLogger("code_review")
    for warning in settings.validate():
        logger.warning(warning)

    return app


def main() -> None:
    """CLI entry point — review a diff file or launch the web server."""
    load_dotenv()
    _setup_logging()

    parser = argparse.ArgumentParser(description="AI code review comment generator.")
    parser.add_argument("--diff", help="Path to a .patch or diff file for CLI review.")
    parser.add_argument("--host", default="127.0.0.1", help="Host for the web app.")
    parser.add_argument("--port", default=5001, type=int, help="Port for the web app.")
    args = parser.parse_args()

    if args.diff:
        diff_text = Path(args.diff).read_text(encoding="utf-8")
        req = ReviewRequest(diff_text=diff_text, max_chars=settings.MAX_DIFF_CHARS)
        req.validate()
        client = ReviewClient(settings)
        review_text, _ = client.generate_review(req.diff_text)
        print(review_text)
        return

    app = create_app()
    app.run(host=args.host, port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
