from flask import Blueprint, abort, render_template, request, url_for
from flask_login import current_user

from sstq.auth_decorators import login_required

scan_picture_bp = Blueprint("scan_picture", __name__)


@scan_picture_bp.route("/scan_picture", methods=["GET"])
@login_required
def scan_picture():
    targets = {
        "product_edit": {
            "return_url": lambda barcode: url_for("product.product_edit", barcode=barcode),
            "title": "Take Product Picture",
            "description": "Capture a product picture and return to the edit page before saving.",
        },
        "product_add": {
            "return_url": lambda barcode: url_for("product.product_add", barcode=barcode),
            "title": "Take Product Picture",
            "description": "Capture a product picture and return to add product before saving.",
        },
    }

    target = (request.args.get("target") or "").strip()
    barcode = (request.args.get("barcode") or "").strip()
    config = targets.get(target)
    if not config:
        abort(404)

    if not (current_user.is_admin or current_user.is_verifier):
        abort(403)

    return render_template(
        "scan_picture.html",
        target=target,
        barcode=barcode,
        return_url=config["return_url"](barcode),
        page_title=config["title"],
        description=config["description"],
    )
