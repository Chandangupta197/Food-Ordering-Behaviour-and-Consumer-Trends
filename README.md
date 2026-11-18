# Food Ordering Behaviour and Consumer Trends

A full-stack upgrade of the original food-ordering analytics project. The existing dataset and Tableau work are retained; this version adds a Flask web application, MySQL-backed user accounts, secure password hashing, session-based authentication, and an interactive analytics dashboard.

## Technology stack

- **Frontend:** HTML, CSS, JavaScript, Chart.js
- **Backend:** Python, Flask
- **Database:** MySQL
- **Data analysis:** pandas
- **Authentication:** Werkzeug password hashing and Flask signed sessions

## Features

- User registration and login
- Passwords stored as hashes (never plaintext)
- Login-protected dashboard and logout
- Session cookie security settings configurable through environment variables
- Dashboard KPIs and charts generated from the project CSV
- Existing Tableau workbook, report, visualizations, and dataset remain part of the repository

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
```

## Setup (Windows)

1. Install Python 3.10+ and MySQL Server.
2. Clone this repository and open its folder in a terminal.
3. Create and activate a virtual environment:

   ```powershell
   py -m venv .venv
   .venv\\Scripts\\Activate.ps1
   ```

4. Install packages:

   ```powershell
   pip install -r requirements.txt
   ```

5. Create a MySQL database and tables by running `schema.sql` in MySQL Workbench or the MySQL CLI.
6. Copy `.env.example` to `.env` and set your local database credentials and a long random `SECRET_KEY`. Never commit `.env`.
7. Start the app:

   ```powershell
   python app.py
   ```

8. Open http://127.0.0.1:5000 and create an account.

## Configuration

The app reads these variables from `.env`:

- `SECRET_KEY`: long, random Flask session signing key
- `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`: MySQL connection settings
- `DATASET_PATH`: optional path to the CSV (defaults to `Data/food_ordering_behavior_dataset.csv`)
- `COOKIE_SECURE`: set to `true` only when deployed behind HTTPS

## Authentication flow

1. Registration validates the form and checks whether the email already exists.
2. The password is hashed with Werkzeug's password-hashing helper before it is stored in MySQL.
3. Login retrieves the user's hash and verifies the submitted password against it.
4. On successful login, the Flask session stores the user's ID and email. The browser receives a signed session cookie; the password is not placed in the cookie.
5. Protected routes use the login-required decorator. Logout clears the session.

For production deployment, use HTTPS, a strong secret key, secure cookie settings, CSRF protection, rate limiting, and database credentials managed outside source control.

## Analytics

The dashboard reads the existing CSV with pandas and computes summary metrics and chart data. It attempts to recognize common column names for cuisine, city, meal type, revenue/order value, rating, and delivery time. If a column in the dataset uses a different name, update the candidate lists in `app.py`.

## Existing project assets

The original Tableau workbook, project report, visualizations, and source dataset are retained. The Flask dashboard is an additional application layer, not a replacement for the original analysis.

## Current status

This is the initial full-stack foundation. Next development steps: verify the CSV's exact column names, add data-import/refresh controls, add analytics filters, write automated tests, and prepare deployment.
