from pathlib import Path
from flask import request, url_for, abort, jsonify, redirect, flash, render_template
from werkzeug.utils import secure_filename
from uuid import uuid4

from sstq.config import app, db
from sstq.models import Product
from sstq.auth_decorators import roles_required

# endpoint that allows a verifier to add/update products within the DB, adding claims and evidence labels
@app.route("/add_product", methods=["POST"])
@roles_required("verifier", "admin") # you can only visit this page if your auth user type is 'verifier' or 'admin'
def add_Product():

    data = request.get_json()
    
    product_data = data.get("productData", {})

    barcode = (product_data.get("barcode") or "").strip()
    name = (product_data.get("name") or "").strip()
    category = (product_data.get("category") or "").strip()
    brand = (product_data.get("brand") or "").strip()
    Description = (product_data.get("Description") or "").strip()
    image = (product_data.get("image") or "").strip()
    
    if Product.query.get(barcode):
        abort(400)

    product = Product(
        barcode = barcode,
        name = name,
        category = category,
        brand = brand,
        description = Description,
        image = image
    )
    print(product)

    db.session.add(product)

    db.session.commit()

    return jsonify({"success": True, "barcode": barcode})

@app.route("/upload_product_image", methods=["POST"])
@roles_required("verifier", "admin")
def upload_product_image():
    image_file = request.files.get("image")
    barcode = (request.form.get("barcode") or "").strip()

    if not image_file:
        return jsonify({"success": False, "message": "Image file is required"}), 400

    if not image_file.mimetype or not image_file.mimetype.startswith("image/"):
        return jsonify({"success": False, "message": "Invalid image type"}), 400

    extension = image_file.mimetype.split("/")[-1].lower()
    if extension == "jpeg":
        extension = "jpg"
    if extension not in {"jpg", "png", "webp"}:
        extension = "jpg"

    safe_barcode = secure_filename(barcode) if barcode else "product"
    filename = f"{safe_barcode}-{uuid4().hex[:12]}.{extension}"

    upload_dir = Path(app.static_folder) / "uploads" / "products"
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / filename
    image_file.save(file_path)

    image_url = url_for("static", filename=f"uploads/products/{filename}")
    return jsonify({"success": True, "image_url": image_url})

@app.route("/validate_barcode", methods=["POST"])
@roles_required("verifier", "admin") # you can only visit this page if your auth user type is 'verifier' or 'admin'
def validate_barcode():
    data = request.get_json()
    barcode = (data.get("barcode") or "").strip()

    if not barcode:
        return {"valid": False, "message": "Barcode required"} 
    
    if db.session.get(Product, barcode):
        return {"valid": False, "message": "Barcode already exists"}
    
    return {"valid": True}

@app.route("/product/edit/<barcode>", methods=["GET"])
@roles_required("verifier", "admin")
def product_edit(barcode):
    product = db.session.get(Product, barcode)
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for("product"))

    return render_template(
        "product_edit.html",
        barcode=product.barcode,
        name=product.name,
        category=product.category,
        brand=product.brand,
        description=product.description,
        image=product.image,
    )


@app.route("/product/edit/<barcode>", methods=["POST"])
@roles_required("verifier", "admin")
def edit_product(barcode):
    product = db.session.get(Product, barcode)
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for("product"))

    new_barcode = (request.form.get("barcode") or "").strip()
    name = (request.form.get("name") or "").strip()
    category = (request.form.get("category") or "").strip()
    brand = (request.form.get("brand") or "").strip()
    description = (request.form.get("description") or "").strip()
    image = (request.form.get("image") or "").strip()

    if not all([new_barcode, name, category, brand, description]):
        flash("All fields except image are required.", "error")
        return redirect(url_for("product_edit", barcode=barcode))

    if new_barcode != barcode and db.session.get(Product, new_barcode):
        flash("Barcode already exists.", "error")
        return redirect(url_for("product_edit", barcode=barcode))

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
        return redirect(url_for("product_edit", barcode=barcode))

    flash("Product updated successfully.", "success")
    return redirect(url_for("product_detail", barcode=new_barcode))

@app.route("/product/<barcode>/delete", methods=["POST"])
@roles_required("verifier", "admin")
def delete_product(barcode):
    product = db.session.get(Product, barcode)
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for("product"))

    try:
        db.session.delete(product)
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash("Failed to delete product. It may be referenced by other records.", "error")
        return redirect(url_for("product_edit", barcode=barcode))

    flash("Product deleted successfully.", "success")
    return redirect(url_for("product"))
