from scraper.extractors.products_api import fetch_all_genders
from scraper.loaders.clickhouse_loader import get_client, load_products

df = fetch_all_genders()
client = get_client()
n = load_products(df, client)
print(f"Loaded {n} rows into ClickHouse")