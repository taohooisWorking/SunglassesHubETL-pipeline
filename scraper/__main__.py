"""
Entry point: scrape both gender catalogs from Sunglass Hut's Algolia API.

    python -m scraper                # load into ClickHouse raw.sunglasshut_products
    python -m scraper --to-file      # save JSON + CSV under data/raw/ instead
"""

import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path

from scraper.extractors.products_api import fetch_all_genders

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scraper")

OUTPUT_DIR = Path("data/raw")


def save_to_file(df) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    json_path = OUTPUT_DIR / f"sunglasshut_products_{timestamp}.json"
    csv_path = OUTPUT_DIR / f"sunglasshut_products_{timestamp}.csv"

    df.to_json(json_path, orient="records", force_ascii=False, indent=2)
    df.to_csv(csv_path, index=False)

    logger.info(f"Saved {len(df)} products to {json_path} and {csv_path}")
    return str(json_path)


def load_to_clickhouse(df) -> int:
    from scraper.loaders.clickhouse_loader import get_client, load_products

    n = load_products(df, get_client())
    logger.info(f"Loaded {n} rows into ClickHouse")
    return n


def run(to_file: bool = False):
    df = fetch_all_genders()
    return save_to_file(df) if to_file else load_to_clickhouse(df)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="python -m scraper", description=__doc__.split("\n\n")[0])
    parser.add_argument("--to-file", action="store_true", help="save JSON + CSV to data/raw/ instead of ClickHouse")
    run(to_file=parser.parse_args().to_file)
