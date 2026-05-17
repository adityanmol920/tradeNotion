import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.schemas import (
    Candle,
    ContextObservation,
    DerivedContext,
    IndicatorSnapshot,
    ManagementMetrics,
    StoredTradePackage,
    TimeframeContext,
    TradeDetail,
    TradeInput,
    TradeListItem,
    TradePackage,
)

DATABASE_PATH = Path(__file__).resolve().parents[1] / "data" / "tradenotion.db"


def get_connection() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS trade_packages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                asset_class TEXT,
                exchange TEXT,
                currency TEXT,
                timezone TEXT,
                side TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL NOT NULL,
                stop_loss_price REAL,
                take_profit_price REAL,
                quantity INTEGER NOT NULL,
                entry_time TEXT NOT NULL,
                exit_time TEXT NOT NULL,
                pnl_points REAL NOT NULL,
                trend TEXT NOT NULL,
                momentum_state TEXT NOT NULL,
                volume_participation TEXT NOT NULL,
                price_vs_vwap TEXT NOT NULL,
                package_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        _ensure_column(connection, "trade_packages", "mae_points", "REAL")
        _ensure_column(connection, "trade_packages", "mfe_points", "REAL")
        _ensure_column(connection, "trade_packages", "capture_efficiency", "REAL")
        _ensure_column(connection, "trade_packages", "stop_loss_price", "REAL")
        _ensure_column(connection, "trade_packages", "take_profit_price", "REAL")
        _ensure_column(connection, "trade_packages", "asset_class", "TEXT")
        _ensure_column(connection, "trade_packages", "exchange", "TEXT")
        _ensure_column(connection, "trade_packages", "currency", "TEXT")
        _ensure_column(connection, "trade_packages", "timezone", "TEXT")


def save_trade_package(package: TradePackage) -> StoredTradePackage:
    trade = package.trade
    context = package.derived_context
    management = package.management_metrics
    created_at = datetime.now(UTC)
    pnl_points = trade.exit_price - trade.entry_price if trade.side == "BUY" else trade.entry_price - trade.exit_price
    package_json = package.model_dump_json()

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO trade_packages (
                symbol,
                asset_class,
                exchange,
                currency,
                timezone,
                side,
                entry_price,
                exit_price,
                stop_loss_price,
                take_profit_price,
                quantity,
                entry_time,
                exit_time,
                pnl_points,
                trend,
                momentum_state,
                volume_participation,
                price_vs_vwap,
                mae_points,
                mfe_points,
                capture_efficiency,
                package_json,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trade.symbol,
                trade.asset_class,
                trade.exchange,
                trade.currency,
                trade.timezone,
                trade.side,
                trade.entry_price,
                trade.exit_price,
                trade.stop_loss_price,
                trade.take_profit_price,
                trade.quantity,
                trade.entry_time.isoformat(),
                trade.exit_time.isoformat(),
                pnl_points,
                context.trend,
                context.momentum_state,
                context.volume_participation,
                context.price_vs_vwap,
                management.mae_points,
                management.mfe_points,
                management.capture_efficiency,
                package_json,
                created_at.isoformat(),
            ),
        )
        trade_package_id = int(cursor.lastrowid)

    return StoredTradePackage(id=trade_package_id, created_at=created_at, package=package)


def list_trade_packages() -> list[TradeListItem]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                symbol,
                side,
                entry_time,
                exit_time,
                pnl_points,
                created_at,
                trend,
                momentum_state,
                mae_points,
                mfe_points,
                capture_efficiency
            FROM trade_packages
            ORDER BY created_at DESC
            """
        ).fetchall()

    return [_trade_list_item_from_row(row) for row in rows]


def get_trade_package(trade_package_id: int) -> StoredTradePackage | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, package_json, created_at
            FROM trade_packages
            WHERE id = ?
            """,
            (trade_package_id,),
        ).fetchone()

    if row is None:
        return None

    package_data: dict[str, Any] = json.loads(row["package_json"])
    if "management_metrics" not in package_data:
        from app.services.management import calculate_management_metrics

        trade = TradeInput.model_validate(package_data["trade"])
        candles = [Candle.model_validate(candle) for candle in package_data["local_candles"]]
        package_data["management_metrics"] = calculate_management_metrics(trade, candles).model_dump()
    if "context_summary" not in package_data:
        from app.services.context_summary import build_context_summary

        trade = TradeInput.model_validate(package_data["trade"])
        package_data["context_summary"] = [
            observation.model_dump()
            for observation in build_context_summary(
                trade=trade,
                indicators=IndicatorSnapshot.model_validate(package_data["indicators_at_entry"]),
                derived_context=DerivedContext.model_validate(package_data["derived_context"]),
                management=ManagementMetrics.model_validate(package_data["management_metrics"]),
                multi_timeframe_context=[
                    TimeframeContext.model_validate(context)
                    for context in package_data.get("multi_timeframe_context", [])
                ],
            )
        ]
    if "decision_scores" not in package_data:
        from app.services.decision_scoring import build_decision_scores

        trade = TradeInput.model_validate(package_data["trade"])
        package_data["decision_scores"] = build_decision_scores(
            trade=trade,
            derived_context=DerivedContext.model_validate(package_data["derived_context"]),
            management=ManagementMetrics.model_validate(package_data["management_metrics"]),
            multi_timeframe_context=[
                TimeframeContext.model_validate(context)
                for context in package_data.get("multi_timeframe_context", [])
            ],
            context_summary=[
                ContextObservation.model_validate(observation)
                for observation in package_data.get("context_summary", [])
            ],
        ).model_dump()

    return StoredTradePackage(
        id=row["id"],
        created_at=datetime.fromisoformat(row["created_at"]),
        package=TradePackage.model_validate(package_data),
    )


def get_trade_detail(trade_package_id: int) -> TradeDetail | None:
    stored_package = get_trade_package(trade_package_id)
    if stored_package is None:
        return None

    package = stored_package.package
    trade = package.trade
    pnl_points = trade.exit_price - trade.entry_price if trade.side == "BUY" else trade.entry_price - trade.exit_price

    return TradeDetail(
        id=stored_package.id,
        created_at=stored_package.created_at,
        trade=trade,
        pnl_points=round(pnl_points, 2),
        indicators_at_entry=package.indicators_at_entry,
        derived_context=package.derived_context,
        management_metrics=package.management_metrics,
        multi_timeframe_context=package.multi_timeframe_context,
        context_summary=package.context_summary,
        decision_scores=package.decision_scores,
    )


def _trade_list_item_from_row(row: sqlite3.Row) -> TradeListItem:
    return TradeListItem(
        id=row["id"],
        symbol=row["symbol"],
        side=row["side"],
        entry_time=datetime.fromisoformat(row["entry_time"]),
        exit_time=datetime.fromisoformat(row["exit_time"]),
        pnl_points=row["pnl_points"],
        created_at=datetime.fromisoformat(row["created_at"]),
        trend=row["trend"],
        momentum_state=row["momentum_state"],
        mae_points=row["mae_points"],
        mfe_points=row["mfe_points"],
        capture_efficiency=row["capture_efficiency"],
    )


def _ensure_column(connection: sqlite3.Connection, table: str, column: str, column_type: str) -> None:
    columns = connection.execute(f"PRAGMA table_info({table})").fetchall()
    if column not in {row["name"] for row in columns}:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
