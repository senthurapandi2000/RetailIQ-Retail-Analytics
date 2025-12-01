/*
RetailIQ Business Analysis Queries
Author: Senthurapandi Rajendran

These queries use the analytical views created in the RetailIQ
SQLite warehouse.
*/


-- ============================================================
-- 1. Monthly revenue and order trend
-- ============================================================

SELECT *
FROM vw_monthly_sales
ORDER BY 1;


-- ============================================================
-- 2. Top 10 international markets by revenue
-- United Kingdom is excluded
-- ============================================================

SELECT
    country,
    ROUND(revenue, 2) AS revenue,
    orders
FROM vw_country_performance
WHERE country <> 'United Kingdom'
ORDER BY revenue DESC
LIMIT 10;


-- ============================================================
-- 3. Geographic revenue concentration
-- ============================================================

SELECT
    country,
    ROUND(revenue, 2) AS revenue,
    ROUND(
        100.0 * revenue / SUM(revenue) OVER (),
        2
    ) AS revenue_share_percentage
FROM vw_country_performance
ORDER BY revenue DESC;


-- ============================================================
-- 4. Top 10 products by revenue
-- Non-product operational entries are excluded
-- ============================================================

SELECT
    stock_code,
    description,
    units_sold,
    ROUND(revenue, 2) AS revenue,
    orders
FROM vw_product_performance
WHERE description IS NOT NULL
  AND UPPER(TRIM(description)) NOT IN (
      'MANUAL',
      'POSTAGE',
      'DOTCOM POSTAGE',
      'BANK CHARGES',
      'AMAZON FEE',
      'DISCOUNT'
  )
ORDER BY revenue DESC
LIMIT 10;


-- ============================================================
-- 5. Top 10 products by units sold
-- ============================================================

SELECT
    stock_code,
    description,
    units_sold,
    ROUND(revenue, 2) AS revenue
FROM vw_product_performance
WHERE description IS NOT NULL
  AND UPPER(TRIM(description)) NOT IN (
      'MANUAL',
      'POSTAGE',
      'DOTCOM POSTAGE',
      'BANK CHARGES',
      'AMAZON FEE',
      'DISCOUNT'
  )
ORDER BY units_sold DESC
LIMIT 10;


-- ============================================================
-- 6. Highest-value customers
-- ============================================================

SELECT *
FROM vw_customer_performance
ORDER BY revenue DESC
LIMIT 20;


-- ============================================================
-- 7. Markets with high revenue and order volume
-- ============================================================

SELECT
    country,
    ROUND(revenue, 2) AS revenue,
    orders
FROM vw_country_performance
ORDER BY revenue DESC, orders DESC
LIMIT 15;


-- ============================================================
-- 8. Product revenue versus sales volume
-- Useful for identifying high-volume, lower-revenue products
-- ============================================================

SELECT
    stock_code,
    description,
    units_sold,
    ROUND(revenue, 2) AS revenue,
    orders
FROM vw_product_performance
WHERE description IS NOT NULL
  AND revenue > 0
  AND units_sold > 0
ORDER BY revenue DESC
LIMIT 100;


-- ============================================================
-- 9. Sample of valid sales transactions
-- ============================================================

SELECT *
FROM vw_valid_sales
LIMIT 100;