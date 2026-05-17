# tradeNotion

## Description
tradeNotion is an AI-powered trade review and learning platform. The first milestone is a deterministic backend pipeline that ingests a completed trade, reconstructs nearby market candles from mock data, computes indicators, and automatically derives market context.
The architecture is market-agnostic and should support global instruments such as indices, equities, crypto, forex, commodities, futures, and options.

## Features
- Mock/manual trade ingestion
- Asset metadata for global markets: asset class, exchange, currency, and timezone
- Optional stop-loss and take-profit levels on each trade
- Local and higher-timeframe mock candle reconstruction
- Multi-timeframe context across 1d, 4h, 1h, 15m, and execution timeframe
- Indicator snapshot at entry: EMA20, EMA50, RSI14, VWAP, volume average, volume ratio
- Automatic derived context such as trend, momentum state, volume participation, and price vs VWAP
- Deterministic context summary with evidence-backed observations
- Deterministic decision scoring v1 with transparent score components
- Trade management metrics: MAE, MFE, captured points, and capture efficiency

## Installation
1. Clone the repository.
2. Install Python 3.11 or later.
3. Create a virtual environment: `python -m venv .venv`
4. Activate it: `.venv\Scripts\Activate.ps1`
5. Install dependencies: `pip install -r requirements.txt`

## Usage
Run the backend:

```powershell
uvicorn app.main:app --reload
```

Generate a mock trade package without starting the API:

```powershell
python .\scripts\smoke_test.py
```

The current API exposes:

- `GET /health`
- `POST /trade-packages`
- `GET /trade-packages`
- `GET /trade-packages/{trade_package_id}`
- `GET /trades`
- `GET /trades/{trade_package_id}`

Run the persistence smoke test:

```powershell
python .\scripts\persistence_smoke_test.py
```

## Contributing
[Guidelines]

## License
[License info]


Testing preprodV1
