"""
scraper.extractors.products_api
Extracts product listings directly from Sunglass Hut's Algolia Search API.
fetch_raw_hits() is the extract step; build_products() is the transform step.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

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
    "isOnSale",
    "percentageDiscount",
    "amountOfDiscount",
    "partnumberId",
]


def _to_value_list(value: Any) -> List[str]:
    """
    Normalizes an Algolia attribute that may come back as:
      - a plain string, e.g. "FALSE"
      - a stringified mixed list, e.g. "[FALSE, TRUE]"
        (grouped index: multiple color variants with different flag values)
      - an actual list, e.g. ["FALSE", "TRUE"]
    into a flat list of stripped string values.
    """
    if isinstance(value, list):
        return [str(v).strip() for v in value]
    s = str(value if value is not None else "").strip()
    if s.startswith("[") and s.endswith("]"):
        return [v.strip() for v in s.strip("[]").split(",") if v.strip()]
    return [s] if s else []


def _is_flag_true(value: Any, true_markers: tuple = ("TRUE",)) -> bool:
    """
    True if ANY value in the (possibly grouped/mixed) attribute matches
    one of the accepted true markers, case-insensitive.

    Needed because this Algolia index groups color variants under one hit,
    so a boolean-looking attribute can come back as a mixed list, and at
    least one field (POLARIZED) uses a non-standard true marker (its own
    facet name "POLARIZED" instead of "TRUE").
    """
    markers = {m.upper() for m in true_markers}
    return any(v.upper() in markers for v in _to_value_list(value))


def _effective_price(prices: Dict[str, Any]) -> Dict[str, Any]:
    """
    Picks the price list a Guest actually sees. Promotions (e.g. "50% off")
    live in their own price list with a higher precedence, not in
    DefaultOfferPriceList_US, so we take the currently-active Guest list with
    the highest (priceListPrecedence, precedence). Rx (prescription lens)
    lists are skipped.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    candidates = [
        p for name, p in prices.items()
        if isinstance(p, dict)
        and not name.startswith("Rx")
        and p.get("segment") in (None, "Guest")
        and (p.get("startDate") or "") <= now
        and now < (p.get("endDate") or "9999")
    ]
    if not candidates:
        return prices.get("DefaultOfferPriceList_US") or prices.get("LISTPRICE") or {}
    return max(
        candidates,
        key=lambda p: (p.get("priceListPrecedence", 0), p.get("precedence", 0)),
    )


def _transform_hit(hit: Dict[str, Any]) -> Dict[str, Any]:
    """Transforms a raw Algolia hit into the standardized product record."""
    attrs = hit.get("attributes", {})
    categories = hit.get("categories", [])
    categories_trans = hit.get("categories_translated", [])

    offer_info = _effective_price(hit.get("prices", {}))
    list_price = offer_info.get("listPrice") or hit.get("sortPrice_Guest")
    offer_price = offer_info.get("offerPrice") or hit.get("sortPrice_Guest")
    percentage_discount = offer_info.get("percentageDiscount", 0.0)
    amount_of_discount = offer_info.get("amountOfDiscount", 0.0)

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
        "isFindInStore": _is_flag_true(attrs.get("SHIP_FROM_STORE", "")),
        "isCustomizable": "custom_sunglasses" in categories,
        "roxableLabel": attrs.get("ROXABLE", ""),
        "brand": brand,
        "imgHover": img_hover,
        # POLARIZED is non-standard: its "true" value is the literal string
        # "POLARIZED" (matching the facet name) rather than "TRUE".
        "isPolarized": _is_flag_true(attrs.get("POLARIZED", ""), true_markers=("TRUE", "POLARIZED")),
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
        # ON_SALE can come back mixed (e.g. "[FALSE, TRUE]") when different
        # color variants of the same grouped hit have different sale status.
        "isOnSale": _is_flag_true(attrs.get("ON_SALE", "")),
        "percentageDiscount": percentage_discount,
        "amountOfDiscount": amount_of_discount,
        "partnumberId": hit.get("partnumberId", "") or hit.get("objectID", ""),
    }


SALE_FACET = "attributes.ON_SALE:TRUE"


def _fetch_by_price_ranges(facet_filters: List[str], label: str) -> List[Dict[str, Any]]:
    """
    Runs one Algolia query per PRICE_RANGES bucket for the given facetFilters
    and returns all hits, to stay under Algolia's 1000 hits/query cap.
    """
    facet_filters_json = ", ".join(f'"{f}"' for f in facet_filters)
    all_hits: List[Dict[str, Any]] = []

    for low, high in PRICE_RANGES:
        params = (
            f'facetFilters=[{facet_filters_json}]'
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
        nb_hits = data.get("nbHits", 0)

        if nb_hits > len(hits):
            logger.warning(
                f"TRUNCATED range for {label} filters={facet_filters} price[{low},{high}): "
                f"nbHits={nb_hits} but only fetched {len(hits)}. "
                f"Consider splitting this price range further."
            )

        all_hits.extend(hits)

    return all_hits


def fetch_raw_hits() -> Dict[str, List[Dict[str, Any]]]:
    """
    Extract step: queries Algolia and returns the untransformed hits, keyed by
    the query that produced them: one entry per gender facet plus "on_sale".

    A merchandising Query Rule on this index (qr-1758165374462) fires whenever
    a gender category filter is present and silently hides every ON_SALE
    variant, so on-sale items are queried separately WITHOUT the gender facet
    and assigned to a gender later in build_products().
    """
    raw = {
        gender: _fetch_by_price_ranges([facet], gender)
        for gender, facet in CATEGORY_FACETS.items()
    }
    raw["on_sale"] = _fetch_by_price_ranges([SALE_FACET], "on_sale")
    return raw


def build_products(raw: Dict[str, List[Dict[str, Any]]], scraped_at: datetime) -> pd.DataFrame:
    """
    Transform step: turns the hits from fetch_raw_hits() into one DataFrame of
    product records for both genders, plus scrape metadata.
    """
    dfs = []
    for gender, facet in CATEGORY_FACETS.items():
        gender_tag = facet.split(":", 1)[1]
        # On-sale hits never overlap the gender pass by objectID; keep only the
        # ones tagged with this gender's category.
        hits = raw.get(gender, []) + [
            h for h in raw.get("on_sale", []) if gender_tag in h.get("categories", [])
        ]

        seen_ids = set()
        records: List[Dict[str, Any]] = []
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
        df["gender"] = gender
        df["scraped_at"] = scraped_at.isoformat()
        df["source_url"] = REFERERS.get(gender, "")

        logger.info(f"Built {len(df)} products for gender={gender}")
        dfs.append(df)

    return pd.concat(dfs, ignore_index=True)
