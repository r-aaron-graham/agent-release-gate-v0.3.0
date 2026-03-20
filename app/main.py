from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.api.routes import api_router, ui_router
from app.core.config import settings
from app.db.session import create_schema_for_local_dev, tables_exist
from app.services.utils import new_csrf_token

@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_create_sqlite_schema and settings.database_url.startswith("sqlite") and not tables_exist():
        create_schema_for_local_dev()
    yield


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret_key,
    same_site="lax",
    https_only=False,
)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.state.templates = Jinja2Templates(directory="app/templates")
app.include_router(ui_router)
app.include_router(api_router, prefix="/api/v1")


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exc: RequestValidationError):
    accepts_html = "text/html" in request.headers.get("accept", "") or request.url.path in {"/submit", "/admin/login"}
    if accepts_html:
        if "csrf_token" not in request.session:
            request.session["csrf_token"] = new_csrf_token()
        message = "One or more fields were invalid. Please correct the form and try again."
        return app.state.templates.TemplateResponse(
            request,
            "error.html",
            {
                "message": message,
                "errors": exc.errors(),
                "back_url": request.headers.get("referer") or "/",
            },
            status_code=422,
        )
    return JSONResponse(status_code=422, content={"detail": exc.errors()})
