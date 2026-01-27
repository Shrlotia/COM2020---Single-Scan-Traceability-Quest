# imports all tools for requesting and responding to HTTP requests, as well as the 'app' and 'db' elements
import json
from pathlib import Path

from flask import render_template
from config import app, db

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


# connects to the index (/) of the web app and shows the default view
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

# basic scan page
@app.route("/scan", methods=["GET"])
def scan():
    return render_template("scan.html")

# simple product page that receives the detected barcode
@app.route("/product/<barcode>", methods=["GET"])
def product(barcode: str):
    normalized = normalize_barcode(barcode)
    product_name = lookup_product_name(normalized)
    return render_template(
        "product.html",
        barcode=normalized,
        product_name=product_name,
    )

# when this file is ran, the DB is created and application is started
if __name__ == "__main__":  
    with app.app_context():
        db.create_all()
        
    # Listen on all interfaces so the app is reachable from your phone on the same Wi-Fi.
    app.run(debug=True, host="0.0.0.0", port=5000)
