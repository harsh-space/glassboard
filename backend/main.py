import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from contextlib import asynccontextmanager
from backend.db import Base, engine
from backend.routes.boards import router as boards_router
from backend.routes.tasks import router as tasks_router
from backend.routes.dependencies import router as dependencies_router
from backend.routes.auth import router as auth_router

# Ensure all models are registered with Base before create_all
import backend.models  # noqa: F401  (registers User, Board, Task, Dependency, etc.)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from sqlalchemy import text
    from backend.db import SessionLocal

    # Create all tables (safe, skips existing)
    Base.metadata.create_all(bind=engine)

    # Explicit migration: ensure owner_id column exists on board table
    # (handles Neon instances upgraded from pre-auth schema)
    try:
        db = SessionLocal()
        db.execute(text(
            "ALTER TABLE board ADD COLUMN IF NOT EXISTS owner_id INTEGER REFERENCES \"user\"(id) ON DELETE CASCADE"
        ))
        db.commit()
        db.close()
    except Exception:
        pass

    # Auto-seed canonical board if database is fresh/empty
    try:
        from backend.models import Board
        from scripts.seed import seed_database
        db = SessionLocal()
        if not db.query(Board).filter(Board.id == 1).first():
            seed_database()
        db.close()
    except Exception:
        pass
    yield


app = FastAPI(title="TaskFlow Pro API", version="1.0.0", lifespan=lifespan)


# CORS configuration: allow local dev + any Vercel deployment automatically
raw_origins = os.getenv("ALLOWED_ORIGIN", os.getenv("FRONTEND_ORIGIN", "http://localhost:5173"))
allowed_origins = [o.strip().rstrip("/") for o in raw_origins.split(",") if o.strip()]
is_wildcard = "*" in allowed_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if is_wildcard else allowed_origins,
    allow_origin_regex=None if is_wildcard else r"^https?://.*\.vercel\.app$|^http://localhost(:\d+)?$",
    allow_credentials=not is_wildcard,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Uniform error formatting per BUILD_SPEC.md §4:
# {"error": {"code": "SOME_CODE", "message": "human readable", "details": {}}}
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        payload = {
            "error": {
                "code": exc.detail.get("code", "ERROR"),
                "message": exc.detail.get("message", "An error occurred."),
                "details": exc.detail.get("details", {}),
            }
        }
    else:
        payload = {
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": str(exc.detail),
                "details": {},
            }
        }
    return JSONResponse(status_code=exc.status_code, content=payload)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request payload.",
                "details": {"errors": exc.errors()},
            }
        },
    )


# Mount routers under /api
app.include_router(boards_router, prefix="/api")
app.include_router(tasks_router, prefix="/api")
app.include_router(dependencies_router, prefix="/api")
app.include_router(auth_router, prefix="/api")


@app.get("/")
def root():
    return {
        "message": "TaskFlow Pro API is running",
        "status": "healthy",
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/api/health")
def health_check():
    db_status = "ok"
    try:
        from sqlalchemy import text
        from backend.db import SessionLocal
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception as e:
        db_status = f"unhealthy: {e}"
    return {
        "status": "ok",
        "database": db_status,
    }
