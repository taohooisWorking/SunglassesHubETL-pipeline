"""
scraper.extractors.brands
Extracts luxury & designer brands listed on sea.sunglasshut.com.
"""

import re
from datetime import datetime, timezone
from typing import Any, Dict, List
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from ..utils import create_stealth_context, create_stealth_page

BASE_URL = "https://sea.sunglasshut.com"


async def scrape_brands(country: str = "th", headless: bool = True) -> List[Dict[str, Any]]:
    """Scrapes luxury & designer brands catalog."""
    results: List[Dict[str, Any]] = []
    url = f"{BASE_URL}/{country.lower()}/en/brands"
    print(f"[*] Starting Brands scraper from: {url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = await create_stealth_context(browser)
        page = await create_stealth_page(context)

        await page.goto(url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(1000)

        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")
        route_brands = soup.find("div", class_="route-brands")
        scraped_time = datetime.now(timezone.utc).isoformat()

        if route_brands:
            items = route_brands.find_all("div", class_="item")
            for item in items:
                img = item.find("img")
                if img:
                    brand_name = img.get("alt", "").strip()
                    logo_src = img.get("src", "")
                    if logo_src and not logo_src.startswith("http"):
                        logo_src = f"{BASE_URL}{logo_src}"

                    slug = re.sub(r"[^a-zA-Z0-9]+", "-", brand_name.lower()).strip("-")
                    results.append({
                        "brand_name": brand_name,
                        "brand_slug": slug,
                        "logo_url": logo_src,
                        "country": country.upper(),
                        "source_url": url,
                        "scraped_at": scraped_time
                    })

        print(f"[+] Found {len(results)} brands.")
        await browser.close()

    return results
