import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.accounts import router as accounts_router
from app.api.advisor import router as advisor_router
from app.api.auth import router as auth_router
from app.api.cashflow import router as cashflow_router
from app.api.categories import router as categories_router
from app.api.dashboard import router as dashboard_router
from app.api.fire import router as fire_router
from app.api.net_worth import router as net_worth_router
from app.api.properties import router as properties_router
from app.api.spending import router as spending_router
from app.api.sync import router as sync_router
from app.api.tax import router as tax_router
from app.api.transactions import router as transactions_router
from app.core.config import get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup validation
    settings = get_settings()
    if settings.JWT_SECRET_KEY in ("change-me", ""):
        raise RuntimeError(
            "JWT_SECRET_KEY must be set to a secure random value. "
            "See .env.example for details."
        )
    if not settings.AUTH_PASSWORD_HASH or not settings.AUTH_PASSWORD_HASH.startswith("$2"):
        raise RuntimeError(
            "AUTH_PASSWORD_HASH must be set to a valid bcrypt hash. "
            "Generate one with: python -c \"import bcrypt; print(bcrypt.hashpw(b'yourpassword', bcrypt.gensalt()).decode())\""
        )
    yield
    # Shutdown


app = FastAPI(
    title="FIRE Master",
    version="0.1.0",
    lifespan=lifespan,
)

_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _settings.CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(advisor_router)
app.include_router(auth_router)
app.include_router(accounts_router)
app.include_router(cashflow_router)
app.include_router(categories_router)
app.include_router(dashboard_router)
app.include_router(fire_router)
app.include_router(net_worth_router)
app.include_router(properties_router)
app.include_router(spending_router)
app.include_router(sync_router)
app.include_router(tax_router)
app.include_router(transactions_router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
