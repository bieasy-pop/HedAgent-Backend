import traceback
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi

from app.config import settings
from app.routers import auth, students, interventions, ai, notifications

ENV_LABEL = "🔧 DEV" if settings.is_development else "🚀 PROD"

app = FastAPI(
    title=f"Academic Intervention API [{ENV_LABEL}]",
    description=f"""
Backend for the student academic intervention system.

**Environment:** `{settings.APP_ENV}`
**Firebase Project:** {'Development' if settings.is_development else 'Production'}

> ⚠️ You are {'in **development** mode — use test accounts only.' if settings.is_development else 'in **production** mode.'}

## Authentication
Click the **Authorize 🔒** button at the top right and enter:
```
Bearer <your_token>
```
Get a token from `POST /api/auth/login` or `POST /api/auth/register`.
""",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Custom OpenAPI schema with Bearer auth ────────────────────────────────────

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Add Bearer token security scheme so the Authorize button works in Swagger
    schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "Firebase ID Token",
            "description": "Enter the token from /api/auth/login or /api/auth/register",
        }
    }

    # Apply security globally — all endpoints will show the lock icon
    schema["security"] = [{"BearerAuth": []}]

    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi


# ── Exception handlers ────────────────────────────────────────────────────────

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Converts FastAPI's default 422 validation errors into your standard
    { success, message, code } shape. Handles missing Authorization header
    and any other request validation failures gracefully.
    """
    errors = exc.errors()

    # Check specifically for missing authorization header
    for error in errors:
        loc = error.get("loc", [])
        if "authorization" in loc or "Authorization" in loc:
            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "message": "Authorization header is missing. Please log in to get a token, then click the Authorize button in Swagger or include 'Authorization: Bearer <token>' in your request.",
                    "code": "MISSING_TOKEN",
                }
            )

    # Generic validation error — list what fields failed
    messages = []
    for error in errors:
        field = " → ".join(str(l) for l in error.get("loc", []))
        msg = error.get("msg", "Invalid value")
        messages.append(f"{field}: {msg}")

    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "Request validation failed: " + "; ".join(messages),
            "code": "VALIDATION_ERROR",
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if settings.is_development:
        error_detail = traceback.format_exc()
        print("UNHANDLED EXCEPTION:\n", error_detail)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": str(exc),
                "traceback": error_detail.splitlines(),
            },
        )
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "An unexpected error occurred. Please try again.",
            "code": "INTERNAL_SERVER_ERROR",
        },
    )


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(auth.router,          prefix="/api/auth",
                   tags=["Auth"])
app.include_router(students.router,
                   prefix="/api/students",      tags=["Students"])
app.include_router(interventions.router,
                   prefix="/api/interventions", tags=["Interventions"])
app.include_router(ai.router,            prefix="/api/ai",
                   tags=["AI"])
app.include_router(notifications.router,
                   prefix="/api/notifications", tags=["Notifications"])


@app.get("/", tags=["Health"])
def root():
    return {
        "status": "ok",
        "environment": settings.APP_ENV,
        "message": f"Academic Intervention API is running [{ENV_LABEL}]",
    }


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy", "environment": settings.APP_ENV}
