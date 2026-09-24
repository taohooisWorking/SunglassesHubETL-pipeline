"""
scraper.utils
Helper utilities for browser automation, anti-bot evasion, and file exports.
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from playwright.async_api import Browser, BrowserContext, Page

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "WebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


async def create_stealth_context(browser: Browser, user_agent: str = DEFAULT_USER_AGENT) -> BrowserContext:
    """Creates a browser context configured to evade standard automation detections."""
    context = await browser.new_context(
        user_agent=user_agent,
        viewport={"width": 1440, "height": 900},
        locale="en-US"
    )
    return context


async def create_stealth_page(context: BrowserContext) -> Page:
    """Initializes a page with bot-evasion overrides (e.g. navigator.webdriver)."""
    page = await context.new_page()
    await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        window.chrome = {
            runtime: {}
        };
    """)
    return page


def save_to_csv(data: List[Dict[str, Any]], filepath: Path) -> None:
    """Saves records to a UTF-8 with BOM CSV file."""
    if not data:
        print(f"[!] No data to save for CSV: {filepath}")
        return

    filepath.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(data[0].keys())

    with open(filepath, mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

    print(f"[SUCCESS] CSV exported ({len(data)} rows): {filepath.resolve()}")


def save_to_json(data: List[Dict[str, Any]], filepath: Path) -> None:
    """Saves records to a formatted JSON file."""
    if not data:
        print(f"[!] No data to save for JSON: {filepath}")
        return

    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, mode="w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[SUCCESS] JSON exported ({len(data)} items): {filepath.resolve()}")


def export_data(
    data: List[Dict[str, Any]],
    base_filename: str,
    output_format: str = "all",
    output_dir: str = "data"
) -> None:
    """Exports scraped data to CSV, JSON, or both based on format preference."""
    out_dir = Path(output_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if output_format in ("csv", "all"):
        csv_file = out_dir / f"{base_filename}_{timestamp}.csv"
        save_to_csv(data, csv_file)

    if output_format in ("json", "all"):
        json_file = out_dir / f"{base_filename}_{timestamp}.json"
        save_to_json(data, json_file)
