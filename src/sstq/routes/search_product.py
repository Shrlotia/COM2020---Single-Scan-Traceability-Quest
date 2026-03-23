from flask import Blueprint, redirect, url_for, request
from sstq.auth_decorators import login_required

search_product_bp = Blueprint("search_product", __name__)

@search_product_bp.route("/search_product", methods=["GET", "POST"])
@login_required
def search_product():
    barcode = (request.values.get("barcode") or "").strip()
    if barcode:
        return redirect(url_for("product.product", barcode=barcode))
    return redirect(url_for("product.product"))
