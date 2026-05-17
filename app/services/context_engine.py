from app.schemas import Candle, DerivedContext, IndicatorSnapshot


def derive_context(entry_candle: Candle, indicators: IndicatorSnapshot) -> DerivedContext:
    trend = _trend(indicators)
    momentum_state = _momentum(indicators)
    volume_participation = _volume_participation(indicators)
    price_vs_vwap = _price_vs_vwap(entry_candle, indicators)

    return DerivedContext(
        trend=trend,
        momentum_state=momentum_state,
        volume_participation=volume_participation,
        price_vs_vwap=price_vs_vwap,
    )


def _trend(indicators: IndicatorSnapshot) -> str:
    if indicators.ema20 is None or indicators.ema50 is None:
        return "insufficient_data"
    if indicators.ema20 > indicators.ema50:
        return "bullish"
    if indicators.ema20 < indicators.ema50:
        return "bearish"
    return "neutral"


def _momentum(indicators: IndicatorSnapshot) -> str:
    if indicators.rsi14 is None:
        return "insufficient_data"
    if indicators.rsi14 >= 70:
        return "overbought"
    if indicators.rsi14 <= 30:
        return "oversold"
    if indicators.rsi14 >= 55:
        return "bullish_momentum"
    if indicators.rsi14 <= 45:
        return "bearish_momentum"
    return "neutral"


def _volume_participation(indicators: IndicatorSnapshot) -> str:
    if indicators.volume_ratio is None:
        return "insufficient_data"
    if indicators.volume_ratio >= 1.5:
        return "strong"
    if indicators.volume_ratio >= 1.0:
        return "healthy"
    if indicators.volume_ratio >= 0.7:
        return "weak"
    return "very_weak"


def _price_vs_vwap(entry_candle: Candle, indicators: IndicatorSnapshot) -> str:
    if indicators.vwap is None:
        return "insufficient_data"
    if entry_candle.close > indicators.vwap:
        return "above_vwap"
    if entry_candle.close < indicators.vwap:
        return "below_vwap"
    return "at_vwap"
