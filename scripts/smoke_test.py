from datetime import datetime
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.schemas import TradeInput
from app.services.trade_package import build_trade_package


def main() -> None:
    trade = TradeInput(
        symbol="NIFTY",
        side="BUY",
        entry_price=22550,
        exit_price=22582,
        stop_loss_price=22530,
        take_profit_price=22590,
        quantity=50,
        entry_time=datetime.fromisoformat("2026-05-07T13:40:00+05:30"),
        exit_time=datetime.fromisoformat("2026-05-07T14:05:00+05:30"),
        notes="Strategy: Breakout, Emotion: FOMO",
    )
    package = build_trade_package(trade)
    print(package.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
