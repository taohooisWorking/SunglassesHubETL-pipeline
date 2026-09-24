#!/usr/bin/env python3
"""
scraper.dump_page
Tool to fetch and dump JavaScript-rendered HTML from a URL using Playwright.
Saves the rendered DOM to an HTML file so you can inspect CSS selectors in your browser.

Usage:
    python scraper/dump_page.py --url https://sea.sunglasshut.com/th/en/stores --output data/dumped_stores.html
    python scraper/dump_page.py --url https://sea.sunglasshut.com/th/en/brands --output data/dumped_brands.html
"""

import argparse
import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "WebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


async def dump_rendered_html(url: str, output_path: str, wait_timeout: int = 30000, headless: bool = True):
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    print(f"[*] Launching Playwright Chromium (headless={headless})...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox"
            ]
        )
        context = await browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1440, "height": 900},
            locale="en-US"
        )
        page = await context.new_page()

        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        print(f"[*] Navigating to: {url}")
        try:
            response = await page.goto(url, wait_until="networkidle", timeout=wait_timeout)
            status = response.status if response else "Unknown"
            print(f"[+] HTTP Status: {status}")
        except Exception as e:
            print(f"[!] Warning during navigation (networkidle): {e}")
            print("[*] Falling back to current DOM content...")

        await page.wait_for_timeout(2000)

        title = await page.title()
        rendered_html = await page.content()
        print(f"[+] Page Title: '{title}'")
        print(f"[+] HTML size: {len(rendered_html):,} characters")

        out_file.write_text(rendered_html, encoding="utf-8")
        print(f"[SUCCESS] Rendered HTML successfully saved to: {out_file.resolve()}")
        print(f"[*] Inspect CSS selectors with:")
        print(f"    open {out_file.resolve()}")

        await browser.close()


def main():
    parser = argparse.ArgumentParser(description="Dump JS-rendered HTML using Playwright.")
    parser.add_argument("--url", default="https://sea.sunglasshut.com/th/en/stores", help="Target URL to dump")
    parser.add_argument("--output", "-o", default="data/dumped_page.html", help="Output file path (.html)")
    parser.add_argument("--timeout", type=int, default=30000, help="Navigation timeout in milliseconds")
    parser.add_argument("--headed", action="store_true", help="Run browser in visible mode")

    args = parser.parse_args()
    asyncio.run(dump_rendered_html(args.url, args.output, args.timeout, headless=not args.headed))


if __name__ == "__main__":
    main()
