"""CSV-adaptive, owner-authenticated analytics dashboard."""
from functools import wraps
from io import BytesIO
import os
from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd
from flask import Flask, Response, flash, jsonify, redirect, render_template, request, session, url_for
from scipy.stats import chi2_contingency, ttest_ind
from werkzeug.security import check_password_hash, generate_password_hash

ROOT = Path(__file__).resolve().parent
SAMPLE_DATA = ROOT / "data" / "food_ordering_behavior_dataset.csv"
DB_PATH = ROOT / "instance" / "owners.sqlite3"
MAX_UPLOAD = 25 * 1024 * 1024
ROLES = {
    "sales": ["sales", "revenue", "order_value", "total_amount", "order_amount", "net_sales", "gross_sales", "amount", "spend", "value", "total", "price", "subtotal", "invoice_amount"],
    "date": ["date", "order_date", "order_datetime", "created_at", "timestamp", "datetime", "transaction_date", "purchase_date", "sale_date"],
    "category": ["category", "cuisine", "meal_type", "product_category", "item_category", "department", "segment", "type"],
    "product": ["product", "product_name", "item", "item_name", "menu_item", "dish", "sku", "service", "product_id"],
    "location": ["city", "location", "region", "area", "branch", "store", "outlet", "state", "country"],
    "quantity": ["quantity", "qty", "units", "unit_sold", "units_sold", "items_sold", "count_sold"],
    "rating": ["rating", "rating_given", "review_score", "stars", "satisfaction", "customer_rating"],
    "customer": ["customer_id", "user_id", "client_id", "customer", "user", "buyer_id"],
    "order_id": ["order_id", "transaction_id", "bill_id", "invoice_id", "order_no", "receipt_id"],
    "discount": ["discount", "discount_applied", "promo", "coupon", "promotion"],
    "repeat": ["repeat", "is_repeat_order", "repeat_order", "returning_customer", "repeat_customer"],
    "status": ["status", "order_status", "payment_status", "fulfillment_status"],
}
ROLE_LABELS = {"sales": "Sales / amount", "date": "Date or time", "category": "Category", "product": "Product or item", "location": "Location", "quantity": "Quantity", "rating": "Rating", "customer": "Customer ID", "order_id": "Order ID", "discount": "Discount or promotion", "repeat": "Repeat customer / order", "status": "Order status"}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD
app.secret_key = os.environ.get("TABLEWISE_SECRET_KEY", "local-dev-key-change-before-deployment")


def connect():
    DB_PATH.parent.mkdir(exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def init_db():
    with connect() as db:
        db.execute("CREATE TABLE IF NOT EXISTS owners (id INTEGER PRIMARY KEY, business TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS owner_datasets (owner_id INTEGER PRIMARY KEY REFERENCES owners(id), filename TEXT NOT NULL, csv_data BLOB NOT NULL, uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP)")


def owner_only(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "owner_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Please sign in again."}), 401
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def normalize(frame):
    names = ["_".join(str(col).replace("\ufeff", "").strip().lower().replace("-", " ").split()) or f"column_{i+1}" for i, col in enumerate(frame.columns)]
    seen = {}
    unique = []
    for name in names:
        seen[name] = seen.get(name, 0) + 1
        unique.append(name if seen[name] == 1 else f"{name}_{seen[name]}")
    frame.columns = unique
    return frame


def parse_csv(raw):
    encoding = "utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
    try:
        return pd.read_csv(BytesIO(raw), sep=None, engine="python", encoding=encoding)
    except UnicodeDecodeError:
        return pd.read_csv(BytesIO(raw), sep=None, engine="python", encoding="latin-1")


def read_owner_data(owner_id):
    with connect() as db:
        saved = db.execute("SELECT filename,csv_data,uploaded_at FROM owner_datasets WHERE owner_id=?", (owner_id,)).fetchone()
    if saved:
        data = pd.read_csv(BytesIO(saved["csv_data"]))
        return normalize(data), {"source": "uploaded", "filename": saved["filename"], "uploaded_at": saved["uploaded_at"]}
    return normalize(pd.read_csv(SAMPLE_DATA)), {"source": "sample", "filename": SAMPLE_DATA.name, "uploaded_at": None}


def infer_roles(frame):
    cols = list(frame.columns)
    roles = {role: "" for role in ROLES}
    used = set()
    # Prefer exact header matches. This protects fields such as order_id from being mistaken for sales.
    for role, aliases in ROLES.items():
        for alias in aliases:
            if alias in cols and alias not in used:
                roles[role] = alias
                used.add(alias)
                break
    # Match familiar words in less standardized headers such as "Order Total (INR)".
    for role, aliases in ROLES.items():
        if roles[role]:
            continue
        for col in cols:
            if col in used:
                continue
            if any(alias in col.split("_") or (len(alias) > 4 and alias in col) for alias in aliases):
                roles[role] = col
                used.add(col)
                break
    # Fall back to value shapes when a header is unfamiliar.
    if not roles["date"]:
        for col in cols:
            if pd.api.types.is_numeric_dtype(frame[col]):
                continue
            if not any(token in col for token in ("date", "time", "stamp")) and numeric_series(frame[col]).notna().mean() > .8:
                continue
            parsed = pd.to_datetime(frame[col], errors="coerce")
            if len(frame) and parsed.notna().mean() >= .8:
                roles["date"] = col
                used.add(col)
                break
    numeric = {}
    for col in cols:
        values = numeric_series(frame[col])
        if values.notna().mean() >= .7:
            numeric[col] = values
    if not roles["rating"]:
        for col, values in numeric.items():
            nonnull = values.dropna()
            if len(nonnull) and nonnull.between(0, 5).mean() >= .95 and nonnull.nunique() <= 11:
                roles["rating"] = col
                used.add(col)
                break
    if not roles["sales"]:
        candidates = [(col, val) for col, val in numeric.items() if col not in used and val.nunique() > 5 and not any(x in col for x in ("id", "age", "year", "zip", "postal"))]
        if candidates:
            roles["sales"] = max(candidates, key=lambda pair: pair[1].nunique())[0]
            used.add(roles["sales"])
    if not roles["quantity"]:
        for col, values in numeric.items():
            if col not in used and any(x in col for x in ("quantity", "qty", "unit", "count", "volume")) and len(values.dropna()) and (values.dropna() % 1 == 0).mean() > .95 and values.min() >= 0:
                roles["quantity"] = col
                used.add(col)
                break
    for role in ("category", "product", "location"):
        if roles[role]:
            continue
        candidates = [col for col in cols if col not in used and 2 <= frame[col].nunique(dropna=True) <= min(60, max(12, len(frame) // 5)) and not pd.api.types.is_numeric_dtype(frame[col])]
        if candidates:
            roles[role] = candidates[0]
            used.add(candidates[0])
    return roles


def numeric_series(series):
    cleaned = series.astype(str).str.replace(",", "", regex=False).str.extract(r"(-?\d+(?:\.\d+)?|-?\.\d+)", expand=False)
    values = pd.to_numeric(cleaned, errors="coerce")
    return values.replace([np.inf, -np.inf], np.nan)


def get_roles(frame):
    roles = infer_roles(frame)
    for role in ROLES:
        selected = request.args.get(f"role_{role}")
        if selected in frame.columns or selected == "":
            roles[role] = selected
    return roles


def apply_filters(frame):
    filter_cols = []
    for col in frame.columns:
        unique = frame[col].nunique(dropna=True)
        if 1 < unique <= 40 and (not pd.api.types.is_numeric_dtype(frame[col]) or unique <= 15):
            filter_cols.append(col)
            selected = request.args.get(f"filter_{col}", "All")
            if selected != "All":
                frame = frame[frame[col].astype(str) == selected]
    return frame, filter_cols


def table_rows(frame):
    return frame.astype(object).where(pd.notna(frame), None).to_dict("records")


def as_num(value):
    if pd.isna(value):
        return None
    return float(value)


@app.get("/")
def index():
    return redirect(url_for("dashboard" if "owner_id" in session else "login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        business = request.form.get("business", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not business or not email or len(password) < 8:
            flash("Add your business name, email, and a password of at least 8 characters.", "error")
        else:
            try:
                with connect() as db:
                    cur = db.execute("INSERT INTO owners(business,email,password_hash) VALUES(?,?,?)", (business, email, generate_password_hash(password)))
                session["owner_id"], session["business"] = cur.lastrowid, business
                return redirect(url_for("dashboard"))
            except sqlite3.IntegrityError:
                flash("That email already has an account. Please sign in.", "error")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        with connect() as db:
            owner = db.execute("SELECT * FROM owners WHERE email=?", (request.form.get("email", "").strip().lower(),)).fetchone()
        if owner and check_password_hash(owner["password_hash"], request.form.get("password", "")):
            session.clear()
            session["owner_id"], session["business"] = owner["id"], owner["business"]
            return redirect(url_for("dashboard"))
        flash("Email or password was not recognized.", "error")
    return render_template("login.html")


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.get("/dashboard")
@owner_only
def dashboard():
    frame, meta = read_owner_data(session["owner_id"])
    return render_template("dashboard.html", business=session.get("business", "Restaurant"), meta=meta, row_count=len(frame))


@app.post("/upload")
@owner_only
def upload():
    file = request.files.get("dataset")
    if not file or not file.filename:
        flash("Choose a CSV file to upload.", "error")
        return redirect(url_for("dashboard"))
    if Path(file.filename).suffix.lower() != ".csv":
        flash("Please upload a CSV file.", "error")
        return redirect(url_for("dashboard"))
    raw = file.read(MAX_UPLOAD + 1)
    if len(raw) > MAX_UPLOAD:
        flash("The file is larger than the 25 MB upload limit.", "error")
        return redirect(url_for("dashboard"))
    try:
        frame = normalize(parse_csv(raw))
        frame = frame.dropna(how="all")
        if frame.empty or not len(frame.columns):
            raise ValueError("the file has no data rows")
    except Exception as exc:
        flash(f"We could not read that CSV: {exc}", "error")
        return redirect(url_for("dashboard"))
    stored = frame.to_csv(index=False).encode("utf-8")
    with connect() as db:
        db.execute("INSERT INTO owner_datasets(owner_id,filename,csv_data,uploaded_at) VALUES(?,?,?,CURRENT_TIMESTAMP) ON CONFLICT(owner_id) DO UPDATE SET filename=excluded.filename,csv_data=excluded.csv_data,uploaded_at=CURRENT_TIMESTAMP", (session["owner_id"], Path(file.filename).name, stored))
    flash(f"Uploaded {Path(file.filename).name}: {len(frame):,} rows ready. Review the suggested column mappings below.", "success")
    return redirect(url_for("dashboard"))


@app.post("/use-sample")
@owner_only
def use_sample():
    with connect() as db:
        db.execute("DELETE FROM owner_datasets WHERE owner_id=?", (session["owner_id"],))
    flash("Sample dataset restored.", "success")
    return redirect(url_for("dashboard"))


@app.get("/api/analytics")
@owner_only
def analytics():
    full, meta = read_owner_data(session["owner_id"])
    roles = get_roles(full)
    frame, filter_cols = apply_filters(full.copy())
    if frame.empty:
        return jsonify({"error": "No rows match these filters."}), 400
    columns = list(full.columns)
    for role in ("sales", "quantity", "rating"):
        col = roles[role]
        if col:
            frame[col] = numeric_series(frame[col])
            full[col] = numeric_series(full[col])
    sales_col, qty_col, date_col = roles["sales"], roles["quantity"], roles["date"]
    sales = frame[sales_col].dropna() if sales_col else pd.Series(dtype=float)
    amount_sum = float(sales.sum()) if len(sales) else None
    order_count = int(frame[roles["order_id"]].nunique()) if roles["order_id"] else len(frame)
    kpis = [{"label": "Rows analyzed", "value": f"{len(frame):,}", "note": f"of {len(full):,} rows in this file"}]
    if sales_col:
        kpis += [{"label": "Total " + ROLE_LABELS["sales"], "value": amount_sum, "format": "money", "note": f"Column: {sales_col}"}, {"label": "Average per row", "value": float(sales.mean()) if len(sales) else None, "format": "money", "note": "Mean of detected sales values"}]
    if roles["order_id"]:
        kpis.append({"label": "Unique transactions", "value": order_count, "note": f"Column: {roles['order_id']}"})
    elif roles["customer"]:
        kpis.append({"label": "Unique customers", "value": int(frame[roles["customer"]].nunique()), "note": f"Column: {roles['customer']}"})
    elif qty_col:
        q = numeric_series(frame[qty_col]).sum()
        kpis.append({"label": "Units", "value": int(q) if pd.notna(q) else None, "note": f"Column: {qty_col}"})
    charts, insights = [], []
    if sales_col and len(sales) > 1:
        counts, edges = np.histogram(sales, bins=min(10, max(3, int(np.sqrt(len(sales))))) if sales.nunique() > 2 else max(1, sales.nunique()))
        bin_labels = [f"{edges[i]:,.2f} to {edges[i+1]:,.2f}" for i in range(len(counts))]
        charts.append({"title": f"Distribution of {sales_col.replace('_',' ')}", "subtitle": "How values are spread across the file", "type": "bar", "labels": bin_labels, "values": counts.astype(int).tolist(), "format": "number"})
    if roles["location"]:
        col = roles["location"]
        grouped = frame.groupby(col, dropna=True).agg(rows=(col, "size"), value=(sales_col, "sum") if sales_col else (col, "size")).sort_values("rows", ascending=False).head(12)
        charts.append({"title": f"Activity by {col.replace('_',' ')}", "subtitle": "Top groups in the current selection", "type": "bar", "labels": grouped.index.astype(str).tolist(), "values": grouped.value.tolist(), "format": "money" if sales_col else "number", "horizontal": True})
        insights.append({"label": "Largest location group", "value": str(grouped.index[0]), "detail": f"{int(grouped.rows.iloc[0]):,} rows"})
    group_col = roles["category"] or roles["product"]
    if group_col:
        metric = sales_col or qty_col
        grouped = frame.groupby(group_col, dropna=True)[metric].sum().sort_values(ascending=False).head(12) if metric else frame[group_col].value_counts().head(12)
        charts.append({"title": f"{('Sales' if sales_col else 'Quantity' if qty_col else 'Rows')} by {group_col.replace('_',' ')}", "subtitle": "Highest values first", "type": "bar", "labels": grouped.index.astype(str).tolist(), "values": grouped.tolist(), "format": "money" if sales_col else "number", "horizontal": True})
        insights.append({"label": "Top " + group_col.replace("_", " "), "value": str(grouped.index[0]) if len(grouped) else "No values", "detail": f"{grouped.iloc[0]:,.2f} in detected metric" if len(grouped) else ""})
    if date_col:
        dates = pd.to_datetime(frame[date_col], errors="coerce")
        valid = frame.loc[dates.notna()].copy()
        if not valid.empty:
            parsed_dates = pd.to_datetime(valid[date_col], errors="coerce")
            period = parsed_dates.dt.to_period("W").astype(str) if parsed_dates.dt.date.nunique() > 90 else parsed_dates.dt.date.astype(str)
            valid["_period"] = period
            measure = sales_col or qty_col
            trend = valid.groupby("_period")[measure].sum().sort_index() if measure else valid.groupby("_period").size().sort_index()
            charts.append({"title": "Activity over time", "subtitle": f"Grouped by date from {date_col}", "type": "line", "labels": trend.index.tolist(), "values": trend.astype(float).tolist(), "format": "money" if sales_col else "number"})
            insights.append({"label": "Date coverage", "value": f"{len(trend)} dates", "detail": f"{trend.index[0]} to {trend.index[-1]}"})
    if roles["rating"]:
        col = roles["rating"]
        rating = numeric_series(frame[col]).dropna()
        if len(rating):
            distribution = rating.value_counts().sort_index()
            charts.append({"title": "Rating distribution", "subtitle": f"Average score: {rating.mean():.2f}", "type": "bar", "labels": distribution.index.astype(str).tolist(), "values": distribution.astype(int).tolist(), "format": "number"})
            kpis.append({"label": "Average rating", "value": float(rating.mean()), "note": f"Column: {col}"})
    if roles["discount"] and sales_col:
        col = roles["discount"]
        grouped = frame.groupby(col)[sales_col].mean().sort_values(ascending=False)
        charts.append({"title": f"Average sales by {col.replace('_',' ')}", "subtitle": "Group differences are descriptive", "type": "bar", "labels": grouped.index.astype(str).tolist(), "values": grouped.astype(float).tolist(), "format": "money"})
    if roles["repeat"]:
        col = roles["repeat"]
        distribution = frame[col].astype(str).value_counts()
        charts.append({"title": f"Distribution of {col.replace('_',' ')}", "subtitle": "Counts in the selected rows", "type": "doughnut", "labels": distribution.index.astype(str).tolist(), "values": distribution.astype(int).tolist(), "format": "number"})
    if not insights:
        insights.append({"label": "Dataset loaded", "value": f"{len(frame):,} rows", "detail": "Choose field mappings below to build more specific analysis."})
    insights += [{"label": "Columns recognized", "value": f"{sum(bool(v) for v in roles.values())} fields", "detail": ", ".join(f"{ROLE_LABELS[k]}: {v}" for k, v in roles.items() if v) or "No familiar field names found"}]
    if sales_col:
        check_values = numeric_series(frame[sales_col])
        insights.append({"label": "Data check", "value": f"{int(check_values.isna().sum()):,} non-numeric values", "detail": f"in the selected {sales_col} column"})
    missing_cells = int(frame.isna().sum().sum())
    duplicate_rows = int(frame.duplicated().sum())
    insights.append({"label": "File quality", "value": f"{missing_cells:,} blank cells", "detail": f"{duplicate_rows:,} duplicate rows in the current selection"})
    table_col = group_col or roles["location"]
    table = {"headers": [], "rows": []}
    if table_col:
        agg = {"row_count": (table_col, "size")}
        if sales_col: agg["total_value"] = (sales_col, "sum")
        if qty_col: agg["total_quantity"] = (qty_col, "sum")
        summary = frame.groupby(table_col, dropna=True).agg(**agg).sort_values("row_count", ascending=False).head(50).reset_index()
        table = {"headers": [table_col.replace("_", " ").title()] + [x.replace("_", " ").title() for x in summary.columns if x != table_col], "rows": [[str(r[table_col])] + [as_num(r[c]) for c in summary.columns if c != table_col] for _, r in summary.iterrows()]}
    else:
        preview = frame.head(50).copy()
        table = {"headers": [c.replace("_", " ").title() for c in preview.columns], "rows": [[str(v) for v in row] for row in preview.fillna("").itertuples(index=False, name=None)]}
    filter_data = {}
    for col in filter_cols:
        values = sorted(full[col].dropna().astype(str).unique().tolist())
        filter_data[col] = values[:40]
    return jsonify({"meta": meta, "columns": columns, "roles": roles, "role_labels": ROLE_LABELS, "filters": filter_data, "kpis": kpis, "charts": charts, "insights": insights, "table": table, "row_count": len(frame), "total_rows": len(full)})


@app.get("/export.csv")
@owner_only
def export_csv():
    full, _ = read_owner_data(session["owner_id"])
    frame, _ = apply_filters(full)
    return Response(frame.to_csv(index=False), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=restaurant_analysis.csv"})


@app.get("/sample.csv")
def sample_csv():
    return Response(SAMPLE_DATA.read_bytes(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=food_ordering_behavior_dataset.csv"})


@app.get("/privacy")
def privacy():
    return render_template("policy.html", page="Privacy", title="Privacy")


@app.get("/terms")
def terms():
    return render_template("policy.html", page="Terms", title="Terms")


@app.errorhandler(413)
def too_large(_error):
    flash("The upload is larger than the 25 MB limit.", "error")
    return redirect(url_for("dashboard"))


init_db()
if __name__ == "__main__":
    app.run(debug=True)
