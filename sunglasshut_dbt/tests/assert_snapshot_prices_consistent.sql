-- Fails on rows where the price fields disagree with each other:
--   * offer price above list price
--   * is_on_sale (from Algolia's ON_SALE flag) disagrees with list_price > offer_price
-- The second check catches Algolia moving promo prices to a price list the
-- scraper's _effective_price() does not pick up.

select *
from {{ ref('fct_product_snapshot') }}
where offer_price > list_price
   or is_on_sale != (list_price > offer_price)
