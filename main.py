from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from pathlib import Path

from app.config import settings
from app.database import engine, Base, async_session
from app.core.logger import logger
from app.core.ssh import ssh_pool
from app.core.docker_client import docker_client

# Import routers
from app.routers.auth import router as auth_router, user_router
from app.routers.team import router as team_router
from app.routers.host import router as host_router
from app.routers.webssh import router as webssh_router
from app.routers.permission import router as permission_router
from app.routers.dashboard import router as dashboard_router
from app.routers.monitor import router as monitor_router
from app.routers.docker import router as docker_router
from app.routers.audit import router as audit_router
from app.routers.site_config import router as site_config_router

# Keep old auxiliary router
from routers.auxiliary import auxiliary_router


async def _ensure_default_admin():
    """Create default super admin if no admin user exists."""
    from sqlalchemy import select, text
    from sqlalchemy.exc import IntegrityError
    from app.models.user import User, UserRole, UserStatus
    from app.core.security import hash_password

    try:
        async with async_session() as db:
            # Check if users table exists first
            result = await db.execute(
                text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users')")
            )
            if not result.scalar():
                logger.warning("Users table does not exist yet, skipping admin creation")
                return

            result = await db.execute(
                select(User).where(User.role == UserRole.admin)
            )
            if result.scalar_one_or_none():
                logger.info("Admin user already exists")
                return

            admin = User(
                username=settings.DEFAULT_ADMIN_USERNAME,
                email=settings.DEFAULT_ADMIN_EMAIL,
                hashed_password=hash_password(settings.DEFAULT_ADMIN_PASSWORD),
                display_name="Super Admin",
                role=UserRole.admin,
                status=UserStatus.active,
            )
            db.add(admin)
            await db.commit()
            logger.info(
                f"Default admin created: {settings.DEFAULT_ADMIN_USERNAME} / {settings.DEFAULT_ADMIN_PASSWORD}"
            )
    except IntegrityError:
        # Another worker already created the admin
        logger.info("Admin user was created by another worker, skipping")
    except Exception as e:
        logger.error(f"Failed to ensure default admin: {e}")
        import traceback
        logger.error(traceback.format_exc())


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"Starting {settings.APP_NAME} in {settings.APP_ENV} mode")

    # Create tables automatically
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables ensured")
    except IntegrityError:
        logger.info("Database tables already exist (created by another worker)")
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        import traceback
        logger.error(traceback.format_exc())

    # Ensure default admin exists
    await _ensure_default_admin()

    yield

    # Shutdown
    logger.info("Shutting down...")
    await ssh_pool.close_all()
    await docker_client.close()
    logger.info("Cleanup complete")


app = FastAPI(
    title="CloudPivot API",
    version="1.0.0",
    description="CloudPivot 云枢 - SSH运维堡垒机平台 API",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.APP_DEBUG else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auxiliary_router)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(user_router, prefix="/api/v1")
app.include_router(team_router, prefix="/api/v1")
app.include_router(host_router, prefix="/api/v1")
app.include_router(webssh_router, prefix="/api/v1")
app.include_router(permission_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(monitor_router, prefix="/api/v1")
app.include_router(docker_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")
app.include_router(site_config_router, prefix="/api/v1")


# ===== Serve Frontend Static Files =====
STATIC_DIR = Path(__file__).parent / "static"


# Mount static assets first (if exists)
if STATIC_DIR.exists() and (STATIC_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")


# Catch-all for SPA: must be last route
@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str):
    # Only serve files for non-API paths
    if full_path.startswith("api/") or full_path.startswith("ws/"):
        from fastapi.responses import JSONResponse
        return JSONResponse({"detail": "Not found"}, status_code=404)
    file_path = STATIC_DIR / full_path
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)
    # SPA fallback: return index.html for all other routes
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"name": settings.APP_NAME, "version": "1.0.0", "status": "running"}
