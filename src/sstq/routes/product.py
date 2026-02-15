from flask import Blueprint, render_template, redirect, jsonify, url_for, flash, request, current_app
from flask_login import login_required, current_user

from sstq.extensions import db
from sstq.auth_decorators import roles_required
from sstq.models import Product

product_bp = Blueprint("product", __name__)

# product list page that shows all products in the DB
@product_bp.route("/product", methods=["GET"])
@login_required
def product():
    products = Product.query.order_by(Product.name.asc()).all()
    return render_template("product.html", products=products)


@product_bp.route("/product/<barcode>", methods=["GET"])
@login_required
def product_detail(barcode):
    product = db.session.get(Product, barcode)
    if not product:
        return render_template("error.html", message="Product not found")
    return render_template("product_detail.html", barcode = product.barcode, name = product.name, category = product.category,
                            brand = product.brand, description = product.description, image = product.image)

@product_bp.route("/product/edit/<barcode>", methods=["GET"])
@roles_required("verifier", "admin")
def product_edit(barcode):
    product = db.session.get(Product, barcode)
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for("product.product"))

    return render_template(
        "product_edit.html",
        barcode=product.barcode,
        name=product.name,
        category=product.category,
        brand=product.brand,
        description=product.description,
        image=product.image,
    )

@product_bp.route("/product/edit/<barcode>", methods=["POST"])
@roles_required("verifier", "admin")
def product_update(barcode):
    product = db.session.get(Product, barcode)
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for("product.product"))

    new_barcode = (request.form.get("barcode") or "").strip()
    name = (request.form.get("name") or "").strip()
    category = (request.form.get("category") or "").strip()
    brand = (request.form.get("brand") or "").strip()
    description = (request.form.get("description") or "").strip()
    image = (request.form.get("image") or "").strip()

    if not all([new_barcode, name, category, brand, description]):
        flash("All fields except image are required.", "error")
        return redirect(url_for("product.product_edit", barcode=barcode))

    if new_barcode != barcode and db.session.get(Product, new_barcode):
        flash("Barcode already exists.", "error")
        return redirect(url_for("product.product_edit", barcode=barcode))

    try:
        product.barcode = new_barcode
        product.name = name
        product.category = category
        product.brand = brand
        product.description = description
        product.image = image
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash("Failed to update product.", "error")
        return redirect(url_for("product.product_edit", barcode=barcode))

    flash("Product updated successfully.", "success")
    return redirect(url_for("product.product_detail", barcode=new_barcode))

# endpoint that allows a verifier to add/update products within the DB, adding claims and evidence labels
@product_bp.route("/add_product", methods=["GET", "POST"])
@roles_required("verifier", "admin") # you can only visit this page if your auth user type is 'verifier' or 'admin'
def product_add():
    
    if request.is_json:
        #it will pass the permission check if it is testing  
        if not current_app.config.get("TESTING"):       
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
        
        data = request.get_json()

        if not data or "productData" not in data:
            return jsonify({"success": False}), 400

        product_data = data["productData"]
        barcode = product_data.get("barcode")

        #check for duplicates
        existing = Product.query.filter_by(barcode=barcode).first()
        if existing:
            return jsonify({"success": False}), 400
        
        new_product = Product(
            barcode=barcode,
            name=product_data.get("name"),
            category=product_data.get("category"),
            brand=product_data.get("brand"),
            description=product_data.get("description"),
            image=product_data.get("image"),
        )

        db.session.add(new_product)
        db.session.commit()

        return jsonify({
            "success": True,
            "barcode": barcode
        }), 200
    
    #if not JSON it will show the html
    return render_template("product_add.html")

# endpoint to delete a product from the DB, only accessible to verifiers and admins
@product_bp.route("/product/<barcode>/delete", methods=["POST"])
@roles_required("verifier", "admin")
def delete_product(barcode):
    product = db.session.get(Product, barcode)
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for("product.product"))

    try:
        db.session.delete(product)
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash("Failed to delete product. It may be referenced by other records.", "error")
        return redirect(url_for("product.product_edit", barcode=barcode))

    flash("Product deleted successfully.", "success")
    return redirect(url_for("product.product_list"))