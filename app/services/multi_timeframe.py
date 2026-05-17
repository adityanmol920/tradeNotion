from datetime import timedelta

from app.schemas import Candle, TimeframeContext, TradeInput
from app.services.market_data import load_mock_candles


def timeframe_map(trade: TradeInput) -> dict[str, str]:
    return {
        "very_high": trade.very_high_timeframe,
        "high": trade.high_timeframe,
        "medium": trade.medium_timeframe,
        "low": trade.low_timeframe,
        "execution": trade.execution_timeframe,
    }


def load_timeframe_candles(trade: TradeInput) -> dict[str, list[Candle]]:
    return {role: load_mock_candles(trade.symbol, timeframe) for role, timeframe in timeframe_map(trade).items()}


def derive_multi_timeframe_context(
    trade: TradeInput,
    candles_by_role: dict[str, list[Candle]],
) -> list[TimeframeContext]:
    timeframes = timeframe_map(trade)
    return [
        _derive_timeframe_context(
            role=role,
            timeframe=timeframes[role],
            candles=candles,
            trade=trade,
        )
        for role, candles in candles_by_role.items()
    ]


def _derive_timeframe_context(
    role: str,
    timeframe: str,
    candles: list[Candle],
    trade: TradeInput,
) -> TimeframeContext:
    duration = _timeframe_duration(timeframe)
    reference_candles = [
        candle
        for candle in candles
        if duration is not None and candle.timestamp + duration <= trade.entry_time
    ]
    if not reference_candles:
        reference_candles = [candle for candle in candles if candle.timestamp <= trade.entry_time]
    if not reference_candles:
        reference_candles = candles[:1]

    trend = _trend(reference_candles)
    nearest_support = _nearest_support(reference_candles, trade.entry_price)
    nearest_resistance = _nearest_resistance(reference_candles, trade.entry_price)
    entry_location = _entry_location(trade.entry_price, nearest_support, nearest_resistance)
    entry_alignment = _entry_alignment(trade.side, trend)

    return TimeframeContext(
        role=role,
        timeframe=timeframe,
        trend=trend,
        entry_alignment=entry_alignment,
        nearest_support=nearest_support,
        nearest_resistance=nearest_resistance,
        entry_location=entry_location,
        candles_analyzed=len(reference_candles),
    )


def _trend(candles: list[Candle]) -> str:
    if len(candles) < 2:
        return "insufficient_data"

    first_close = candles[0].close
    last_close = candles[-1].close
    move = last_close - first_close
    threshold = max(first_close * 0.001, 1)

    if move > threshold:
        return "bullish"
    if move < -threshold:
        return "bearish"
    return "neutral"


def _nearest_support(candles: list[Candle], entry_price: float) -> float | None:
    supports = [candle.low for candle in candles if candle.low <= entry_price]
    return round(max(supports), 2) if supports else None


def _nearest_resistance(candles: list[Candle], entry_price: float) -> float | None:
    resistances = [candle.high for candle in candles if candle.high >= entry_price]
    return round(min(resistances), 2) if resistances else None


def _entry_location(
    entry_price: float,
    nearest_support: float | None,
    nearest_resistance: float | None,
) -> str:
    support_distance = _distance_ratio(entry_price, nearest_support)
    resistance_distance = _distance_ratio(entry_price, nearest_resistance)

    near_support = support_distance is not None and support_distance <= 0.0025
    near_resistance = resistance_distance is not None and resistance_distance <= 0.0025

    if near_support and near_resistance:
        return "between_nearby_htf_levels"
    if near_resistance:
        return "near_resistance"
    if near_support:
        return "near_support"
    return "between_levels"


def _entry_alignment(side: str, trend: str) -> str:
    if trend not in {"bullish", "bearish"}:
        return "unclear"
    if side == "BUY" and trend == "bullish":
        return "aligned"
    if side == "SELL" and trend == "bearish":
        return "aligned"
    return "against"


def _distance_ratio(entry_price: float, level: float | None) -> float | None:
    if level is None:
        return None
    return abs(entry_price - level) / entry_price


def _timeframe_duration(timeframe: str) -> timedelta | None:
    unit = timeframe[-1]
    value = timeframe[:-1]
    if not value.isdigit():
        return None

    amount = int(value)
    if unit == "m":
        return timedelta(minutes=amount)
    if unit == "h":
        return timedelta(hours=amount)
    if unit == "d":
        return timedelta(days=amount)
    return None
