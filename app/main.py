import traceback
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi

from app.config import settings
from app.routers import auth, students, interventions, ai, notifications
from app.routers import courses, classification, analytics, reminders, admin

ENV_LABEL = "🔧 DEV" if settings.is_development else "🚀 PROD"

app = FastAPI(
    title=f"Academic Intervention API [{ENV_LABEL}]",
    description=f"""
Backend for the student academic intervention system.

**Environment:** `{settings.APP_ENV}`

## Authentication
Click **Authorize 🔒** and enter: `Bearer <your_token>`
Get a token from `POST /api/auth/login`.
""",
    version="2.0.0",
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


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(title=app.title, version=app.version, description=app.description, routes=app.routes)
    schema["components"]["securitySchemes"] = {
        "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "Firebase ID Token"}
    }
    schema["security"] = [{"BearerAuth": []}]
    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    for error in errors:
        if "authorization" in error.get("loc", []):
            return JSONResponse(status_code=401, content={"success": False, "message": "Authorization header is missing. Click Authorize 🔒 in Swagger or include 'Authorization: Bearer <token>'.", "code": "MISSING_TOKEN"})
    messages = [f"{' → '.join(str(l) for l in e.get('loc', []))}: {e.get('msg')}" for e in errors]
    return JSONResponse(status_code=422, content={"success": False, "message": "Validation failed: " + "; ".join(messages), "code": "VALIDATION_ERROR"})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if settings.is_development:
        error_detail = traceback.format_exc()
        print("UNHANDLED EXCEPTION:\n", error_detail)
        return JSONResponse(status_code=500, content={"success": False, "message": str(exc), "traceback": error_detail.splitlines()})
    return JSONResponse(status_code=500, content={"success": False, "message": "An unexpected error occurred.", "code": "INTERNAL_SERVER_ERROR"})


# ── Phase 1 routers ───────────────────────────────────────────────────────────
app.include_router(auth.router,          prefix="/api/auth",          tags=["Auth"])
app.include_router(students.router,      prefix="/api/students",      tags=["Students"])
app.include_router(interventions.router, prefix="/api/interventions", tags=["Interventions"])
app.include_router(ai.router,            prefix="/api/ai",            tags=["AI — OpenAI"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])

# ── Phase 2 routers ───────────────────────────────────────────────────────────
app.include_router(courses.router,        prefix="/api/courses",        tags=["Courses"])
app.include_router(classification.router, prefix="/api/classification",  tags=["AI — Classification"])
app.include_router(analytics.router,      prefix="/api/analytics",       tags=["Analytics"])
app.include_router(reminders.router,      prefix="/api/reminders",       tags=["Reminders"])
app.include_router(admin.router,          prefix="/api/admin",           tags=["Admin"])


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "version": "2.0.0", "environment": settings.APP_ENV}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy", "environment": settings.APP_ENV}
