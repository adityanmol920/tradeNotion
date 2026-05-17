from app.schemas import Candle, ManagementMetrics, TradeInput


def calculate_management_metrics(trade: TradeInput, candles: list[Candle]) -> ManagementMetrics:
    trade_candles = [candle for candle in candles if trade.entry_time <= candle.timestamp <= trade.exit_time]
    if not trade_candles:
        trade_candles = [min(candles, key=lambda candle: abs(candle.timestamp - trade.entry_time))]

    if trade.side == "BUY":
        max_favorable_price = max(candle.high for candle in trade_candles)
        max_adverse_price = min(candle.low for candle in trade_candles)
        mfe_points = max_favorable_price - trade.entry_price
        mae_points = trade.entry_price - max_adverse_price
        captured_points = trade.exit_price - trade.entry_price
    else:
        max_favorable_price = min(candle.low for candle in trade_candles)
        max_adverse_price = max(candle.high for candle in trade_candles)
        mfe_points = trade.entry_price - max_favorable_price
        mae_points = max_adverse_price - trade.entry_price
        captured_points = trade.entry_price - trade.exit_price

    mfe_points = max(mfe_points, 0)
    mae_points = max(mae_points, 0)
    capture_efficiency = captured_points / mfe_points if mfe_points > 0 else None

    return ManagementMetrics(
        mae_points=round(mae_points, 2),
        mfe_points=round(mfe_points, 2),
        captured_points=round(captured_points, 2),
        capture_efficiency=round(capture_efficiency, 2) if capture_efficiency is not None else None,
        max_adverse_price=round(max_adverse_price, 2),
        max_favorable_price=round(max_favorable_price, 2),
        candles_analyzed=len(trade_candles),
    )
