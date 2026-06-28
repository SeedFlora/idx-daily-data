# idx-daily-data

Daily OHLCV snapshots for selected IDX (Indonesia, `.JK`), Tokyo (Japan, `.T`),
and crypto tickers, pulled from Yahoo Finance and committed once per day.
One CSV per ticker under [`data/`](data/).

Re-runs are idempotent: rows are keyed by date, so corrections overwrite the
same day instead of duplicating. Automated via cron on a self-hosted server.
