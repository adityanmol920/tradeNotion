from app.schemas import (
    ContextObservation,
    DecisionScores,
    DerivedContext,
    ManagementMetrics,
    ScoreBreakdown,
    ScoreComponent,
    TimeframeContext,
    TradeInput,
)

FORMULA_VERSION = "decision_scoring_v1"
BASE_SCORE = 50
OVERALL_WEIGHTS = {
    "selection": 0.45,
    "management": 0.35,
    "risk": 0.20,
}


def build_decision_scores(
    trade: TradeInput,
    derived_context: DerivedContext,
    management: ManagementMetrics,
    multi_timeframe_context: list[TimeframeContext],
    context_summary: list[ContextObservation],
) -> DecisionScores:
    selection = _selection_score(derived_context, multi_timeframe_context, context_summary)
    management_score = _management_score(trade, management)
    risk = _risk_score(trade)
    overall_score = _overall_score(selection.score, management_score.score, risk.score)

    return DecisionScores(
        formula_version=FORMULA_VERSION,
        selection=selection,
        management=management_score,
        risk=risk,
        overall_score=overall_score,
        confidence=_confidence(trade, management, multi_timeframe_context),
        weights=OVERALL_WEIGHTS,
    )


def _selection_score(
    derived_context: DerivedContext,
    contexts: list[TimeframeContext],
    context_summary: list[ContextObservation],
) -> ScoreBreakdown:
    components: list[ScoreComponent] = []

    aligned_count = len([context for context in contexts if context.entry_alignment == "aligned"])
    against_major = [
        context
        for context in contexts
        if context.role in {"very_high", "high", "medium"} and context.entry_alignment == "against"
    ]

    if aligned_count == len(contexts) and contexts:
        components.append(_component("Trend aligned across all tracked timeframes", 25, {"aligned_count": aligned_count}))
    elif aligned_count >= 4:
        components.append(_component("Trend aligned across most tracked timeframes", 18, {"aligned_count": aligned_count}))
    elif aligned_count >= 3:
        components.append(_component("Trend aligned across several tracked timeframes", 10, {"aligned_count": aligned_count}))

    for context in against_major:
        components.append(
            _component(
                f"Trade was against {context.timeframe} trend",
                -10,
                {"role": context.role, "timeframe": context.timeframe, "trend": context.trend},
            )
        )

    if derived_context.volume_participation == "strong":
        components.append(_component("Strong volume participation", 10, {"volume_participation": "strong"}))
    elif derived_context.volume_participation == "healthy":
        components.append(_component("Healthy volume participation", 5, {"volume_participation": "healthy"}))
    elif derived_context.volume_participation == "weak":
        components.append(_component("Weak volume participation", -8, {"volume_participation": "weak"}))
    elif derived_context.volume_participation == "very_weak":
        components.append(_component("Very weak volume participation", -15, {"volume_participation": "very_weak"}))

    if derived_context.momentum_state in {"overbought", "oversold"}:
        components.append(
            _component(
                f"Execution timeframe momentum was {derived_context.momentum_state}",
                -10,
                {"momentum_state": derived_context.momentum_state},
            )
        )

    location_risks = [observation for observation in context_summary if observation.category == "location"]
    for observation in location_risks:
        components.append(_component(observation.message, -15, observation.evidence))

    return _breakdown(components)


def _management_score(trade: TradeInput, management: ManagementMetrics) -> ScoreBreakdown:
    components: list[ScoreComponent] = []

    if management.capture_efficiency is not None:
        if management.capture_efficiency >= 0.75:
            components.append(
                _component(
                    "Captured most of the favorable move",
                    25,
                    {"capture_efficiency": management.capture_efficiency},
                )
            )
        elif management.capture_efficiency >= 0.50:
            components.append(
                _component(
                    "Captured a meaningful portion of the favorable move",
                    15,
                    {"capture_efficiency": management.capture_efficiency},
                )
            )
        elif management.capture_efficiency >= 0.25:
            components.append(
                _component(
                    "Captured a limited portion of the favorable move",
                    5,
                    {"capture_efficiency": management.capture_efficiency},
                )
            )
        else:
            components.append(
                _component(
                    "Captured very little of the favorable move",
                    -10,
                    {"capture_efficiency": management.capture_efficiency},
                )
            )

    if trade.stop_loss_price is not None:
        planned_risk = abs(trade.entry_price - trade.stop_loss_price)
        if planned_risk > 0:
            adverse_risk_ratio = management.mae_points / planned_risk
            if adverse_risk_ratio < 0.30:
                impact = 15
                label = "Price barely moved against planned risk"
            elif adverse_risk_ratio < 0.70:
                impact = 5
                label = "Price used a moderate portion of planned risk"
            elif adverse_risk_ratio <= 1:
                impact = -5
                label = "Price moved close to planned stop-loss"
            else:
                impact = -25
                label = "Price exceeded planned stop-loss distance"
            components.append(
                _component(
                    label,
                    impact,
                    {
                        "mae_points": management.mae_points,
                        "planned_risk_points": round(planned_risk, 2),
                        "adverse_risk_ratio": round(adverse_risk_ratio, 2),
                    },
                )
            )

    return _breakdown(components)


def _risk_score(trade: TradeInput) -> ScoreBreakdown:
    components: list[ScoreComponent] = []

    if trade.stop_loss_price is not None:
        components.append(_component("Stop-loss was provided", 15, {"stop_loss_price": trade.stop_loss_price}))
    else:
        components.append(_component("Stop-loss was missing", -25))

    if trade.take_profit_price is not None:
        components.append(_component("Take-profit was provided", 10, {"take_profit_price": trade.take_profit_price}))
    else:
        components.append(_component("Take-profit was missing", -10))

    if trade.stop_loss_price is not None and trade.take_profit_price is not None:
        risk = abs(trade.entry_price - trade.stop_loss_price)
        reward = abs(trade.take_profit_price - trade.entry_price)
        if risk > 0:
            reward_risk = reward / risk
            if reward_risk >= 2:
                impact = 20
                label = "Planned reward/risk was at least 2.0"
            elif reward_risk >= 1.5:
                impact = 12
                label = "Planned reward/risk was between 1.5 and 2.0"
            elif reward_risk >= 1:
                impact = 5
                label = "Planned reward/risk was at least 1.0"
            else:
                impact = -15
                label = "Planned reward/risk was below 1.0"
            components.append(
                _component(
                    label,
                    impact,
                    {
                        "planned_risk_points": round(risk, 2),
                        "planned_reward_points": round(reward, 2),
                        "reward_risk": round(reward_risk, 2),
                    },
                )
            )

    return _breakdown(components)


def _confidence(
    trade: TradeInput,
    management: ManagementMetrics,
    contexts: list[TimeframeContext],
) -> str:
    has_risk_plan = trade.stop_loss_price is not None and trade.take_profit_price is not None
    has_management = management.mfe_points is not None and management.mae_points is not None
    has_all_timeframes = len(contexts) >= 5 and all(context.candles_analyzed > 0 for context in contexts)

    if has_risk_plan and has_management and has_all_timeframes:
        return "high"
    if has_management and len(contexts) >= 3:
        return "medium"
    return "low"


def _overall_score(selection: int, management: int, risk: int) -> int:
    score = (
        selection * OVERALL_WEIGHTS["selection"]
        + management * OVERALL_WEIGHTS["management"]
        + risk * OVERALL_WEIGHTS["risk"]
    )
    return _clamp(round(score))


def _breakdown(components: list[ScoreComponent]) -> ScoreBreakdown:
    return ScoreBreakdown(score=_clamp(BASE_SCORE + sum(component.impact for component in components)), components=components)


def _component(label: str, impact: int, evidence: dict | None = None) -> ScoreComponent:
    return ScoreComponent(label=label, impact=impact, evidence=evidence or {})


def _clamp(score: int) -> int:
    return max(0, min(100, score))
