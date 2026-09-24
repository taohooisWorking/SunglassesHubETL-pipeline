"""
scraper.extractors.products
Configurable DOM product listing extractor for PLP (Product Listing Pages).
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from ..utils import create_stealth_context, create_stealth_page

BASE_URL = "https://sea.sunglasshut.com"

DEFAULT_PRODUCT_SELECTORS = {
    "card": ".product-card, .item, [data-testid='product-card'], .product-item",
    "brand": ".brand, .product-card__brand, [data-element='brand']",
    "name": ".name, .product-name, .product-card__name, h2, h3",
    "price": ".price, .sales-price, .product-card__price",
    "original_price": ".original-price, .strike-price, .was-price",
    "link": "a[href]",
    "image": "img[src]"
}


async def scrape_products(
    url: str,
    selectors: Optional[Dict[str, str]] = None,
    headless: bool = True
) -> List[Dict[str, Any]]:
    """
    Scrapes product listings from a rendered page DOM using configurable CSS selectors.
    """
    sel = {**DEFAULT_PRODUCT_SELECTORS, **(selectors or {})}
    results: List[Dict[str, Any]] = []
    print(f"[*] Navigating to Product Listing: {url}")
    print(f"[*] Using Card Selector: '{sel['card']}'")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = await create_stealth_context(browser)
        page = await create_stealth_page(context)

        try:
            await page.goto(url, wait_until="networkidle", timeout=35000)
        except Exception as e:
            print(f"[!] Warning during navigation: {e}")

        # Scroll to trigger lazy loading
        await page.evaluate("window.scrollBy(0, 1000)")
        await page.wait_for_timeout(2000)

        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")
        scraped_time = datetime.now(timezone.utc).isoformat()

        cards = soup.select(sel["card"])
        print(f"[+] Found {len(cards)} matching product card elements")

        for idx, card in enumerate(cards, 1):
            brand_el = card.select_one(sel["brand"]) if sel.get("brand") else None
            name_el = card.select_one(sel["name"]) if sel.get("name") else None
            price_el = card.select_one(sel["price"]) if sel.get("price") else None
            orig_price_el = card.select_one(sel["original_price"]) if sel.get("original_price") else None
            link_el = card.select_one(sel["link"]) if sel.get("link") else None
            img_el = card.select_one(sel["image"]) if sel.get("image") else None

            prod_url = link_el.get("href") if link_el else ""
            if prod_url and not prod_url.startswith("http"):
                prod_url = f"{BASE_URL}{prod_url}"

            img_url = img_el.get("src") or img_el.get("data-src") if img_el else ""
            if img_url and not img_url.startswith("http"):
                img_url = f"{BASE_URL}{img_url}"

            prod_record = {
                "item_index": idx,
                "brand": brand_el.get_text(strip=True) if brand_el else "",
                "product_name": name_el.get_text(strip=True) if name_el else "",
                "price": price_el.get_text(strip=True) if price_el else "",
                "original_price": orig_price_el.get_text(strip=True) if orig_price_el else "",
                "product_url": prod_url,
                "image_url": img_url,
                "source_url": url,
                "scraped_at": scraped_time
            }
            results.append(prod_record)

        await browser.close()

    return results
