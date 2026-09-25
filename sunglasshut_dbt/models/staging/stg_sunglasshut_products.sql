{{ config(materialized='view') }}

select
    partnumberId                       as sku,
    gender,
    brand,
    modelName                          as model_name,
    name                                as product_name,
    lensColor                          as lens_color,
    localizedColorLabel                as color_label,
    roxableLabel                       as roxable_label,
    colorsNumber                       as colors_count,
    listPrice                          as list_price,
    offerPrice                         as offer_price,
    img                                 as image_url,
    imgHover                           as image_hover_url,
    isJunior = 1                        as is_junior,
    isFindInStore = 1                   as is_find_in_store,
    isCustomizable = 1                  as is_customizable,
    isPolarized = 1                     as is_polarized,
    isOutOfStock = 1                    as is_out_of_stock,
    isEngravable = 1                    as is_engravable,
    source_url,
    scraped_at,
    toDate(scraped_at)                 as scraped_date
from {{ source('raw', 'sunglasshut_products') }}
where partnumberId != ''