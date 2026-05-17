from app.schemas import ContextObservation, DerivedContext, IndicatorSnapshot, ManagementMetrics, TimeframeContext, TradeInput


def build_context_summary(
    trade: TradeInput,
    indicators: IndicatorSnapshot,
    derived_context: DerivedContext,
    management: ManagementMetrics,
    multi_timeframe_context: list[TimeframeContext],
) -> list[ContextObservation]:
    observations: list[ContextObservation] = []
    observations.extend(_trend_observations(trade, multi_timeframe_context))
    observations.extend(_location_observations(trade, multi_timeframe_context))
    observations.extend(_momentum_observations(indicators, derived_context))
    observations.extend(_volume_observations(indicators, derived_context))
    observations.extend(_management_observations(management))
    observations.extend(_risk_plan_observations(trade, management))
    return observations


def _trend_observations(trade: TradeInput, contexts: list[TimeframeContext]) -> list[ContextObservation]:
    aligned = [context for context in contexts if context.entry_alignment == "aligned"]
    against = [context for context in contexts if context.entry_alignment == "against"]

    if aligned and len(aligned) >= max(3, len(contexts) - 1):
        return [
            ContextObservation(
                category="trend",
                severity="positive",
                message=f"Trade aligned with trend across {len(aligned)} of {len(contexts)} tracked timeframes.",
                evidence={
                    "side": trade.side,
                    "aligned_timeframes": [context.timeframe for context in aligned],
                    "against_timeframes": [context.timeframe for context in against],
                },
            )
        ]

    if against:
        return [
            ContextObservation(
                category="trend",
                severity="caution",
                message=f"Trade was against trend on {len(against)} tracked timeframe(s).",
                evidence={
                    "side": trade.side,
                    "against_timeframes": [context.timeframe for context in against],
                    "aligned_timeframes": [context.timeframe for context in aligned],
                },
            )
        ]

    return [
        ContextObservation(
            category="trend",
            severity="neutral",
            message="Trend alignment was unclear across the tracked timeframes.",
            evidence={
                "side": trade.side,
                "timeframes": [context.timeframe for context in contexts],
            },
        )
    ]


def _location_observations(trade: TradeInput, contexts: list[TimeframeContext]) -> list[ContextObservation]:
    observations: list[ContextObservation] = []
    higher_roles = {"very_high", "high", "medium"}
    higher_contexts = [context for context in contexts if context.role in higher_roles]

    resistance_contexts = [
        context for context in higher_contexts if context.entry_location in {"near_resistance", "between_nearby_htf_levels"}
    ]
    support_contexts = [
        context for context in higher_contexts if context.entry_location in {"near_support", "between_nearby_htf_levels"}
    ]

    if trade.side == "BUY" and resistance_contexts:
        observations.append(
            ContextObservation(
                category="location",
                severity="risk",
                message="Long entry was near higher-timeframe resistance.",
                evidence={
                    "timeframes": [context.timeframe for context in resistance_contexts],
                    "nearest_resistance": {
                        context.timeframe: context.nearest_resistance for context in resistance_contexts
                    },
                },
            )
        )
    elif trade.side == "SELL" and support_contexts:
        observations.append(
            ContextObservation(
                category="location",
                severity="risk",
                message="Short entry was near higher-timeframe support.",
                evidence={
                    "timeframes": [context.timeframe for context in support_contexts],
                    "nearest_support": {context.timeframe: context.nearest_support for context in support_contexts},
                },
            )
        )

    return observations


def _momentum_observations(
    indicators: IndicatorSnapshot,
    derived_context: DerivedContext,
) -> list[ContextObservation]:
    if derived_context.momentum_state == "overbought":
        return [
            ContextObservation(
                category="momentum",
                severity="caution",
                message="Execution timeframe momentum was overbought at entry.",
                evidence={"rsi14": indicators.rsi14},
            )
        ]
    if derived_context.momentum_state == "oversold":
        return [
            ContextObservation(
                category="momentum",
                severity="caution",
                message="Execution timeframe momentum was oversold at entry.",
                evidence={"rsi14": indicators.rsi14},
            )
        ]
    if derived_context.momentum_state in {"bullish_momentum", "bearish_momentum"}:
        return [
            ContextObservation(
                category="momentum",
                severity="neutral",
                message=f"Execution timeframe showed {derived_context.momentum_state.replace('_', ' ')} at entry.",
                evidence={"rsi14": indicators.rsi14},
            )
        ]
    return []


def _volume_observations(
    indicators: IndicatorSnapshot,
    derived_context: DerivedContext,
) -> list[ContextObservation]:
    if derived_context.volume_participation in {"weak", "very_weak"}:
        return [
            ContextObservation(
                category="volume",
                severity="caution",
                message="Volume participation was below recent average at entry.",
                evidence={
                    "volume_ratio": indicators.volume_ratio,
                    "volume_participation": derived_context.volume_participation,
                },
            )
        ]
    if derived_context.volume_participation == "strong":
        return [
            ContextObservation(
                category="volume",
                severity="positive",
                message="Volume participation was strong relative to recent average at entry.",
                evidence={
                    "volume_ratio": indicators.volume_ratio,
                    "volume_participation": derived_context.volume_participation,
                },
            )
        ]
    return []


def _management_observations(management: ManagementMetrics) -> list[ContextObservation]:
    if management.capture_efficiency is None:
        return []
    if management.capture_efficiency >= 0.75:
        return [
            ContextObservation(
                category="management",
                severity="positive",
                message="Trade captured most of the favorable move available before exit.",
                evidence={
                    "capture_efficiency": management.capture_efficiency,
                    "captured_points": management.captured_points,
                    "mfe_points": management.mfe_points,
                },
            )
        ]
    if management.capture_efficiency <= 0.35 and management.mfe_points > 0:
        return [
            ContextObservation(
                category="management",
                severity="caution",
                message="Trade captured a small portion of the favorable move available before exit.",
                evidence={
                    "capture_efficiency": management.capture_efficiency,
                    "captured_points": management.captured_points,
                    "mfe_points": management.mfe_points,
                },
            )
        ]
    return [
        ContextObservation(
            category="management",
            severity="neutral",
            message="Trade captured a moderate portion of the favorable move available before exit.",
            evidence={
                "capture_efficiency": management.capture_efficiency,
                "captured_points": management.captured_points,
                "mfe_points": management.mfe_points,
            },
        )
    ]


def _risk_plan_observations(trade: TradeInput, management: ManagementMetrics) -> list[ContextObservation]:
    if trade.stop_loss_price is None:
        return [
            ContextObservation(
                category="risk_plan",
                severity="caution",
                message="No stop-loss price was provided for this trade.",
                evidence={"stop_loss_price": None},
            )
        ]

    planned_risk = abs(trade.entry_price - trade.stop_loss_price)
    if planned_risk == 0:
        return []

    adverse_risk_ratio = management.mae_points / planned_risk
    if adverse_risk_ratio >= 0.8:
        severity = "risk"
        message = "Price moved close to the planned stop-loss during the trade."
    else:
        severity = "positive"
        message = "Price did not deeply threaten the planned stop-loss during the trade."

    return [
        ContextObservation(
            category="risk_plan",
            severity=severity,
            message=message,
            evidence={
                "planned_risk_points": round(planned_risk, 2),
                "mae_points": management.mae_points,
                "adverse_risk_ratio": round(adverse_risk_ratio, 2),
                "stop_loss_price": trade.stop_loss_price,
            },
        )
    ]
