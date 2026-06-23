"""Session middleware for UI endpoints"""

from application.settings import app_settings
from starlette.middleware.sessions import SessionMiddleware


def get_session_middleware():
    """Get configured session middleware"""
    return SessionMiddleware(
        secret_key=app_settings.session_secret_key,
        max_age=app_settings.session_max_age,
        session_cookie="mario_session",  # Custom cookie name
        https_only=not app_settings.debug,  # HTTPS only in production
        same_site="lax",
    )
