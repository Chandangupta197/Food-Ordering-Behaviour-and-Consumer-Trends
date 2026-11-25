-- 01_schema.sql  |  MySQL 8.0+
CREATE DATABASE IF NOT EXISTS food_db;
USE food_db;

DROP TABLE IF EXISTS food_orders;
CREATE TABLE food_orders (
    order_id            INT PRIMARY KEY,
    user_id             INT NOT NULL,
    age                 TINYINT UNSIGNED NOT NULL,
    city                VARCHAR(30) NOT NULL,
    order_time          VARCHAR(15) NOT NULL,   -- Morning / Afternoon / Evening / Night
    day_type            VARCHAR(10) NOT NULL,   -- Weekday / Weekend
    cuisine             VARCHAR(30) NOT NULL,
    meal_type           VARCHAR(15) NOT NULL,
    restaurant_type     VARCHAR(15) NOT NULL,   -- Budget / Mid-range / Premium
    order_value         INT NOT NULL,
    discount_applied    VARCHAR(3) NOT NULL,    -- Yes / No
    delivery_fee        INT NOT NULL,
    time_taken_to_order INT NOT NULL,
    rating_given        TINYINT NOT NULL,       -- 1 to 5
    is_repeat_order     VARCHAR(3) NOT NULL,    -- Yes / No
    mood                VARCHAR(15) NOT NULL,
    hunger_level        VARCHAR(10) NOT NULL,
    company             VARCHAR(10) NOT NULL,   -- Alone / Family / Friends / Partner
    rainy_weather       VARCHAR(3) NOT NULL,    -- Yes / No
    INDEX idx_city (city),
    INDEX idx_cuisine (cuisine),
    INDEX idx_meal (meal_type),
    INDEX idx_user (user_id)
);
