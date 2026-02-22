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

# Pfad zum öffentlichen Avatar-Ordner (für dynamisch hinzugefügte Custom-Avatare)
PUBLIC_AVATAR_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'frontend', 'public', 'avatar')
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


@react_bp.route('/avatar/costum/<path:filename>')
def serve_custom_avatar(filename):
    """Liefert dynamisch hochgeladene Custom-Avatare aus frontend/public/avatar/costum/."""
    costum_dir = os.path.join(PUBLIC_AVATAR_DIR, 'costum')
    return send_from_directory(costum_dir, filename)


@react_bp.route('/avatar/<path:filename>')
def serve_avatar(filename):
    """Liefert Standard-Avatare – bevorzugt aus dem Build, Fallback aus public/."""
    dist_avatar_dir = os.path.join(DIST_DIR, 'avatar')
    if os.path.isfile(os.path.join(dist_avatar_dir, filename)):
        return send_from_directory(dist_avatar_dir, filename)
    return send_from_directory(PUBLIC_AVATAR_DIR, filename)
