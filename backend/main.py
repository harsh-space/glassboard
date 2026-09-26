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

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
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


@app.get("/api/health")

def health_check():
    return {"status": "ok"}
