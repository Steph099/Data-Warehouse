"""CLI entry point for ingestion.

Examples:
    python -m acme_dwh.ingestion.run_ingestion BTCUSD ETHUSD
    python -m acme_dwh.ingestion.run_ingestion BTCUSD --start 2020-01-01 --end 2021-01-01
    python -m acme_dwh.ingestion.run_ingestion BTCUSD --provider nasdaq_data_link
    python -m acme_dwh.ingestion.run_ingestion BTCUSD --provider both
"""
from __future__ import annotations

import argparse
import logging
from datetime import date

from acme_dwh.config import get_settings
from acme_dwh.ingestion.load import Ingestor
from acme_dwh.ingestion.providers import build_extractor, resolve_providers

log = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = get_settings()

    parser = argparse.ArgumentParser(description="Ingest financial time-series into the Acme DWH.")
    parser.add_argument("symbols", nargs="+", help="provider symbols, e.g. BTCUSD ETHUSD")
    parser.add_argument(
        "--provider",
        default=settings.ingest_provider,
        help="bitfinex | nasdaq_data_link | both (or a comma-separated list)",
    )
    parser.add_argument("--start", type=date.fromisoformat, default=None, help="YYYY-MM-DD (inclusive)")
    parser.add_argument("--end", type=date.fromisoformat, default=None, help="YYYY-MM-DD (exclusive)")
    args = parser.parse_args(argv)

    provider_names = resolve_providers(args.provider, settings)
    failures = 0
    for name in provider_names:
        try:
            extractor = build_extractor(name, settings)
        except Exception as exc:  # noqa: BLE001 - report and keep going to other providers
            failures += 1
            log.error("Provider %s unavailable, skipping: %s", name, exc)
            continue
        try:
            ingestor = Ingestor(extractor)
            for symbol in args.symbols:
                stats = ingestor.ingest_symbol(symbol, args.start, args.end)
                print(stats)
        except Exception as exc:  # noqa: BLE001 - one provider failing must not abort the rest
            failures += 1
            log.error("Ingestion via %s failed: %s", name, exc)
        finally:
            close = getattr(extractor, "close", None)
            if callable(close):
                close()

    if failures and failures == len(provider_names):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
