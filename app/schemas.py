from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class TradeInput(BaseModel):
    symbol: str = Field(examples=["NIFTY", "BTCUSD", "XAUUSD", "CL"])
    asset_class: Literal["equity", "index", "crypto", "forex", "commodity", "futures", "option", "other"] = "index"
    exchange: str | None = Field(default=None, examples=["NSE", "BINANCE", "COMEX", "NYMEX"])
    currency: str | None = Field(default=None, examples=["INR", "USD"])
    timezone: str | None = Field(default=None, examples=["Asia/Kolkata", "UTC", "America/New_York"])
    side: Literal["BUY", "SELL"]
    entry_price: float
    exit_price: float
    stop_loss_price: float | None = None
    take_profit_price: float | None = None
    quantity: int
    entry_time: datetime
    exit_time: datetime
    notes: str | None = None
    very_high_timeframe: str = "1d"
    high_timeframe: str = "4h"
    medium_timeframe: str = "1h"
    low_timeframe: str = "15m"
    execution_timeframe: str = "5m"
    higher_timeframe: str = "1h"

    @model_validator(mode="after")
    def validate_risk_levels(self) -> "TradeInput":
        if self.side == "BUY":
            if self.stop_loss_price is not None and self.stop_loss_price >= self.entry_price:
                raise ValueError("BUY stop_loss_price must be below entry_price")
            if self.take_profit_price is not None and self.take_profit_price <= self.entry_price:
                raise ValueError("BUY take_profit_price must be above entry_price")
        else:
            if self.stop_loss_price is not None and self.stop_loss_price <= self.entry_price:
                raise ValueError("SELL stop_loss_price must be above entry_price")
            if self.take_profit_price is not None and self.take_profit_price >= self.entry_price:
                raise ValueError("SELL take_profit_price must be below entry_price")
        return self


class Candle(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class IndicatorSnapshot(BaseModel):
    ema20: float | None
    ema50: float | None
    rsi14: float | None
    vwap: float | None
    volume_average20: float | None
    volume_ratio: float | None


class DerivedContext(BaseModel):
    trend: str
    momentum_state: str
    volume_participation: str
    price_vs_vwap: str


class ManagementMetrics(BaseModel):
    mae_points: float
    mfe_points: float
    captured_points: float
    capture_efficiency: float | None
    max_adverse_price: float
    max_favorable_price: float
    candles_analyzed: int


class TimeframeContext(BaseModel):
    role: str
    timeframe: str
    trend: str
    entry_alignment: str
    nearest_support: float | None
    nearest_resistance: float | None
    entry_location: str
    candles_analyzed: int


class ContextObservation(BaseModel):
    category: str
    severity: Literal["positive", "neutral", "caution", "risk"]
    message: str
    evidence: dict


class ScoreComponent(BaseModel):
    label: str
    impact: int
    evidence: dict = Field(default_factory=dict)


class ScoreBreakdown(BaseModel):
    score: int
    components: list[ScoreComponent]


class DecisionScores(BaseModel):
    formula_version: str
    selection: ScoreBreakdown
    management: ScoreBreakdown
    risk: ScoreBreakdown
    overall_score: int
    confidence: Literal["low", "medium", "high"]
    weights: dict[str, float]


class TradePackage(BaseModel):
    trade: TradeInput
    local_timeframe: str
    higher_timeframe: str
    candles_before_entry: int
    candles_after_entry: int
    indicators_at_entry: IndicatorSnapshot
    derived_context: DerivedContext
    management_metrics: ManagementMetrics
    multi_timeframe_context: list[TimeframeContext] = Field(default_factory=list)
    context_summary: list[ContextObservation] = Field(default_factory=list)
    decision_scores: DecisionScores | None = None
    timeframe_candles: dict[str, list[Candle]] = Field(default_factory=dict)
    local_candles: list[Candle]
    higher_timeframe_candles: list[Candle]


class StoredTradePackage(BaseModel):
    id: int
    created_at: datetime
    package: TradePackage


class TradeListItem(BaseModel):
    id: int
    symbol: str
    side: Literal["BUY", "SELL"]
    entry_time: datetime
    exit_time: datetime
    pnl_points: float
    created_at: datetime
    trend: str
    momentum_state: str
    mae_points: float | None = None
    mfe_points: float | None = None
    capture_efficiency: float | None = None


class TradeDetail(BaseModel):
    id: int
    created_at: datetime
    trade: TradeInput
    pnl_points: float
    indicators_at_entry: IndicatorSnapshot
    derived_context: DerivedContext
    management_metrics: ManagementMetrics
    multi_timeframe_context: list[TimeframeContext] = Field(default_factory=list)
    context_summary: list[ContextObservation] = Field(default_factory=list)
    decision_scores: DecisionScores | None = None
