from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from app.database import get_trade_detail, get_trade_package, init_db, list_trade_packages, save_trade_package
from app.schemas import StoredTradePackage, TradeDetail, TradeInput, TradeListItem
from app.services.trade_package import build_trade_package


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="TradeNotion API", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/trade-packages", response_model=StoredTradePackage)
def create_trade_package(trade: TradeInput) -> StoredTradePackage:
    package = build_trade_package(trade)
    return save_trade_package(package)


@app.get("/trade-packages", response_model=list[TradeListItem])
def read_trade_packages() -> list[TradeListItem]:
    return list_trade_packages()


@app.get("/trade-packages/{trade_package_id}", response_model=StoredTradePackage)
def read_trade_package(trade_package_id: int) -> StoredTradePackage:
    package = get_trade_package(trade_package_id)
    if package is None:
        raise HTTPException(status_code=404, detail="Trade package not found")
    return package


@app.get("/trades", response_model=list[TradeListItem])
def read_trades() -> list[TradeListItem]:
    return list_trade_packages()


@app.get("/trades/{trade_package_id}", response_model=TradeDetail)
def read_trade(trade_package_id: int) -> TradeDetail:
    trade = get_trade_detail(trade_package_id)
    if trade is None:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade
