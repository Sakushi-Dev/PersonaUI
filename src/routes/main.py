"""
Main Routes – Hauptseite (React SPA)
"""
from flask import Blueprint
from routes.react_frontend import serve_react_app

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Hauptseite – liefert das React SPA aus."""
    return serve_react_app()
