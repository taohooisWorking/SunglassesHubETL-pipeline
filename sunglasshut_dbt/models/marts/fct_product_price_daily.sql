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
    product_name,
    list_price,
    offer_price,
    (list_price is not null and offer_price is not null and list_price > offer_price) as is_on_sale,
    round(
        if(list_price is not null and list_price > 0 and offer_price is not null,
           (list_price - offer_price) / list_price * 100, 0),
        1
    ) as discount_pct,
    is_polarized,
    is_out_of_stock,
    scraped_date
from ranked
where rn = 1