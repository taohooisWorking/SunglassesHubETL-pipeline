"""
Entry point: run `python -m scraper` to scrape both categories
and save the result as JSON + CSV under data/raw/.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

from scraper.extractors.products_api import fetch_all_genders

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scraper")

OUTPUT_DIR = Path("data/raw")


def run():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = fetch_all_genders()

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    json_path = OUTPUT_DIR / f"sunglasshut_products_{timestamp}.json"
    csv_path = OUTPUT_DIR / f"sunglasshut_products_{timestamp}.csv"

    df.to_json(json_path, orient="records", force_ascii=False, indent=2)
    df.to_csv(csv_path, index=False)

    logger.info(f"Saved {len(df)} products to {json_path} and {csv_path}")
    return str(json_path)


if __name__ == "__main__":
    run()