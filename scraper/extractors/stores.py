"""
scraper.extractors.stores
Extracts store location information across South East Asia (TH, SG, MY, ID).
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from ..utils import create_stealth_context, create_stealth_page

BASE_URL = "https://sea.sunglasshut.com"


def parse_store_popup(popup_html: str) -> Dict[str, Any]:
    """Extracts store details from the Leaflet marker popup HTML."""
    details = {
        "store_name": "",
        "address": "",
        "opening_hours": "",
        "apple_maps_url": "",
        "google_maps_url": ""
    }
    if not popup_html:
        return details

    soup = BeautifulSoup(popup_html, "html.parser")
    title_box = soup.find("div", class_="title")
    if title_box:
        h6 = title_box.find("h6")
        if h6:
            details["store_name"] = h6.get_text(strip=True)
        p = title_box.find("p")
        if p:
            details["address"] = p.get_text(strip=True)

    info_box = soup.find("table", class_="info")
    if info_box:
        hours_rows = []
        for tr in info_box.find_all("tr"):
            th = tr.find("th")
            td = tr.find("td")
            if th and td:
                hours_rows.append(f"{th.get_text(strip=True)} {td.get_text(strip=True)}")
        details["opening_hours"] = " | ".join(hours_rows)

    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True).lower()
        if "apple" in text or "apple.com" in href:
            details["apple_maps_url"] = href
        elif "google" in text or "google.com" in href:
            details["google_maps_url"] = href

    return details


async def scrape_stores(countries: List[str], headless: bool = True) -> List[Dict[str, Any]]:
    """Scrapes all stores across specified South East Asian countries."""
    results: List[Dict[str, Any]] = []

    print(f"[*] Starting Stores scraper for countries: {[c.upper() for c in countries]}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = await create_stealth_context(browser)
        page = await create_stealth_page(context)

        for country in countries:
            url = f"{BASE_URL}/{country.lower()}/en/stores"
            print(f"[*] Loading stores from: {url}")
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
            except Exception as e:
                print(f"[!] Warning navigating to {url}: {e}")

            await page.wait_for_timeout(1500)

            # Extract raw marker objects from JavaScript window context
            markers_data = await page.evaluate("""() => {
                if (typeof markers === 'undefined') return [];
                const res = [];
                for (const k in markers) {
                    const m = markers[k];
                    res.push({
                        id: k,
                        lat: m.getLatLng ? m.getLatLng().lat : null,
                        lng: m.getLatLng ? m.getLatLng().lng : null,
                        popup: m.getPopup ? m.getPopup().getContent() : ''
                    });
                }
                return res;
            }""")

            print(f"[+] Found {len(markers_data)} stores in {country.upper()}")
            scraped_time = datetime.now(timezone.utc).isoformat()

            for item in markers_data:
                parsed = parse_store_popup(item.get("popup", ""))
                store_record = {
                    "store_id": item.get("id"),
                    "store_name": parsed["store_name"] or item.get("id"),
                    "country": country.upper(),
                    "address": parsed["address"],
                    "opening_hours": parsed["opening_hours"],
                    "latitude": item.get("lat"),
                    "longitude": item.get("lng"),
                    "google_maps_url": parsed["google_maps_url"],
                    "apple_maps_url": parsed["apple_maps_url"],
                    "source_url": url,
                    "scraped_at": scraped_time
                }
                results.append(store_record)

            await asyncio.sleep(1.0)

        await browser.close()

    return results
