from flask import Blueprint, jsonify, url_for, current_app, request
from werkzeug.utils import secure_filename
from pathlib import Path
from uuid import uuid4

from sstq.extensions import db
from sstq.auth_decorators import roles_required
from sstq.models import Product

helper_bp = Blueprint("helper", __name__)

@helper_bp.route("/upload_product_image", methods=["POST"])
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

    upload_dir = Path(current_app.static_folder) / "uploads" / "products"
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / filename
    image_file.save(file_path)

    image_url = url_for("static", filename=f"uploads/products/{filename}")
    return jsonify({"success": True, "image_url": image_url})

@helper_bp.route("/validate_barcode", methods=["POST"])
@roles_required("verifier", "admin") # you can only visit this page if your auth user type is 'verifier' or 'admin'
def validate_barcode():
    data = request.get_json()
    barcode = (data.get("barcode") or "").strip()

    if not barcode:
        return {"valid": False, "message": "Barcode required"} 
    
    if db.session.get(Product, barcode):
        return {"valid": False, "message": "Barcode already exists"}
    
    return {"valid": True}

