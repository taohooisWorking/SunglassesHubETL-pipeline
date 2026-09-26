{{ config(
    materialized='table',
    order_by='(sku, gender, scraped_date)',
    partition_by='toYYYYMM(scraped_date)'
) }}

with ranked as (
    select
        *,
        row_number() over (
            partition by sku, gender, scraped_date
            order by scraped_at desc
        ) as rn
    from {{ ref('stg_sunglasshut_products') }}
)

select
    sku,
    gender,
    brand,
    list_price,
    offer_price,
    is_on_sale,
    coalesce(discount_pct, 0)          as discount_pct,
    coalesce(discount_amount, 0)       as discount_amount,
    is_out_of_stock,
    scraped_date
from ranked
where rn = 1
