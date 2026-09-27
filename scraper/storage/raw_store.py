"""
scraper.storage.raw_store
Raw landing zone in MinIO (S3-compatible). Each scrape run stores the
untransformed Algolia hits so they can be re-transformed later without
re-scraping (the site only ever shows today's catalog).

Layout:
    s3://<bucket>/products/dt=YYYY-MM-DD/run=YYYYMMDDTHHMMSSZ/
        manifest.json        scraped_at, index name, hit counts
        women.json.gz        hits from the women's gender facet
        men.json.gz          hits from the men's gender facet
        on_sale.json.gz      ON_SALE hits (queried without a gender facet)
"""

import gzip
import io
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from minio import Minio

load_dotenv()

logger = logging.getLogger("scraper.storage.raw_store")

BUCKET = os.environ.get("MINIO_BUCKET", "sunglasshut-raw")
PREFIX = "products"


def get_client() -> Minio:
    return Minio(
        os.environ.get("MINIO_ENDPOINT", "localhost:9002"),
        access_key=os.environ["MINIO_ROOT_USER"],
        secret_key=os.environ["MINIO_ROOT_PASSWORD"],
        secure=os.environ.get("MINIO_SECURE", "false").lower() == "true",
    )


def _put_json(client: Minio, key: str, obj: Any, compress: bool) -> None:
    body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    content_type = "application/json"
    if compress:
        body = gzip.compress(body)
        content_type = "application/gzip"
    client.put_object(BUCKET, key, io.BytesIO(body), len(body), content_type=content_type)


def _get_json(client: Minio, key: str) -> Any:
    response = client.get_object(BUCKET, key)
    try:
        body = response.read()
    finally:
        response.close()
        response.release_conn()
    if key.endswith(".gz"):
        body = gzip.decompress(body)
    return json.loads(body)


def save_run(raw: Dict[str, List[Dict[str, Any]]], scraped_at: datetime, index_name: str) -> str:
    """Writes one scrape run to MinIO and returns its run prefix."""
    client = get_client()
    if not client.bucket_exists(BUCKET):
        client.make_bucket(BUCKET)

    run_prefix = f"{PREFIX}/dt={scraped_at:%Y-%m-%d}/run={scraped_at:%Y%m%dT%H%M%SZ}"
    for name, hits in raw.items():
        _put_json(client, f"{run_prefix}/{name}.json.gz", hits, compress=True)

    # Written last: a run without a manifest is incomplete and never loaded.
    manifest = {
        "scraped_at": scraped_at.isoformat(),
        "algolia_index": index_name,
        "hit_counts": {name: len(hits) for name, hits in raw.items()},
    }
    _put_json(client, f"{run_prefix}/manifest.json", manifest, compress=False)

    logger.info(f"Saved raw run to s3://{BUCKET}/{run_prefix} {manifest['hit_counts']}")
    return run_prefix


def latest_run(date: Optional[str] = None) -> str:
    """Returns the newest complete run prefix, optionally within one YYYY-MM-DD day."""
    client = get_client()
    search = f"{PREFIX}/dt={date}/" if date else f"{PREFIX}/"
    manifests = [
        obj.object_name
        for obj in client.list_objects(BUCKET, prefix=search, recursive=True)
        if obj.object_name.endswith("/manifest.json")
    ]
    if not manifests:
        raise FileNotFoundError(f"No complete scrape runs under s3://{BUCKET}/{search}")
    return max(manifests).rsplit("/", 1)[0]


def load_run(run_prefix: str) -> Tuple[Dict[str, List[Dict[str, Any]]], datetime]:
    """Reads a run back from MinIO: ({name: hits}, scraped_at)."""
    client = get_client()
    manifest = _get_json(client, f"{run_prefix}/manifest.json")
    raw = {
        name: _get_json(client, f"{run_prefix}/{name}.json.gz")
        for name in manifest["hit_counts"]
    }
    return raw, datetime.fromisoformat(manifest["scraped_at"])
