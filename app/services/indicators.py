from app.schemas import Candle, IndicatorSnapshot


def _ema(values: list[float], period: int) -> list[float | None]:
    if not values:
        return []

    multiplier = 2 / (period + 1)
    output: list[float | None] = []
    current: float | None = None

    for index, value in enumerate(values):
        if index + 1 < period:
            output.append(None)
            continue
        if index + 1 == period:
            current = sum(values[:period]) / period
        else:
            current = (value - current) * multiplier + current
        output.append(current)

    return output


def _rsi(values: list[float], period: int = 14) -> list[float | None]:
    if len(values) <= period:
        return [None for _ in values]

    output: list[float | None] = [None for _ in values]
    gains: list[float] = []
    losses: list[float] = []

    for index in range(1, period + 1):
        change = values[index] - values[index - 1]
        gains.append(max(change, 0))
        losses.append(abs(min(change, 0)))

    average_gain = sum(gains) / period
    average_loss = sum(losses) / period
    output[period] = _rsi_value(average_gain, average_loss)

    for index in range(period + 1, len(values)):
        change = values[index] - values[index - 1]
        gain = max(change, 0)
        loss = abs(min(change, 0))
        average_gain = ((average_gain * (period - 1)) + gain) / period
        average_loss = ((average_loss * (period - 1)) + loss) / period
        output[index] = _rsi_value(average_gain, average_loss)

    return output


def _rsi_value(average_gain: float, average_loss: float) -> float:
    if average_loss == 0:
        return 100.0
    relative_strength = average_gain / average_loss
    return 100 - (100 / (1 + relative_strength))


def _vwap(candles: list[Candle]) -> list[float | None]:
    output: list[float | None] = []
    cumulative_price_volume = 0.0
    cumulative_volume = 0.0

    for candle in candles:
        typical_price = (candle.high + candle.low + candle.close) / 3
        cumulative_price_volume += typical_price * candle.volume
        cumulative_volume += candle.volume
        output.append(cumulative_price_volume / cumulative_volume if cumulative_volume else None)

    return output


def _rolling_average(values: list[float], period: int) -> list[float | None]:
    output: list[float | None] = []
    for index in range(len(values)):
        if index + 1 < period:
            output.append(None)
        else:
            window = values[index + 1 - period : index + 1]
            output.append(sum(window) / period)
    return output


def _round(value: float | None) -> float | None:
    return round(value, 2) if value is not None else None


def snapshot_at(candles: list[Candle], index: int) -> IndicatorSnapshot:
    closes = [candle.close for candle in candles]
    volumes = [candle.volume for candle in candles]

    ema20 = _ema(closes, 20)
    ema50 = _ema(closes, 50)
    rsi14 = _rsi(closes, 14)
    vwap = _vwap(candles)
    volume_average20 = _rolling_average(volumes, 20)

    average_volume = volume_average20[index]
    volume_ratio = volumes[index] / average_volume if average_volume else None

    return IndicatorSnapshot(
        ema20=_round(ema20[index]),
        ema50=_round(ema50[index]),
        rsi14=_round(rsi14[index]),
        vwap=_round(vwap[index]),
        volume_average20=_round(average_volume),
        volume_ratio=_round(volume_ratio),
    )
