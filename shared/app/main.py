from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.agents import router as agents_router
from app.routes.portfolio import router as portfolio_router
from app.routes.reports import router as reports_router
from app.routes.settings import router as settings_router
from app.routes.trades import router as trades_router

app = FastAPI(
    title="AI Investment Simulator API",
    description=(
        "SIMULATION ONLY — Paper trading simulator powered by AI agents. "
        "Not financial advice. No real trades are executed."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents_router)
app.include_router(portfolio_router)
app.include_router(reports_router)
app.include_router(settings_router)
app.include_router(trades_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
