-- 02_load_data.sql  |  run after 01_schema.sql
-- Needs local_infile enabled:  SET GLOBAL local_infile = 1;
-- and the client started with --local-infile=1 (MySQL Workbench: add OPT_LOCAL_INFILE=1 in the connection's advanced settings).
-- Change the path below to the full path of the CSV on your machine (use forward slashes on Windows).
USE food_db;

LOAD DATA LOCAL INFILE 'C:/path/to/food_ordering_project/data/food_ordering_behavior_dataset.csv'
INTO TABLE food_orders
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES;

-- Sanity checks: expect 50000 rows and 4000 customers
SELECT COUNT(*) AS total_rows, COUNT(DISTINCT user_id) AS customers FROM food_orders;
