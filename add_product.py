from config import app, db
from pathlib import Path
from config import db
from models import Product

from flask import render_template, request, redirect, url_for, flash, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from auth_decorators import roles_required

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
    
    if Product.query.get(barcode):
        abort(400)

    product = Product(
       barcode = barcode,
        name = name,
        category = category,
        brand = brand,
        description = Description,
        image =" "
    )
    print(product)

    db.session.add(product)

    db.session.commit()

    return jsonify({"success": True, "barcode": barcode})

@app.route("/validate_barcode", methods=["POST"])
@roles_required("verifier", "admin") # you can only visit this page if your auth user type is 'verifier' or 'admin'
def validate_barcode():
    data = request.get_json()
    barcode = (data.get("barcode") or "").strip()

    if not barcode:
        return {"valid": False, "message": "Barcode required"} 
    
    if Product.query.get(barcode):
        return {"valid": False, "message": "Barcode already exists"}
    
    return {"valid": True}