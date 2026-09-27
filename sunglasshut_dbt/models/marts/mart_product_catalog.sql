{{ config(materialized='table', order_by='sku') }}

with latest as (
    select *
    from {{ ref('fct_product_snapshot') }}
    where scraped_date = (select max(scraped_date) from {{ ref('fct_product_snapshot') }})
)

select
    s.sku                                                     as sku,
    any(s.brand)                                              as brand,
    any(b.price_tier)                                         as brand_price_tier,
    any(p.model_name)                                         as model_name,
    if(uniqExact(s.gender) = 2, 'unisex', any(s.gender))      as gender_group,
    any(s.list_price)                                         as list_price,
    any(s.offer_price)                                        as offer_price,
    toUInt8(max(p.is_polarized))                              as is_polarized,
    toUInt8(max(s.is_on_sale))                                as is_on_sale,
    any(s.scraped_date)                                       as snapshot_date
from latest s
join {{ ref('dim_product') }} p on p.sku = s.sku and p.gender = s.gender
left join {{ ref('dim_brand') }} b on b.brand = s.brand
where s.brand != ''
group by s.sku
