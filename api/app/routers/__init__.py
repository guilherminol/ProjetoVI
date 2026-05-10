from app.routers.admin import router as admin_router  # noqa: F401
from app.routers.auth import router as auth_router  # noqa: F401
from app.routers.users import router as users_router  # noqa: F401

__all__ = ["admin_router", "auth_router", "users_router"]
