"""
Central configuration for Sunglass Hut PLP scraper.
"""

ALGOLIA_APP_ID = "21OGKM5TH5"
ALGOLIA_API_KEY = "dc91173a4a5d669a3eef474e5836e94f"
ALGOLIA_INDEX_NAME = "prod_live_sgh_en-us__grouped"
ALGOLIA_URL = f"https://{ALGOLIA_APP_ID}-dsn.algolia.net/1/indexes/{ALGOLIA_INDEX_NAME}/query"

CATEGORY_FACETS = {
    "women": "categories:gender_female",
    "men": "categories:gender_male",
}
CATEGORY_IDS = CATEGORY_FACETS

# Price ranges to partition requests and stay under Algolia's 1000 hits/query limit
PRICE_RANGES = [
    (0, 150),
    (150, 250),
    (250, 400),
    (400, 600),
    (600, 100000),
]

REFERERS = {
    "women": "https://www.sunglasshut.com/us/womens-sunglasses",
    "men": "https://www.sunglasshut.com/us/mens-sunglasses",
}

DEFAULT_HEADERS = {
    "X-Algolia-Application-Id": ALGOLIA_APP_ID,
    "X-Algolia-API-Key": ALGOLIA_API_KEY,
    "Content-Type": "application/json",
    "Referer": "https://www.sunglasshut.com/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}