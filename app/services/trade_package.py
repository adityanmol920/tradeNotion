from app.schemas import TradeInput, TradePackage
from app.services.context_engine import derive_context
from app.services.context_summary import build_context_summary
from app.services.decision_scoring import build_decision_scores
from app.services.indicators import snapshot_at
from app.services.management import calculate_management_metrics
from app.services.market_data import candle_window, nearest_candle_index
from app.services.multi_timeframe import derive_multi_timeframe_context, load_timeframe_candles


def build_trade_package(trade: TradeInput) -> TradePackage:
    timeframe_candles = load_timeframe_candles(trade)
    local_candles = timeframe_candles["execution"]
    higher_timeframe_candles = timeframe_candles["medium"]

    entry_index = nearest_candle_index(local_candles, trade.entry_time)
    entry_candle = local_candles[entry_index]
    indicators = snapshot_at(local_candles, entry_index)
    derived_context = derive_context(entry_candle, indicators)
    management_metrics = calculate_management_metrics(trade, local_candles)
    multi_timeframe_context = derive_multi_timeframe_context(trade, timeframe_candles)
    context_summary = build_context_summary(
        trade=trade,
        indicators=indicators,
        derived_context=derived_context,
        management=management_metrics,
        multi_timeframe_context=multi_timeframe_context,
    )
    decision_scores = build_decision_scores(
        trade=trade,
        derived_context=derived_context,
        management=management_metrics,
        multi_timeframe_context=multi_timeframe_context,
        context_summary=context_summary,
    )

    before = 20
    after = 10

    return TradePackage(
        trade=trade,
        local_timeframe=trade.execution_timeframe,
        higher_timeframe=trade.higher_timeframe,
        candles_before_entry=min(before, entry_index),
        candles_after_entry=min(after, len(local_candles) - entry_index - 1),
        indicators_at_entry=indicators,
        derived_context=derived_context,
        management_metrics=management_metrics,
        multi_timeframe_context=multi_timeframe_context,
        context_summary=context_summary,
        decision_scores=decision_scores,
        timeframe_candles=timeframe_candles,
        local_candles=candle_window(local_candles, entry_index, before=before, after=after),
        higher_timeframe_candles=higher_timeframe_candles,
    )
