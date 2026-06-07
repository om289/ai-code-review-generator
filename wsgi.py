"""WSGI entry point for production deployment (Gunicorn, etc.)."""

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run()
