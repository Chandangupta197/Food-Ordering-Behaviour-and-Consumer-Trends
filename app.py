import os
import re
from functools import wraps

import pandas as pd
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_mysqldb import MySQL
from werkzeug.security import check_password_hash, generate_password_hash

from config import Config

app = Flask(__name__)
app.config.from_object(Config)
mysql = MySQL(app)

EMAIL_RE = re.compile(r"^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def get_dataset():
    path = os.getenv("DATASET_PATH", "Data/food_ordering_behavior_dataset.csv")
    if not os.path.isfile(path):
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except (OSError, pd.errors.ParserError, UnicodeDecodeError):
        return pd.DataFrame()


def find_column(df, candidates):
    lookup = {str(col).strip().lower().replace("_", " "): col for col in df.columns}
    for candidate in candidates:
        key = candidate.lower().replace("_", " ")
        if key in lookup:
            return lookup[key]
    return None


def top_counts(df, candidates, limit=7):
    col = find_column(df, candidates)
    if col is None:
        return {"labels": [], "values": []}
    counts = df[col].dropna().astype(str).value_counts().head(limit)
    return {"labels": counts.index.tolist(), "values": counts.astype(int).tolist()}


def dashboard_data():
    df = get_dataset()
    if df.empty:
        return {
            "total_orders": 0, "total_revenue": 0, "avg_rating": None,
            "avg_delivery": None, "cuisine": {"labels": [], "values": []},
            "city": {"labels": [], "values": []},
            "meal": {"labels": [], "values": []},
            "dataset_warning": "Dataset could not be loaded. Check DATASET_PATH."
        }

    revenue_col = find_column(df, ["revenue", "order value", "amount", "total"])
    rating_col = find_column(df, ["customer rating", "rating", "ratings"])
    delivery_col = find_column(df, ["delivery time", "delivery_time", "delivery minutes"])
    numeric = lambda col: pd.to_numeric(df[col], errors="coerce") if col else pd.Series(dtype=float)

    revenue = numeric(revenue_col)
    ratings = numeric(rating_col)
    delivery = numeric(delivery_col)
    return {
        "total_orders": int(len(df)),
        "total_revenue": round(float(revenue.sum()), 2) if revenue_col else 0,
        "avg_rating": round(float(ratings.mean()), 2) if ratings.notna().any() else None,
        "avg_delivery": round(float(delivery.mean()), 2) if delivery.notna().any() else None,
        "cuisine": top_counts(df, ["cuisine type", "cuisine"]),
        "city": top_counts(df, ["city", "customer city"]),
        "meal": top_counts(df, ["meal type", "meal"]),
        "dataset_warning": None
    }


@app.get("/")
def index():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or len(name) > 100 or not EMAIL_RE.match(email):
            flash("Enter a valid name and email address.", "danger")
            return render_template("register.html")
        if len(password) < 8:
            flash("Password must contain at least 8 characters.", "danger")
            return render_template("register.html")
        cur = mysql.connection.cursor()
        try:
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cur.fetchone():
                flash("An account with this email already exists.", "warning")
                return render_template("register.html")
            password_hash = generate_password_hash(password)
            cur.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)",
                (name, email, password_hash)
            )
            mysql.connection.commit()
            flash("Account created. You can now log in.", "success")
            return redirect(url_for("login"))
        except Exception:
            mysql.connection.rollback()
            app.logger.exception("Registration failed")
            flash("Could not create the account. Check the database setup.", "danger")
        finally:
            cur.close()
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        cur = mysql.connection.cursor()
        try:
            cur.execute("SELECT id, name, email, password_hash FROM users WHERE email = %s", (email,))
            user = cur.fetchone()
        finally:
            cur.close()
        if user and check_password_hash(user[3], password):
            session.clear()
            session["user_id"] = user[0]
            session["user_name"] = user[1]
            session["user_email"] = user[2]
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")


@app.get("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", metrics=dashboard_data())


@app.post("/logout")
@login_required
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


if __name__ == "__main__":
    # Debug is for local development only. Disable it in production.
    app.run(host="127.0.0.1", port=5000, debug=True)
