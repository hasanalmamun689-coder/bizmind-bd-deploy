import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import (
    admin, ai, alerts, analytics, auth, customers, expenses, forecast,
    inventory, procurement, products, recommendations, sales, suppliers,
)
from app.core.config import settings

logger = logging.getLogger("sme")

app = FastAPI(title=settings.APP_NAME, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in (auth, products, inventory, sales, customers, suppliers, procurement, expenses,
               analytics, forecast, alerts, recommendations, ai, admin):
    app.include_router(module.router)


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    def friendly(e: dict) -> str:
        field = ".".join(str(p) for p in e["loc"][1:]).replace("_", " ") or "request"
        kind = e["type"]
        if kind == "missing":
            return f"{field} is required"
        if kind.startswith("uuid"):
            return f"{field} is not a valid identifier"
        if kind in ("string_too_short", "string_too_long") or "greater" in kind or "less" in kind:
            return f"{field}: {e['msg'].lower()}"
        if kind.startswith("value_error") and "email" in field:
            return f"{field} is not a valid email address"
        return f"{field} is invalid"

    fields = [friendly(e) for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": "Invalid input: " + "; ".join(fields) + "."})


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception):
    # section 36: never leak stack traces or DB internals to the client.
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Something went wrong on our side. Please try again."})


@app.get("/api/health")
def health():
    return {"status": "ok"}
