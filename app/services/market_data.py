import csv
from datetime import datetime
from pathlib import Path

from app.schemas import Candle

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "mock"


def load_mock_candles(symbol: str, timeframe: str) -> list[Candle]:
    path = DATA_DIR / f"{symbol.upper()}_{timeframe}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing mock candle data: {path}")

    candles: list[Candle] = []
    with path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            candles.append(
                Candle(
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]),
                )
            )
    return candles


def nearest_candle_index(candles: list[Candle], target: datetime) -> int:
    if not candles:
        raise ValueError("Cannot find an entry candle in an empty candle list")
    return min(range(len(candles)), key=lambda index: abs(candles[index].timestamp - target))


def candle_window(candles: list[Candle], center_index: int, before: int = 20, after: int = 10) -> list[Candle]:
    start = max(center_index - before, 0)
    end = min(center_index + after + 1, len(candles))
    return candles[start:end]
