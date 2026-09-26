{{ config(materialized='table', order_by='brand') }}

-- Grain: one row per brand. dim_product is (sku, gender), so unisex SKUs appear
-- twice; every ratio below counts distinct SKUs to avoid double counting.

with latest_prices as (
    select sku, list_price, offer_price, is_on_sale, discount_pct
    from {{ ref('fct_product_snapshot') }}
    where scraped_date = (select max(scraped_date) from {{ ref('fct_product_snapshot') }})
    limit 1 by sku
),

products as (
    select
        p.brand,
        p.sku,
        p.gender,
        p.is_polarized,
        p.is_customizable,
        p.is_engravable,
        lp.list_price,
        lp.offer_price,
        lp.is_on_sale,
        lp.discount_pct
    from {{ ref('dim_product') }} p
    left join latest_prices lp on p.sku = lp.sku
    where p.brand != ''
),

agg as (
    select
        brand,
        uniqExact(sku)                                        as total_skus,
        uniqExactIf(sku, gender = 'women')                    as women_skus,
        uniqExactIf(sku, gender = 'men')                      as men_skus,
        uniqExactIf(sku, is_polarized)    / uniqExact(sku)    as polarized_ratio,
        uniqExactIf(sku, is_customizable) / uniqExact(sku)    as customizable_ratio,
        uniqExactIf(sku, is_engravable)   / uniqExact(sku)    as engravable_ratio,
        uniqExactIf(sku, is_on_sale)      / uniqExact(sku)    as on_sale_ratio,
        round(min(list_price), 2)                             as min_list_price,
        round(median(list_price), 2)                          as median_list_price,
        round(max(list_price), 2)                             as max_list_price,
        if(countIf(is_on_sale) = 0, null,
           round(avgIf(discount_pct, is_on_sale), 1))         as avg_discount_pct_on_sale
    from products
    group by brand
)

select
    *,
    multiIf(
        median_list_price < 150, 'budget',
        median_list_price < 250, 'mid',
        median_list_price < 400, 'premium',
        'luxury'
    ) as price_tier
from agg
