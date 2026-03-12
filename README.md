# ArbScan Pro

Production-focused Flask app for discovering quasi-guaranteed arbitrage edges between sportsbooks and prediction markets.

## What changed
- Responsive modern UI with a config panel.
- Runtime config endpoints to view/update bankroll, min gross margin %, and refresh interval.
- Masked API-key visibility for operational awareness without exposing full secrets.

## API endpoints
- `GET /api/opportunities`: Returns opportunities filtered by `min_gross_margin_pct`, plus meta analytics.
- `GET /api/config`: Returns runtime config + masked keys (`ODDS_API_KEY`, `POLYMARKET_API_KEY`).
- `POST /api/config`: Updates runtime config (`bankroll`, `min_gross_margin_pct`, `refresh_interval_seconds`).

## API coverage
- The Odds API (`/v4/sports/{sport}/odds`)
- Polymarket Gamma (`/events`)
- ESPN Scoreboard API (coverage sanity)
- TheSportsDB (coverage sanity)

## Run locally
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Environment variables
- `ODDS_API_KEY`
- `POLYMARKET_API_KEY`
- `SPORT` (default `soccer_epl`)
- `DEFAULT_BANKROLL` (default `1000`)
- `MIN_GROSS_MARGIN_PCT` (default `0.5`)
- `REFRESH_INTERVAL_SECONDS` (default `30`)
- `PORT` (default `8000`)
