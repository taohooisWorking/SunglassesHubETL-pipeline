CREATE DATABASE IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.sunglasshut_products
(
    partnumberId         String,
    gender               LowCardinality(String),
    brand                String,
    modelName            String,
    name                 String,
    lensColor            String,
    localizedColorLabel  String,
    roxableLabel         String,
    colorsNumber         UInt32,
    listPrice            Nullable(Float64),
    offerPrice           Nullable(Float64),
    img                  String,
    imgHover              String,
    isJunior             UInt8,
    isFindInStore        UInt8,
    isCustomizable       UInt8,
    isPolarized          UInt8,
    isOutOfStock         UInt8,
    isEngravable         UInt8,
    source_url           String,
    scraped_at           DateTime64(6, 'UTC'),
    _ingested_at         DateTime64(6, 'UTC') DEFAULT now64(6)
)
ENGINE = MergeTree
PARTITION BY (gender, toYYYYMMDD(scraped_at))
ORDER BY (gender, partnumberId, scraped_at);