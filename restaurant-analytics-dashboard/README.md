# Food Ordering Behaviour & Consumer Trends
Data Analytics & Machine Learning project: Python, Pandas, NumPy, MySQL, Matplotlib, Seaborn, Scikit-learn.

## Owner analytics dashboard (web prototype)
The project includes a Python/Flask dashboard with owner registration/login and a single CSV upload per owner. Each account's uploaded file is stored separately in the local SQLite database and is used as the dashboard's only analysis dataset. Until an owner uploads a file, the app uses the included sample dataset.

1. `pip install -r requirements.txt`
2. `python app.py`
3. Open `http://127.0.0.1:5000`, create a local owner account, and sign in.

The browser loads Chart.js from its public CDN, so an internet connection is needed for interactive charts. Owner accounts and uploaded CSV data are stored in `instance/owners.sqlite3`; set `TABLEWISE_SECRET_KEY` before deployment. This is a local prototype, not a production authentication or subscription service.

The dashboard detects likely column roles, adds filters for categorical columns, builds charts when mapped fields support them, summarizes the data, and exports the filtered CSV. Owners can change inferred field mappings in the dashboard.

The upload accepts any readable, non-empty CSV up to 25 MB. It guesses common roles such as sales, date, category, product, location, quantity, rating, customer, and order ID from headers and values. Owners can change these mappings; filters and the data table also include other columns. Charts appear when mapped fields support them. Since arbitrary headers cannot always reveal their meaning, owners should confirm the mappings. Inventory forecasts require inventory data in the uploaded file.

## Folder structure
```
food_ordering_project/
├── data/food_ordering_behavior_dataset.csv   50,000 orders x 19 columns
├── notebooks/food_ordering_analysis.ipynb    cleaning, EDA, tests, SQL, ML, clustering
├── sql/01_schema.sql                         create database + table (MySQL 8)
├── sql/02_load_data.sql                      load the CSV (LOAD DATA LOCAL INFILE)
├── sql/03_business_queries.sql               5 business queries
├── src/load_to_mysql.py                      alternative loader using pandas + SQLAlchemy
├── outputs/charts/                           PNG charts (regenerated when the notebook runs)
└── requirements.txt
```

## How to run
1. `pip install -r requirements.txt`
2. `cd notebooks` then `jupyter notebook` and open `food_ordering_analysis.ipynb`; choose **Run All**.
   The notebook runs its SQL section on an in-memory SQLite copy, so MySQL is not required for it.
3. For MySQL: run `sql/01_schema.sql`, load data with `sql/02_load_data.sql` (edit the file path) or `python src/load_to_mysql.py`, then run `sql/03_business_queries.sql`.

## Key results (from the notebook)
| Item | Result |
|---|---|
| Data quality | 0 missing values, 0 duplicates, 0 IQR outliers |
| Orders by city | 8,262 (Hyderabad) to 8,443 (Mumbai) |
| Orders by cuisine | 8,228 (North Indian) to 8,452 (Desserts) |
| Average order value | 547.73 (currency assumed to be INR) |
| Repeat rate with / without discount | 49.96% / 49.98% |
| Statistical tests | 0 of 8 significant at 5% |
| Repeat-order models | accuracy about 50% (baseline 50.0%), ROC-AUC about 0.50 |
| Rating models (5 classes) | accuracy about 19-20% (baseline 20.1%) |
| Order-value regression | R2 about 0, MAE about 223.6 (baseline 223.6) |
| K-Means silhouette | 0.14-0.15 for k = 2 to 7 (weak structure) |

**Conclusion:** the attributes show no usable predictive signal; models perform at chance level. The data may be simulated. Richer data (item prices, order history, timestamps) is needed for real prediction.

## Notes
* `random_state = 42` is used throughout, so results are reproducible.
* Age bands (Gen-Z <= 24, Millennial 25-40, Adult 41+) are derived in the notebook; the dataset has ages 18-44 only.
* SQL queries are standard and MySQL 8 compatible. They were tested on SQLite; run them once in MySQL to confirm on your setup.
