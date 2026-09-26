import os
import clickhouse_connect
import pandas as pd
from dotenv import load_dotenv

load_dotenv()


def get_client():
    return clickhouse_connect.get_client(
        host=os.environ.get("CLICKHOUSE_HOST", "localhost"),
        port=int(os.environ.get("CLICKHOUSE_PORT", 8123)),
        username=os.environ.get("CLICKHOUSE_USER", "sunglasses_dbt"),
        password=os.environ.get("CLICKHOUSE_PASSWORD", "sunglasses_dbt"),
        database=os.environ.get("CLICKHOUSE_RAW_DB", "raw"),
    )


def load_products(df: pd.DataFrame, client, table: str = "sunglasshut_products"):
    df = df.copy()

    bool_cols = ["isJunior", "isFindInStore", "isCustomizable", "isPolarized", "isOutOfStock", "isEngravable", "isOnSale"]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].astype(int)

    if "colorsNumber" in df.columns:
        df["colorsNumber"] = pd.to_numeric(df["colorsNumber"], errors="coerce").fillna(0).astype("uint32")

    for price_col in ["listPrice", "offerPrice", "percentageDiscount", "amountOfDiscount"]:
        if price_col in df.columns:
            df[price_col] = pd.to_numeric(df[price_col], errors="coerce")

    str_cols = [
        "partnumberId", "gender", "brand", "modelName", "name",
        "lensColor", "localizedColorLabel", "roxableLabel",
        "img", "imgHover", "source_url"
    ]
    for col in str_cols:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str)

    df["scraped_at"] = pd.to_datetime(df["scraped_at"])

    client.insert_df(table, df)
    return len(df)