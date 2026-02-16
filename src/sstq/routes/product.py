from datetime import datetime

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from sstq.auth_decorators import roles_required
from sstq.extensions import db
from sstq.models import Breakdown, Claim, Evidence, Product, Stage

product_bp = Blueprint("product", __name__)

def _safe_text(value):
    return str(value or "").replace("|", "/").replace("\n", " ").strip()


def _serialize_rows(rows):
    return "\n".join("|".join(_safe_text(field) for field in row) for row in rows)


def _parse_rows(raw_text, expected_parts):
    rows = []
    for line_no, raw_line in enumerate((raw_text or "").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        parts = [part.strip() for part in line.split("|", maxsplit=expected_parts - 1)]
        if len(parts) < expected_parts:
            parts.extend([""] * (expected_parts - len(parts)))
        rows.append((line_no, parts))
    return rows


def _parse_date(value, field_name, line_no):
    value = (value or "").strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"Invalid date for {field_name} on line {line_no}. Use YYYY-MM-DD.") from exc


def _format_date(value):
    if not value:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    return value.strftime("%Y-%m-%d")


def _build_edit_payload(product):
    stages = sorted(product.stages, key=lambda s: (s.start_date or datetime.min.date(), s.stage_id))
    breakdowns = sorted(product.breakdowns, key=lambda b: b.breakdown_id)
    claims = sorted(product.claims, key=lambda c: c.claim_id)

    stage_rows = [
        [
            stage.stage_type,
            stage.country,
            stage.region or "",
            _format_date(stage.start_date),
            _format_date(stage.end_date),
            stage.description,
        ]
        for stage in stages
    ]

    breakdown_rows = [
        [
            breakdown.breakdown_name,
            breakdown.country,
            f"{breakdown.percentage:g}",
            breakdown.notes or "",
        ]
        for breakdown in breakdowns
    ]

    claim_rows = [
        [
            claim.claim_type,
            claim.claim_text,
            claim.confidence_label or "",
            claim.rationale or "",
        ]
        for claim in claims
    ]

    claim_index_map = {claim.claim_id: index for index, claim in enumerate(claims, start=1)}
    evidence_rows = []
    for claim in claims:
        for evidence in sorted(claim.evidence, key=lambda e: e.evidence_id):
            evidence_rows.append(
                [
                    str(claim_index_map[claim.claim_id]),
                    evidence.evidence_type,
                    evidence.issuer or "",
                    _format_date(evidence.date),
                    evidence.summary or "",
                    evidence.file_reference or "",
                ]
            )

    return {
        "stage_rows": _serialize_rows(stage_rows),
        "breakdown_rows": _serialize_rows(breakdown_rows),
        "claim_rows": _serialize_rows(claim_rows),
        "evidence_rows": _serialize_rows(evidence_rows),
    }


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
        flash("Product not found.", "error")
        return redirect(url_for("product.product"))

    stages = sorted(product.stages, key=lambda s: (s.start_date or datetime.min.date(), s.stage_id))
    breakdowns = sorted(product.breakdowns, key=lambda b: b.breakdown_id)
    claims = sorted(product.claims, key=lambda c: c.claim_id)

    return render_template(
        "product_detail.html",
        product=product,
        stages=stages,
        breakdowns=breakdowns,
        claims=claims,
    )


@product_bp.route("/product/evidence/<barcode>", methods=["GET"])
@login_required
def product_evidence(barcode):
    product = db.session.get(Product, barcode)
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for("product.product"))

    claims = sorted(product.claims, key=lambda c: c.claim_id)
    return render_template("product_evidence.html", product=product, claims=claims)


@product_bp.route("/product/edit/<barcode>", methods=["GET"])
@roles_required("verifier", "admin")
def product_edit(barcode):
    product = db.session.get(Product, barcode)
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for("product.product"))

    edit_payload = _build_edit_payload(product)

    return render_template(
        "product_edit.html",
        barcode=product.barcode,
        name=product.name,
        category=product.category,
        brand=product.brand,
        description=product.description,
        image=product.image,
        stage_rows=edit_payload["stage_rows"],
        breakdown_rows=edit_payload["breakdown_rows"],
        claim_rows=edit_payload["claim_rows"],
        evidence_rows=edit_payload["evidence_rows"],
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
        parsed_stages = []
        for line_no, parts in _parse_rows(request.form.get("timeline_rows"), 6):
            stage_type, country, region, start_raw, end_raw, stage_desc = parts
            if not stage_type or not country or not stage_desc:
                raise ValueError(f"Timeline line {line_no} needs stage type, country and description.")

            start_date = _parse_date(start_raw, "timeline start date", line_no)
            end_date = _parse_date(end_raw, "timeline end date", line_no)
            if start_date and end_date and end_date < start_date:
                raise ValueError(f"Timeline line {line_no} has end date before start date.")

            parsed_stages.append(
                Stage(
                    product_barcode=new_barcode,
                    stage_type=stage_type,
                    country=country,
                    region=region or None,
                    start_date=start_date,
                    end_date=end_date,
                    description=stage_desc,
                )
            )

        parsed_breakdowns = []
        for line_no, parts in _parse_rows(request.form.get("breakdown_rows"), 4):
            name_value, country, percentage_raw, notes = parts
            if not name_value or not country or not percentage_raw:
                raise ValueError(f"Origin breakdown line {line_no} needs name, country and percentage.")

            try:
                percentage = float(percentage_raw)
            except ValueError as exc:
                raise ValueError(f"Origin breakdown line {line_no} has invalid percentage.") from exc

            parsed_breakdowns.append(
                Breakdown(
                    product_barcode=new_barcode,
                    breakdown_name=name_value,
                    country=country,
                    percentage=percentage,
                    notes=notes or None,
                )
            )

        parsed_claims = []
        for line_no, parts in _parse_rows(request.form.get("claim_rows"), 4):
            claim_type, claim_text, confidence_label, rationale = parts
            if not claim_type or not claim_text:
                raise ValueError(f"Claim line {line_no} needs claim type and claim text.")

            parsed_claims.append(
                {
                    "claim_type": claim_type,
                    "claim_text": claim_text,
                    "confidence_label": confidence_label or None,
                    "rationale": rationale or None,
                }
            )

        parsed_evidence = []
        for line_no, parts in _parse_rows(request.form.get("evidence_rows"), 6):
            claim_index_raw, evidence_type, issuer, date_raw, summary, file_reference = parts
            if not claim_index_raw or not evidence_type:
                raise ValueError(f"Evidence line {line_no} needs claim index and evidence type.")
            if not parsed_claims:
                raise ValueError("Evidence exists but no claims are defined.")

            try:
                claim_index = int(claim_index_raw)
            except ValueError as exc:
                raise ValueError(f"Evidence line {line_no} claim index must be a number.") from exc

            if claim_index < 1 or claim_index > len(parsed_claims):
                raise ValueError(
                    f"Evidence line {line_no} references claim {claim_index}, but claim index must be between 1 and {len(parsed_claims)}."
                )

            evidence_date = _parse_date(date_raw, "evidence date", line_no)
            parsed_evidence.append(
                {
                    "claim_index": claim_index,
                    "evidence_type": evidence_type,
                    "issuer": issuer or None,
                    "date": datetime.combine(evidence_date, datetime.min.time()) if evidence_date else datetime.utcnow(),
                    "summary": summary or None,
                    "file_reference": file_reference or None,
                }
            )

    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("product.product_edit", barcode=barcode))

    try:
        old_claims = Claim.query.filter_by(product_barcode=barcode).all()
        old_claim_ids = [claim.claim_id for claim in old_claims]
        if old_claim_ids:
            Evidence.query.filter(Evidence.claim_id.in_(old_claim_ids)).delete(synchronize_session=False)

        Claim.query.filter_by(product_barcode=barcode).delete(synchronize_session=False)
        Stage.query.filter_by(product_barcode=barcode).delete(synchronize_session=False)
        Breakdown.query.filter_by(product_barcode=barcode).delete(synchronize_session=False)

        product.barcode = new_barcode
        product.name = name
        product.category = category
        product.brand = brand
        product.description = description
        product.image = image

        for stage in parsed_stages:
            db.session.add(stage)
        for breakdown in parsed_breakdowns:
            db.session.add(breakdown)

        created_claims = []
        for claim_data in parsed_claims:
            claim = Claim(product_barcode=new_barcode, **claim_data)
            db.session.add(claim)
            created_claims.append(claim)

        db.session.flush()

        for evidence_data in parsed_evidence:
            claim_ref = created_claims[evidence_data["claim_index"] - 1]
            db.session.add(
                Evidence(
                    claim_id=claim_ref.claim_id,
                    evidence_type=evidence_data["evidence_type"],
                    issuer=evidence_data["issuer"],
                    date=evidence_data["date"],
                    summary=evidence_data["summary"],
                    file_reference=evidence_data["file_reference"],
                )
            )

        db.session.commit()
    except Exception:
        db.session.rollback()
        flash("Failed to update product.", "error")
        return redirect(url_for("product.product_edit", barcode=barcode))

    flash("Product updated successfully.", "success")
    return redirect(url_for("product.product_detail", barcode=new_barcode))


# endpoint that allows a verifier to add/update products within the DB, adding claims and evidence labels
@product_bp.route("/add_product", methods=["GET", "POST"])
@roles_required("verifier", "admin")
def product_add():
    if request.is_json:
        # it will pass the permission check if it is testing
        if not current_app.config.get("TESTING"):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))

        data = request.get_json()

        if not data or "productData" not in data:
            return jsonify({"success": False}), 400

        product_data = data["productData"]
        barcode = product_data.get("barcode")

        # check for duplicates
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

        return jsonify({"success": True, "barcode": barcode}), 200

    # if not JSON it will show the html
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
    return redirect(url_for("product.product"))
