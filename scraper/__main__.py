"""
Entry point for the Sunglass Hut scraper.

    python -m scraper extract                 # Algolia -> MinIO raw run, prints its prefix
    python -m scraper load [--run PREFIX]     # MinIO run -> ClickHouse (default: latest run)
    python -m scraper load --date 2026-09-27  # latest run of that day
    python -m scraper run                     # extract + load (default when no command given)
"""

import argparse
import logging
from datetime import datetime, timezone
from typing import Optional

from scraper.config import ALGOLIA_INDEX_NAME
from scraper.extractors.products_api import build_products, fetch_raw_hits
from scraper.storage import raw_store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scraper")


def extract() -> str:
    scraped_at = datetime.now(timezone.utc)
    raw = fetch_raw_hits()
    return raw_store.save_run(raw, scraped_at, ALGOLIA_INDEX_NAME)


def load(run_prefix: Optional[str] = None, date: Optional[str] = None) -> int:
    from scraper.loaders.clickhouse_loader import get_client, load_products

    run_prefix = run_prefix or raw_store.latest_run(date)
    raw, scraped_at = raw_store.load_run(run_prefix)
    df = build_products(raw, scraped_at)

    n = load_products(df, get_client())
    logger.info(f"Loaded {n} rows from {run_prefix} into ClickHouse")
    return n


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m scraper", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("extract", help="scrape Algolia and store the raw run in MinIO")
    load_p = sub.add_parser("load", help="transform a raw MinIO run and load it into ClickHouse")
    group = load_p.add_mutually_exclusive_group()
    group.add_argument("--run", help="run prefix, e.g. products/dt=2026-09-27/run=20260927T211500Z")
    group.add_argument("--date", help="load the latest run of this YYYY-MM-DD day")
    sub.add_parser("run", help="extract + load")
    args = parser.parse_args()

    if args.command == "extract":
        print(extract())
    elif args.command == "load":
        load(args.run, args.date)
    else:
        load(extract())


if __name__ == "__main__":
    main()
