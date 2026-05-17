from datetime import datetime
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database import get_trade_package, init_db, list_trade_packages, save_trade_package
from app.schemas import TradeInput
from app.services.trade_package import build_trade_package


def main() -> None:
    init_db()

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
    saved = save_trade_package(package)
    fetched = get_trade_package(saved.id)
    trade_list = list_trade_packages()

    if fetched is None:
        raise RuntimeError("Saved package could not be fetched")

    print(f"saved_id={saved.id}")
    print(f"stored_packages={len(trade_list)}")
    print(f"trend={fetched.package.derived_context.trend}")
    print(f"momentum_state={fetched.package.derived_context.momentum_state}")
    print(f"mae_points={fetched.package.management_metrics.mae_points}")
    print(f"mfe_points={fetched.package.management_metrics.mfe_points}")
    print(f"capture_efficiency={fetched.package.management_metrics.capture_efficiency}")
    print(f"timeframes={len(fetched.package.multi_timeframe_context)}")
    print(f"context_observations={len(fetched.package.context_summary)}")
    if fetched.package.decision_scores is not None:
        print(f"overall_score={fetched.package.decision_scores.overall_score}")
        print(f"score_confidence={fetched.package.decision_scores.confidence}")


if __name__ == "__main__":
    main()
