# Food Ordering Behaviour and Consumer Trends

A full-stack upgrade of the original food-ordering analytics project. The original dataset, Jupyter/analysis workflow (where maintained separately), Tableau workbook, report, and visualizations are preserved. This version adds a Flask web application with SQLite-backed user accounts and an analytics dashboard.

## Technology stack

- **Frontend:** HTML, CSS, JavaScript, Chart.js
- **Backend:** Python, Flask
- **Database:** SQLite3 (Python's built-in `sqlite3` module)
- **Data analysis:** Jupyter Notebook, pandas and NumPy
- **Dashboard analytics:** pandas + Chart.js
- **Authentication:** Werkzeug password hashing and Flask signed sessions

## Features

- User registration and login
- Passwords stored as secure hashes, never plaintext
- Login-protected dashboard and logout
- SQLite database created automatically on first app start
- Dashboard KPIs and charts generated from the project CSV
- Existing dataset and original project assets remain in the repository

## Project structure

```
app.py
config.py
requirements.txt
.env.example
schema.sql
Data/
  food_ordering_behavior_dataset.csv
templates/
  base.html
  index.html
  login.html
  register.html
  dashboard.html
static/
  css/style.css
  js/dashboard.js
instance/
  food_ordering.sqlite3   # generated automatically; keep local/private
```

> The current GitHub repository contains the CSV dataset but does not currently contain a Jupyter `.ipynb` notebook or an existing SQLite analysis database. The web app therefore leaves your notebook untouched and uses the same CSV for dashboard analytics. SQLite stores the app's user accounts. If you later add your notebook/database to the project, the dashboard can be connected to its analysis tables or exported results.

## Setup (Windows)

1. Install Python 3.10+.
2. Clone this repository and open its folder in a terminal.
3. Create and activate a virtual environment:

   ```powershell
   py -m venv .venv
   .venv\\Scripts\\Activate.ps1
   ```

4. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

5. Copy `.env.example` to `.env` and set a long random `SECRET_KEY`. You do not need MySQL Server or MySQL Workbench.
6. Start the app:

   ```powershell
   python app.py
   ```

7. Open http://127.0.0.1:5000 and create an account. The SQLite database and users table are created automatically in the `instance` folder.

## Configuration

- `SECRET_KEY`: long, random Flask session signing key
- `DATABASE_PATH`: SQLite database file path (defaults to `instance/food_ordering.sqlite3`)
- `DATASET_PATH`: CSV path (defaults to `Data/food_ordering_behavior_dataset.csv`)
- `COOKIE_SECURE`: set to `true` only when deployed behind HTTPS

Never commit your real `.env` file or a production database containing user information.

## Authentication flow

1. Registration validates the name, email and password.
2. Werkzeug hashes the password before it is stored in SQLite.
3. Login retrieves the stored hash and verifies the submitted password.
4. On successful login, Flask stores the user's ID and basic profile details in its signed session cookie. The password is never stored in the cookie.
5. Protected routes use a login-required decorator. Logout clears the session.

For production, use HTTPS, a strong secret key, secure cookie settings, CSRF protection, rate limiting and suitable database backups.

## Analytics and Jupyter workflow

Your Jupyter Notebook remains a separate analysis workspace. The Flask dashboard currently reads the same source CSV using pandas and generates its own summary metrics and chart data. It does not rewrite or execute the notebook. The SQLite database created by Flask is currently used for authentication.

If your notebook already creates analysis tables in a separate SQLite database, set `DATABASE_PATH` to that database only after confirming it contains (or can safely contain) the `users` table. A cleaner next step is to keep authentication in `food_ordering.sqlite3` and have the dashboard read selected analysis tables from your notebook database using a separate read-only SQLite connection.

## Existing project assets

The original Tableau workbook, project report, visualizations, and source dataset are retained. This Flask dashboard is an additional application layer, not a replacement for your existing analysis.

## Current status

The Flask authentication layer and dashboard foundation use SQLite3. Next steps are to verify the dataset's exact column names, connect the notebook's actual SQLite analysis outputs (if you want the dashboard to use them), add filters and automated tests, and prepare deployment.
