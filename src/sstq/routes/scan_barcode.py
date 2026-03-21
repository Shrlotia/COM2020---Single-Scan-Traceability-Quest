from flask import Blueprint, abort, render_template, request, url_for
from flask_login import current_user

from sstq.auth_decorators import login_required

scan_barcode_bp = Blueprint("scan_barcode", __name__)


@scan_barcode_bp.route("/scan_barcode", methods=["GET"])
@login_required
def scan_barcode():
    targets = {
        "search_product": {
            "return_url": url_for("search_product.search_product"),
            "title": "Scan Barcode",
            "description": "Scan a barcode and return to product search.",
        },
        "product_add": {
            "return_url": url_for("product.product_add"),
            "title": "Scan Barcode for New Product",
            "description": "Scan a barcode and return to add product.",
        },
    }

    target = (request.args.get("target") or "").strip()
    config = targets.get(target)
    if not config:
        abort(404)

    if target == "product_add" and not (current_user.is_admin or current_user.is_verifier):
        abort(403)

    return render_template(
        "scan_barcode.html",
        target=target,
        return_url=config["return_url"],
        page_title=config["title"],
        description=config["description"],
    )
