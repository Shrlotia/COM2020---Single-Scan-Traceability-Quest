from flask import Blueprint, jsonify, url_for, current_app, request
from werkzeug.utils import secure_filename
from pathlib import Path
from uuid import uuid4

from sstq.extensions import db
from sstq.auth_decorators import roles_required
from sstq.models import Product

helper_bp = Blueprint("helper", __name__)

def _validate_image_file(image_file):
    if not image_file:
        return "Image file is required"

    if not image_file.mimetype or not image_file.mimetype.startswith("image/"):
        return "Invalid image type"

    return None


def _validate_pdf_file(uploaded_file):
    if not uploaded_file:
        return "PDF file is required"

    mimetype = (uploaded_file.mimetype or "").lower()
    filename = (uploaded_file.filename or "").lower()
    if mimetype != "application/pdf" and not filename.endswith(".pdf"):
        return "Invalid PDF file"

    return None


def _normalized_extension(image_file):
    extension = image_file.mimetype.split("/")[-1].lower()
    if extension == "jpeg":
        extension = "jpg"
    if extension not in {"jpg", "png", "webp"}:
        extension = "jpg"
    return extension


def _save_image_file(image_file, *, barcode, subdir):
    extension = _normalized_extension(image_file)
    safe_barcode = secure_filename(barcode) if barcode else "product"
    filename = f"{safe_barcode}-{uuid4().hex[:12]}.{extension}"

    upload_dir = Path(current_app.static_folder) / "uploads" / subdir
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / filename
    image_file.save(file_path)
    return file_path, url_for("static", filename=f"uploads/{subdir}/{filename}")


def _save_uploaded_file(uploaded_file, *, barcode, subdir, extension):
    safe_barcode = secure_filename(barcode) if barcode else "file"
    filename = f"{safe_barcode}-{uuid4().hex[:12]}.{extension}"

    upload_dir = Path(current_app.static_folder) / "uploads" / subdir
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / filename
    uploaded_file.save(file_path)
    return file_path, url_for("static", filename=f"uploads/{subdir}/{filename}")


@helper_bp.route("/upload_product_image", methods=["POST"])
@roles_required("verifier", "admin")
def upload_product_image():
    image_file = request.files.get("image")
    barcode = (request.form.get("barcode") or "").strip()

    error = _validate_image_file(image_file)
    if error:
        return jsonify({"success": False, "message": error}), 400

    _, image_url = _save_image_file(image_file, barcode=barcode, subdir="products")
    return jsonify({"success": True, "image_url": image_url})


@helper_bp.route("/upload_product_image_temp", methods=["POST"])
@roles_required("verifier", "admin")
def upload_product_image_temp():
    image_file = request.files.get("image")
    barcode = (request.form.get("barcode") or "").strip()

    error = _validate_image_file(image_file)
    if error:
        return jsonify({"success": False, "message": error}), 400

    _, image_url = _save_image_file(image_file, barcode=barcode, subdir="cache")
    return jsonify({"success": True, "image_url": image_url})


@helper_bp.route("/upload_evidence_file_temp", methods=["POST"])
@roles_required("verifier", "admin")
def upload_evidence_file_temp():
    uploaded_file = request.files.get("file")
    barcode = (request.form.get("barcode") or "").strip()

    error = _validate_pdf_file(uploaded_file)
    if error:
        return jsonify({"success": False, "message": error}), 400

    _, file_url = _save_uploaded_file(
        uploaded_file,
        barcode=barcode,
        subdir="cache/evidence",
        extension="pdf",
    )
    return jsonify({"success": True, "file_url": file_url})

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
