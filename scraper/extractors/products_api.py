"""
scraper.extractors.products_api
Extracts product listings directly from Sunglass Hut's Algolia Search API.
Covers both men's and women's categories through one parameterized function.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal

import pandas as pd
import requests

from ..config import (
    ALGOLIA_URL,
    CATEGORY_FACETS,
    DEFAULT_HEADERS,
    PRICE_RANGES,
    REFERERS,
)

logger = logging.getLogger("scraper.extractors.products_api")

COLUMNS = [
    "isJunior",
    "lensColor",
    "img",
    "isFindInStore",
    "isCustomizable",
    "roxableLabel",
    "brand",
    "imgHover",
    "isPolarized",
    "colorsNumber",
    "isOutOfStock",
    "modelName",
    "isEngravable",
    "localizedColorLabel",
    "name",
    "listPrice",
    "offerPrice",
]


def _transform_hit(hit: Dict[str, Any]) -> Dict[str, Any]:
    """Transforms a raw Algolia hit into the standardized product record."""
    attrs = hit.get("attributes", {})
    categories = hit.get("categories", [])
    categories_trans = hit.get("categories_translated", [])

    prices = hit.get("prices", {})
    offer_info = (
        prices.get("DefaultOfferPriceList_US")
        or prices.get("LISTPRICE")
        or {}
    )
    list_price = offer_info.get("listPrice") or hit.get("sortPrice_Guest")
    offer_price = offer_info.get("offerPrice") or hit.get("sortPrice_Guest")

    # Extract images from attachments
    attachments = hit.get("attachments", [])
    plp_imgs = [
        a.get("url")
        for a in attachments
        if a.get("rule") == "PLP" and a.get("url")
    ]
    if not plp_imgs:
        plp_imgs = [a.get("url") for a in attachments if a.get("url")]

    img = plp_imgs[0] if len(plp_imgs) > 0 else ""
    img_hover = plp_imgs[1] if len(plp_imgs) > 1 else img

    brand = attrs.get("BRAND", "")
    model_name = attrs.get("MODEL_NAME", "")
    name = f"{brand} {model_name}".strip() if brand and model_name else (model_name or brand)

    return {
        "isJunior": (
            attrs.get("GENDER") == "CHILD"
            or attrs.get("PRODUCT_TYPE") == "Junior"
            or "gender_kids" in categories
        ),
        "lensColor": attrs.get("LENS_COLOR", ""),
        "img": img,
        "isFindInStore": str(attrs.get("SHIP_FROM_STORE", "")).upper() == "TRUE",
        "isCustomizable": "custom_sunglasses" in categories,
        "roxableLabel": attrs.get("ROXABLE", ""),
        "brand": brand,
        "imgHover": img_hover,
        "isPolarized": str(attrs.get("POLARIZED", "")).upper() == "TRUE",
        "colorsNumber": attrs.get("CROSS_LINKS", 1),
        "isOutOfStock": (
            hit.get("inventoryQuantity", 0) <= 0
            or not hit.get("buyable", True)
        ),
        "modelName": model_name,
        "isEngravable": "Engraving Sunglasses" in categories_trans,
        "localizedColorLabel": attrs.get("FRONT_COLOR", "") or attrs.get("FRONT_COLOR_FACET", ""),
        "name": name,
        "listPrice": list_price,
        "offerPrice": offer_price,
        "partnumberId": hit.get("partnumberId", "") or hit.get("objectID", ""),
    }


def fetch_products(gender: Literal["men", "women"]) -> pd.DataFrame:
    """
    Fetches all products for the given gender category from the Algolia API.
    Uses price ranges to partition queries and bypass the 1000 hits limit.
    Returns a DataFrame with the selected product columns plus scrape metadata.
    """
    if gender not in CATEGORY_FACETS:
        raise ValueError(
            f"Unknown gender '{gender}', expected one of {list(CATEGORY_FACETS)}"
        )

    facet = CATEGORY_FACETS[gender]
    logger.info(f"Fetching Algolia catalog for gender={gender} (facet={facet})")

    seen_ids = set()
    records: List[Dict[str, Any]] = []

    for low, high in PRICE_RANGES:
        params = (
            f'facetFilters=["{facet}"]'
            f'&numericFilters=["sortPrice_Guest>={low}", "sortPrice_Guest<{high}"]'
            f'&hitsPerPage=1000'
        )
        payload = {"params": params}
        response = requests.post(
            ALGOLIA_URL,
            headers=DEFAULT_HEADERS,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        hits = data.get("hits", [])

        for hit in hits:
            obj_id = hit.get("objectID") or hit.get("partnumberId")
            if obj_id and obj_id in seen_ids:
                continue
            if obj_id:
                seen_ids.add(obj_id)

            records.append(_transform_hit(hit))

    df = pd.DataFrame(records)
    if df.empty:
        df = pd.DataFrame(columns=COLUMNS)

    scraped_at = datetime.now(timezone.utc).isoformat()
    df["gender"] = gender
    df["scraped_at"] = scraped_at
    df["source_url"] = REFERERS.get(gender, "")

    logger.info(f"Fetched {len(df)} products for gender={gender}")
    return df


def fetch_all_genders() -> pd.DataFrame:
    """Fetches both men's and women's catalogs and combines them into one DataFrame."""
    dfs = [fetch_products(gender) for gender in CATEGORY_FACETS]
    return pd.concat(dfs, ignore_index=True)