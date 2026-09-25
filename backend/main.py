import os
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.routes.boards import router as boards_router

app = FastAPI(title="TaskFlow Pro API", version="1.0.0")

# CORS configuration: strict frontend origin only, never '*'
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
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


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
