#!/usr/bin/env python3
"""
scraper.main
Main entry point for the Sunglass Hut SEA Scraper.
Supports extracting Stores, Brands, and Products to CSV & JSON formats.

Usage:
    # Run via module
    python -m scraper --type stores --country all --output-format all

    # Or run script directly
    python scraper/main.py --type all
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add project root to sys.path so imports work seamlessly regardless of how the script is called
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from scraper.extractors.stores import scrape_stores
from scraper.extractors.brands import scrape_brands
from scraper.extractors.products import scrape_products
from scraper.utils import export_data

DEFAULT_COUNTRIES = ["th", "sg", "my", "id"]
BASE_URL = "https://sea.sunglasshut.com"


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Sunglass Hut SEA Web Scraper (Stores, Brands, Products) with CSV/JSON export."
    )
    parser.add_argument(
        "--type", "-t",
        choices=["stores", "brands", "products", "all"],
        default="stores",
        help="Type of data to scrape: 'stores' (default), 'brands', 'products', or 'all'"
    )
    parser.add_argument(
        "--country", "-c",
        choices=["all", "th", "sg", "my", "id"],
        default="all",
        help="Country to scrape: 'all' (default), 'th' (Thailand), 'sg' (Singapore), 'my' (Malaysia), 'id' (Indonesia)"
    )
    parser.add_argument(
        "--output-format", "-f",
        choices=["csv", "json", "all"],
        default="all",
        help="Output file format: 'csv', 'json', or 'all' (default)"
    )
    parser.add_argument(
        "--output-dir", "-d",
        default="data",
        help="Directory to save scraped files (default: 'data')"
    )
    parser.add_argument(
        "--url",
        help="Custom URL for product listing scraping (used with --type products)"
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run browser in visible mode (useful for debugging)"
    )
    return parser.parse_args()


async def main_async():
    args = parse_arguments()
    headless = not args.headed

    if args.country == "all":
        countries = DEFAULT_COUNTRIES
    else:
        countries = [args.country]

    if args.type in ("stores", "all"):
        stores = await scrape_stores(countries=countries, headless=headless)
        prefix = f"sunglasshut_stores_{args.country}"
        export_data(stores, prefix, output_format=args.output_format, output_dir=args.output_dir)

    if args.type in ("brands", "all"):
        target_country = countries[0] if countries else "th"
        brands = await scrape_brands(country=target_country, headless=headless)
        prefix = f"sunglasshut_brands_{target_country}"
        export_data(brands, prefix, output_format=args.output_format, output_dir=args.output_dir)

    if args.type == "products":
        prod_url = args.url or f"{BASE_URL}/th/en/products"
        products = await scrape_products(url=prod_url, headless=headless)
        prefix = "sunglasshut_products"
        export_data(products, prefix, output_format=args.output_format, output_dir=args.output_dir)


def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n[!] Process interrupted by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
