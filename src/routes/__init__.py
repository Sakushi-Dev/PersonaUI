"""
Routes Package - Modulare Route-Verwaltung für die Chat-Anwendung
"""
# Import aller Route-Blueprints
from routes.main import main_bp
from routes.chat import chat_bp
from routes.character import character_bp
from routes.sessions import sessions_bp
from routes.api import api_bp
from routes.avatar import avatar_bp
from routes.access import access_bp
from routes.settings import settings_bp
from routes.custom_specs import custom_specs_bp
from routes.user_profile import user_profile_bp
from routes.onboarding import onboarding_bp
from routes.commands import commands_bp
from routes.react_frontend import react_bp, has_react_build


def register_routes(app):
    """Registriert alle Route-Blueprints bei der Flask-App"""
    # React-Frontend Blueprint (Assets aus frontend/dist/)
    if has_react_build():
        app.register_blueprint(react_bp)

    app.register_blueprint(access_bp)  # Access-Control muss zuerst registriert werden
    app.register_blueprint(onboarding_bp)  # Onboarding vor main, damit /onboarding erreichbar ist
    app.register_blueprint(main_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(character_bp)
    app.register_blueprint(sessions_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(avatar_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(custom_specs_bp)
    app.register_blueprint(user_profile_bp)
    app.register_blueprint(commands_bp)

