"""
React Frontend – Liefert das gebaute React-SPA aus frontend/dist/ aus.

Wenn der Build existiert (frontend/dist/index.html), wird das React-Frontend
für alle Seiten-Routen verwendet. API-Routen bleiben unverändert.
"""
import os
from flask import Blueprint, send_from_directory

# Pfad zum React-Build: src/../frontend/dist
DIST_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'frontend', 'dist')
)


def has_react_build():
    """Prüft ob ein React-Build vorhanden ist."""
    return os.path.isfile(os.path.join(DIST_DIR, 'index.html'))


# Blueprint mit eigenem static_folder für die React-Assets
react_bp = Blueprint(
    'react',
    __name__,
    static_folder=os.path.join(DIST_DIR, 'assets'),
    static_url_path='/assets',
)


def serve_react_app():
    """Liefert die React index.html aus (für Client-Side-Routing)."""
    return send_from_directory(DIST_DIR, 'index.html')


@react_bp.route('/vite.svg')
def vite_svg():
    """Vite-Favicon."""
    return send_from_directory(DIST_DIR, 'vite.svg')
