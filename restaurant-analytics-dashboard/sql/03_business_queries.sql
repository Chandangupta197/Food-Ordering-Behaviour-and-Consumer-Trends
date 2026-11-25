-- 03_business_queries.sql  |  MySQL 8.0+ (window functions need 8.0)
USE food_db;

-- Q1. Orders, revenue and average order value by city
SELECT city, COUNT(*) AS orders, ROUND(SUM(order_value)) AS revenue,
       ROUND(AVG(order_value), 2) AS avg_order_value
FROM food_orders
GROUP BY city
ORDER BY orders DESC;

-- Q2. Revenue and average rating by meal type
SELECT meal_type, COUNT(*) AS orders, SUM(order_value) AS revenue,
       ROUND(AVG(rating_given), 3) AS avg_rating
FROM food_orders
GROUP BY meal_type
ORDER BY revenue DESC;

-- Q3. Repeat-order rate by discount
SELECT discount_applied, COUNT(*) AS orders,
       ROUND(100.0 * SUM(is_repeat_order = 'Yes') / COUNT(*), 2) AS repeat_rate_pct
FROM food_orders
GROUP BY discount_applied;

-- Q4. Top cuisine in each city (window function)
SELECT city, cuisine, orders FROM (
    SELECT city, cuisine, COUNT(*) AS orders,
           RANK() OVER (PARTITION BY city ORDER BY COUNT(*) DESC) AS rk
    FROM food_orders
    GROUP BY city, cuisine
) t
WHERE rk = 1;

-- Q5. Top 5 average order values by restaurant type and company
SELECT restaurant_type, company, ROUND(AVG(order_value), 2) AS aov
FROM food_orders
GROUP BY restaurant_type, company
ORDER BY aov DESC
LIMIT 5;
