import traceback
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routers import auth, students, interventions, ai, notifications

app = FastAPI(
    title="Academic Intervention API",
    description="Backend for the student academic intervention system.",
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


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catches any unhandled exception and returns the real error message
    instead of a generic 500. Remove or restrict this before going to production.
    """
    error_detail = traceback.format_exc()
    print("UNHANDLED EXCEPTION:\n", error_detail)
    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc),
            "traceback": error_detail.splitlines(),
        },
    )


app.include_router(auth.router,          prefix="/api/auth",          tags=["Auth"])
app.include_router(students.router,      prefix="/api/students",      tags=["Students"])
app.include_router(interventions.router, prefix="/api/interventions", tags=["Interventions"])
app.include_router(ai.router,            prefix="/api/ai",            tags=["AI"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "Academic Intervention API is running"}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}
