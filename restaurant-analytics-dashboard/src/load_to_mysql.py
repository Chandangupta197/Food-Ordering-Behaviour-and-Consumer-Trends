"""Load the CSV into MySQL (alternative to LOAD DATA in sql/02_load_data.sql).

Run 01_schema.sql first, then:
    pip install sqlalchemy pymysql
    set MYSQL_USER=root & set MYSQL_PASSWORD=yourpassword      (Windows)
    export MYSQL_USER=root MYSQL_PASSWORD=yourpassword           (Mac/Linux)
    python src/load_to_mysql.py
"""
import os
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text

USER = os.environ.get("MYSQL_USER", "root")
PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
HOST = os.environ.get("MYSQL_HOST", "localhost")
DB = os.environ.get("MYSQL_DB", "food_db")
CSV = Path(__file__).resolve().parents[1] / "data" / "food_ordering_behavior_dataset.csv"

engine = create_engine(f"mysql+pymysql://{USER}:{PASSWORD}@{HOST}/{DB}")
df = pd.read_csv(CSV)
with engine.begin() as conn:
    conn.execute(text("TRUNCATE TABLE food_orders"))
df.to_sql("food_orders", engine, if_exists="append", index=False, chunksize=5000)

with engine.connect() as conn:
    rows, users = conn.execute(text("SELECT COUNT(*), COUNT(DISTINCT user_id) FROM food_orders")).one()
print(f"Loaded {rows} rows, {users} customers into {DB}.food_orders")
