{{ config(materialized='table', order_by='(sku, gender)') }}

select
    sku,
    gender,
    argMax(brand, scraped_at)              as brand,
    argMax(model_name, scraped_at)         as model_name,
    argMax(product_name, scraped_at)       as product_name,
    argMax(lens_color, scraped_at)         as lens_color,
    argMax(color_label, scraped_at)        as color_label,
    argMax(image_url, scraped_at)          as image_url,
    argMax(is_junior, scraped_at)          as is_junior,
    argMax(is_customizable, scraped_at)    as is_customizable,
    argMax(is_engravable, scraped_at)      as is_engravable,
    max(scraped_at)                        as last_seen_at
from {{ ref('stg_sunglasshut_products') }}
group by sku, gender
