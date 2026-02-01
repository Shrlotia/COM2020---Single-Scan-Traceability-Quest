# imports all tools for requesting and responding to HTTP requests, as well as the 'app' and 'db' elements
import json
from pathlib import Path

from flask import render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from config import app, db
from models import User

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# connects to the index (/) of the web app and shows the default view
@app.route("/", methods=["GET"])
def home():
    return render_template("home.html")

# basic scan page
@app.route("/scan", methods=["GET", "POST"])
@login_required
def scan():
    if request.method == "GET":
        return render_template("scan.html")
    elif request.method == "POST":
        barcode = request.form.get("barcode", "").strip()
        
        if not barcode:
            return redirect(url_for("scan"))

        return redirect(url_for("product", barcode=barcode))

# simple product page that receives the detected barcode
@app.route("/product/<barcode>", methods=["GET"])
@login_required
def product(barcode: str):
    normalized = normalize_barcode(barcode)
    product_name = lookup_product_name(normalized)
    return render_template("product.html", barcode=normalized, product_name=product_name)

# basic scan page
@app.route("/timeline", methods=["GET"])
@login_required
def timeline():
    return render_template("timeline.html")

# basic scan page
@app.route("/trace_quest", methods=["GET"])
@login_required
def tracequest():
    return render_template("tracequest.html")

@app.route("/profile", methods=["GET"])
@login_required
def profile():
    return render_template("profile.html")

# basic scan page
@app.route("/add_product", methods=["GET"])
@login_required
def add():
    return render_template("add.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    elif request.method == "POST":
        action = request.form.get("action")
        username = request.form.get("username")
        password = request.form.get("password")
        
        if not username or not password:
            flash("Username and password required", "error")
            return redirect(url_for("login"))
        
        user = User.query.filter_by(username=username).first()
            
        if action == "login":
            if not user or not user.check_password(password):
                flash("Invalid username or password", "error")
                return redirect(url_for("login"))
            else:
                login_user(user)
                return redirect(url_for("home"))
            
        if action == "register":
            role = "verifier" if (request.form.get("is_verifier") is not None) else "consumer"
            
            if user:
                flash("Username already exists: Pick another", "error")
                return redirect(url_for("login"))
            else:
                new_user = User(username=username, role=role)
                new_user.set_password(password)
                
                db.session.add(new_user)
                db.session.commit()
                
                login_user(new_user)
                flash("Account successfully created", "success")
                return redirect(url_for("home"))
            
@app.route("/logout", methods=["GET"])
@login_required
def logout():
    logout_user()  
    flash("You have been logged out", "success")
    return redirect(url_for("home"))

@app.route("/admin", methods=["GET"])
@login_required
def admin():
    return render_template("admin.html")

# local data file containing barcodes and product names
OFF_DATA_PATH = Path(__file__).with_name("SimplifiedOFFData.jsonl")

# lightweight in-memory index: barcode -> product_name
PRODUCT_INDEX: dict[str, str] = {}
PRODUCT_INDEX_READY = False

def normalize_barcode(value: str) -> str:
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    if len(digits) == 12:
        # UPC-A is often represented as EAN-13 with a leading 0.
        return f"0{digits}"
    return digits or str(value)

def ensure_product_index() -> None:
    global PRODUCT_INDEX_READY
    if PRODUCT_INDEX_READY:
        return

    if not OFF_DATA_PATH.exists():
        PRODUCT_INDEX_READY = True
        return

    with OFF_DATA_PATH.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue

            code = normalize_barcode(item.get("code", ""))
            name = (item.get("product_name") or "").strip()
            if code and name and code not in PRODUCT_INDEX:
                PRODUCT_INDEX[code] = name

    PRODUCT_INDEX_READY = True

def lookup_product_name(barcode: str) -> str | None:
    ensure_product_index()
    normalized = normalize_barcode(barcode)

    # Try the normalized code first, then a UPC-A variant without a leading 0.
    product_name = PRODUCT_INDEX.get(normalized)
    if not product_name and len(normalized) == 13 and normalized.startswith("0"):
        product_name = PRODUCT_INDEX.get(normalized[1:])

    return product_name

# when this file is ran, the DB is created and application is started
if __name__ == "__main__":  
    with app.app_context():
        db.create_all()
        
    # Listen on all interfaces so the app is reachable from your phone on the same Wi-Fi.
    # does not work on mobile no matter what I try, might have to fix later
    app.run(debug=True, host="0.0.0.0", port=5000)
