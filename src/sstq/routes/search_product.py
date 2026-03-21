from flask import Blueprint, render_template, redirect, url_for, request
from sstq.auth_decorators import login_required

search_product_bp = Blueprint("search_product", __name__)

# endpoint that allows the user to enter in or scan a barcode for a product
@search_product_bp.route("/search_product", methods=["GET", "POST"])
@login_required # means you cannot access this page without being authenticated
def search_product():
    barcode = request.args.get("barcode", "").strip()

    # if we want to see the main scan page, we load it in this branch
    if request.method == "GET":
        return render_template("search_product.html", initial_barcode=barcode)
    # once we scan the barcode, we can process it and show the product info
    elif request.method == "POST":
        # if the barcode is empty, the value is set to ""
        barcode = request.form.get("barcode", "").strip()
        
        # keeps refreshing the scan page if the barcode is not valid (empty)
        if not barcode:
            return redirect(url_for("search_product.search_product"))

        # if the barcode is valid, we send it the the '/product/<barcode>' endpoint to be displayed
        return redirect(url_for("product.product_detail", barcode=barcode))
