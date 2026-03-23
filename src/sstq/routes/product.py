from datetime import datetime
from pathlib import Path
from uuid import uuid4
from urllib.parse import urlparse

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_
from werkzeug.utils import secure_filename

from sstq.auth_decorators import roles_required
from sstq.extensions import db
from sstq.models import Breakdown, ChangeLog, Claim, Evidence, Issue, Product, Stage

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


def _split_categories(raw_category):
    parts = []
    seen = set()

    for part in str(raw_category or "").split(","):
        category = part.strip()
        if not category:
            continue
        normalized = category.casefold()
        if normalized in seen:
            continue
        seen.add(normalized)
        parts.append(category)

    return parts or ["Uncategorized"]

def _list_categories(products):
    categories = {}

    for product in products:
        for category in _split_categories(product.category):
            categories.setdefault(category.casefold(), category)

    return [categories[key] for key in sorted(categories)]


def _dedupe_barcodes(values):
    barcodes = []
    seen = set()

    for value in values:
        barcode = str(value or "").strip()
        if not barcode or barcode in seen:
            continue
        seen.add(barcode)
        barcodes.append(barcode)

    return barcodes


def _parse_compare_ids(raw_value):
    return _dedupe_barcodes(str(raw_value or "").split(","))


def _product_sort_clause(sort_value):
    sort_key = str(sort_value or "name-asc").strip().lower()
    mapping = {
        "name-asc": (Product.name.asc(), Product.barcode.asc()),
        "name-desc": (Product.name.desc(), Product.barcode.desc()),
        "barcode-asc": (Product.barcode.asc(),),
        "barcode-desc": (Product.barcode.desc(),),
        "category-asc": (Product.category.asc(), Product.name.asc()),
        "category-desc": (Product.category.desc(), Product.name.asc()),
    }
    return sort_key if sort_key in mapping else "name-asc", mapping.get(sort_key, mapping["name-asc"])


def _compare_breakdowns(product):
    return [
        {
            "label": breakdown.breakdown_name,
            "country": breakdown.country,
            "percentage": breakdown.percentage,
            "notes": breakdown.notes,
        }
        for breakdown in sorted(product.breakdowns, key=lambda row: (row.breakdown_name.casefold(), row.country.casefold(), row.breakdown_id))
    ]


def _compare_claims(product):
    return [
        {
            "claim_type": claim.claim_type,
            "claim_text": claim.claim_text,
            "confidence_label": claim.confidence_label or "No label",
            "evidence_count": len(claim.evidence),
        }
        for claim in sorted(product.claims, key=lambda row: (row.claim_type.casefold(), row.claim_id))
    ]


def _compare_payload(product):
    claims = _compare_claims(product)
    confidence_summary = {"verified": 0, "partially-verified": 0, "unverified": 0, "other": 0}

    for claim in claims:
        label = str(claim["confidence_label"]).casefold()
        if label in confidence_summary:
            confidence_summary[label] += 1
        else:
            confidence_summary["other"] += 1

    return {
        "product": product,
        "breakdowns": _compare_breakdowns(product),
        "claims": claims,
        "confidence_summary": confidence_summary,
    }


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
        "stage_items": stage_rows,
        "breakdown_items": breakdown_rows,
        "claim_items": claim_rows,
        "evidence_items": evidence_rows,
    }


def _empty_editor_payload():
    return {
        "stage_rows": "",
        "breakdown_rows": "",
        "claim_rows": "",
        "evidence_rows": "",
        "stage_items": [],
        "breakdown_items": [],
        "claim_items": [],
        "evidence_items": [],
    }


def _log_change(summary):
    if current_user.is_authenticated:
        db.session.add(ChangeLog(user_id=current_user.user_id, change_summary=summary))


def _resolve_product_image_path(image_value):
    if not image_value:
        return None

    image_path = urlparse(image_value).path or str(image_value)
    if "/static/" in image_path:
        relative_path = image_path.split("/static/", 1)[1]
    elif image_path.startswith("static/"):
        relative_path = image_path.removeprefix("static/")
    else:
        return None

    static_root = Path(current_app.static_folder).resolve()
    candidate = (static_root / relative_path).resolve()
    try:
        candidate.relative_to(static_root)
    except ValueError:
        return None

    return candidate


def _delete_product_image_file(image_value):
    image_path = _resolve_product_image_path(image_value)
    if not image_path:
        return

    image_path.unlink(missing_ok=True)


def _is_temp_image(image_value):
    image_path = urlparse(str(image_value or "")).path or str(image_value or "")
    return "/static/uploads/cache/" in image_path or image_path.startswith("/static/uploads/cache/")


def _promote_temp_image(image_value, barcode):
    image_path = _resolve_product_image_path(image_value)
    if not image_path or not image_path.exists():
        return image_value

    uploads_dir = Path(current_app.static_folder) / "uploads" / "products"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    extension = image_path.suffix.lower() or ".jpg"
    safe_barcode = secure_filename(barcode) if barcode else "product"
    target_name = f"{safe_barcode}-{uuid4().hex[:12]}{extension}"
    target_path = uploads_dir / target_name
    image_path.replace(target_path)
    return url_for("static", filename=f"uploads/products/{target_name}")


def _is_temp_evidence(file_reference):
    file_path = urlparse(str(file_reference or "")).path or str(file_reference or "")
    return "/static/uploads/cache/evidence/" in file_path or file_path.startswith("/static/uploads/cache/evidence/")


def _resolve_evidence_file_path(file_reference):
    file_path = urlparse(str(file_reference or "")).path or str(file_reference or "")
    if "/static/uploads/evidence/" not in file_path and "/static/uploads/cache/evidence/" not in file_path:
        return None
    return _resolve_product_image_path(file_reference)


def _delete_evidence_file(file_reference):
    evidence_path = _resolve_evidence_file_path(file_reference)
    if not evidence_path:
        return
    evidence_path.unlink(missing_ok=True)


def _promote_temp_evidence(file_reference, barcode, claim_index, evidence_index):
    evidence_path = _resolve_evidence_file_path(file_reference)
    if not evidence_path or not evidence_path.exists():
        return file_reference

    uploads_dir = Path(current_app.static_folder) / "uploads" / "evidence"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    safe_barcode = secure_filename(barcode) if barcode else "product"
    target_name = f"{safe_barcode}-claim-{claim_index}-evidence-{evidence_index}.pdf"
    target_path = uploads_dir / target_name
    target_path.unlink(missing_ok=True)
    evidence_path.replace(target_path)
    return url_for("static", filename=f"uploads/evidence/{target_name}")


def _delete_product_related_records(product):
    claim_ids = [claim.claim_id for claim in Claim.query.filter_by(product_barcode=product.barcode).all()]
    if claim_ids:
        evidence_files = [
            evidence.file_reference
            for evidence in Evidence.query.filter(Evidence.claim_id.in_(claim_ids)).all()
            if evidence.file_reference
        ]
        for file_reference in evidence_files:
            _delete_evidence_file(file_reference)
        Evidence.query.filter(Evidence.claim_id.in_(claim_ids)).delete(synchronize_session=False)
        Issue.query.filter(Issue.claim_id.in_(claim_ids)).delete(synchronize_session=False)

    Claim.query.filter_by(product_barcode=product.barcode).delete(synchronize_session=False)
    Stage.query.filter_by(product_barcode=product.barcode).delete(synchronize_session=False)
    Breakdown.query.filter_by(product_barcode=product.barcode).delete(synchronize_session=False)


# product list page that shows all products in the DB
@product_bp.route("/product", methods=["GET"])
@login_required
def product():
    search_query = (request.args.get("q") or request.args.get("barcode") or "").strip()
    selected_category = (request.args.get("category") or "").strip()
    selected_sort, sort_clause = _product_sort_clause(request.args.get("sort"))
    page = max(1, request.args.get("page", default=1, type=int) or 1)

    query = Product.query
    if search_query:
        search_pattern = f"%{search_query}%"
        query = query.filter(
            or_(
                Product.barcode.ilike(search_pattern),
                Product.name.ilike(search_pattern),
                Product.category.ilike(search_pattern),
            )
        )

    if selected_category:
        query = query.filter(Product.category.ilike(f"%{selected_category}%"))

    pagination = query.order_by(*sort_clause).paginate(page=page, per_page=20, error_out=False)
    all_products = Product.query.order_by(Product.name.asc()).all()
    return render_template(
        "product.html",
        products=pagination.items,
        categories=_list_categories(all_products),
        initial_search=search_query,
        selected_category=selected_category,
        selected_sort=selected_sort,
        pagination=pagination,
    )


@product_bp.route("/products/compare", methods=["GET"])
@login_required
def product_compare():
    selected_barcodes = _parse_compare_ids(request.args.get("ids"))
    if len(selected_barcodes) != 2:
        flash("Select exactly two products to compare.", "error")
        return redirect(url_for("product.product"))

    products = [db.session.get(Product, barcode) for barcode in selected_barcodes]
    if any(product is None for product in products):
        flash("One or more selected products could not be found.", "error")
        return redirect(url_for("product.product"))

    left_product, right_product = products
    return render_template(
        "product_compare.html",
        left=_compare_payload(left_product),
        right=_compare_payload(right_product),
    )


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


@product_bp.route("/product/claim/<int:claim_id>/report_issue", methods=["POST"])
@login_required
def report_issue(claim_id):
    claim = db.session.get(Claim, claim_id)
    barcode = (request.form.get("barcode") or "").strip()
    if not claim:
        flash("Claim not found.", "error")
        if barcode:
            return redirect(url_for("product.product_evidence", barcode=barcode))
        return redirect(url_for("product.product"))

    issue_type = (request.form.get("issue_type") or "").strip()
    description = (request.form.get("description") or "").strip()

    if not issue_type or not description:
        flash("Issue type and description are required.", "error")
        return redirect(url_for("product.product_evidence", barcode=claim.product_barcode))

    try:
        issue = Issue(
            claim_id=claim.claim_id,
            user_id=current_user.user_id,
            issue_type=issue_type,
            description=description,
            status="open",
        )
        db.session.add(issue)
        _log_change(
            f"Reported issue for claim #{claim.claim_id} on product {claim.product_barcode}: {issue_type}."
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash("Failed to submit issue report.", "error")
        return redirect(url_for("product.product_evidence", barcode=claim.product_barcode))

    flash("Issue report submitted.", "success")
    return redirect(url_for("product.product_evidence", barcode=claim.product_barcode))


@product_bp.route("/product/edit/<barcode>", methods=["GET"])
@roles_required("verifier", "admin")
def product_edit(barcode):
    product = db.session.get(Product, barcode)
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for("product.product"))

    edit_payload = _build_edit_payload(product)
    image_value = (request.args.get("temp_image") or "").strip() or product.image

    return render_template(
        "product_edit.html",
        barcode=product.barcode,
        name=product.name,
        category=product.category,
        brand=product.brand,
        description=product.description,
        image=image_value,
        stage_rows=edit_payload["stage_rows"],
        breakdown_rows=edit_payload["breakdown_rows"],
        claim_rows=edit_payload["claim_rows"],
        evidence_rows=edit_payload["evidence_rows"],
        stage_items=edit_payload["stage_items"],
        breakdown_items=edit_payload["breakdown_items"],
        claim_items=edit_payload["claim_items"],
        evidence_items=edit_payload["evidence_items"],
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
        old_evidence_files = [
            evidence.file_reference
            for claim in old_claims
            for evidence in claim.evidence
            if evidence.file_reference
        ]
        old_claim_ids = [claim.claim_id for claim in old_claims]
        if old_claim_ids:
            Evidence.query.filter(Evidence.claim_id.in_(old_claim_ids)).delete(synchronize_session=False)

        Claim.query.filter_by(product_barcode=barcode).delete(synchronize_session=False)
        Stage.query.filter_by(product_barcode=barcode).delete(synchronize_session=False)
        Breakdown.query.filter_by(product_barcode=barcode).delete(synchronize_session=False)

        finalized_image = image
        if _is_temp_image(image):
            finalized_image = _promote_temp_image(image, new_barcode)
            if product.image and product.image != finalized_image:
                _delete_product_image_file(product.image)
        elif product.image and image != product.image:
            _delete_product_image_file(product.image)

        product.barcode = new_barcode
        product.name = name
        product.category = category
        product.brand = brand
        product.description = description
        product.image = finalized_image

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

        evidence_counts = {}
        finalized_evidence_files = []
        for evidence_data in parsed_evidence:
            claim_ref = created_claims[evidence_data["claim_index"] - 1]
            claim_index = evidence_data["claim_index"]
            evidence_counts[claim_index] = evidence_counts.get(claim_index, 0) + 1
            finalized_file_reference = evidence_data["file_reference"]
            if _is_temp_evidence(finalized_file_reference):
                finalized_file_reference = _promote_temp_evidence(
                    finalized_file_reference,
                    new_barcode,
                    claim_index,
                    evidence_counts[claim_index],
                )
            if finalized_file_reference:
                finalized_evidence_files.append(finalized_file_reference)
            db.session.add(
                Evidence(
                    claim_id=claim_ref.claim_id,
                    evidence_type=evidence_data["evidence_type"],
                    issuer=evidence_data["issuer"],
                    date=evidence_data["date"],
                    summary=evidence_data["summary"],
                    file_reference=finalized_file_reference,
                )
            )

        _log_change(
            f"Updated product '{name}' ({new_barcode}) with timeline/breakdown/claim/evidence changes."
        )
        db.session.commit()
        for file_reference in old_evidence_files:
            if file_reference not in finalized_evidence_files:
                _delete_evidence_file(file_reference)
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
    if request.method == "GET":
        payload = _empty_editor_payload()
        return render_template(
            "product_add.html",
            initial_barcode=(request.args.get("barcode") or "").strip(),
            image=(request.args.get("temp_image") or "").strip(),
            stage_rows=payload["stage_rows"],
            breakdown_rows=payload["breakdown_rows"],
            claim_rows=payload["claim_rows"],
            evidence_rows=payload["evidence_rows"],
            stage_items=payload["stage_items"],
            breakdown_items=payload["breakdown_items"],
            claim_items=payload["claim_items"],
            evidence_items=payload["evidence_items"],
        )

    barcode = (request.form.get("barcode") or "").strip()
    name = (request.form.get("name") or "").strip()
    category = (request.form.get("category") or "").strip()
    brand = (request.form.get("brand") or "").strip()
    description = (request.form.get("description") or "").strip()
    image = (request.form.get("image") or "").strip()

    if not all([barcode, name, category, brand]):
        flash("Barcode, product name, category and brand are required.", "error")
        return redirect(url_for("product.product_add", barcode=barcode))

    if db.session.get(Product, barcode):
        flash("Barcode already exists.", "error")
        return redirect(url_for("product.product_add", barcode=barcode))

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
                    product_barcode=barcode,
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
                    product_barcode=barcode,
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
        return redirect(url_for("product.product_add", barcode=barcode))

    try:
        finalized_image = _promote_temp_image(image, barcode) if _is_temp_image(image) else image or None

        product = Product(
            barcode=barcode,
            name=name,
            category=category,
            brand=brand,
            description=description or "",
            image=finalized_image,
        )
        db.session.add(product)

        for stage in parsed_stages:
            db.session.add(stage)
        for breakdown in parsed_breakdowns:
            db.session.add(breakdown)

        created_claims = []
        for claim_data in parsed_claims:
            claim = Claim(product_barcode=barcode, **claim_data)
            db.session.add(claim)
            created_claims.append(claim)

        db.session.flush()

        evidence_counts = {}
        for evidence_data in parsed_evidence:
            claim_ref = created_claims[evidence_data["claim_index"] - 1]
            claim_index = evidence_data["claim_index"]
            evidence_counts[claim_index] = evidence_counts.get(claim_index, 0) + 1
            finalized_file_reference = evidence_data["file_reference"]
            if _is_temp_evidence(finalized_file_reference):
                finalized_file_reference = _promote_temp_evidence(
                    finalized_file_reference,
                    barcode,
                    claim_index,
                    evidence_counts[claim_index],
                )

            db.session.add(
                Evidence(
                    claim_id=claim_ref.claim_id,
                    evidence_type=evidence_data["evidence_type"],
                    issuer=evidence_data["issuer"],
                    date=evidence_data["date"],
                    summary=evidence_data["summary"],
                    file_reference=finalized_file_reference,
                )
            )

        _log_change(f"Created product '{name}' ({barcode}) with timeline/breakdown/claim/evidence data.")
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash("Failed to create product.", "error")
        return redirect(url_for("product.product_add", barcode=barcode))

    flash("Product created successfully.", "success")
    return redirect(url_for("product.product_detail", barcode=barcode))


# endpoint to delete a product from the DB, only accessible to verifiers and admins
@product_bp.route("/product/<barcode>/delete", methods=["POST"])
@roles_required("verifier", "admin")
def delete_product(barcode):
    product = db.session.get(Product, barcode)
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for("product.product"))

    image_value = product.image
    try:
        product_name = product.name
        _delete_product_related_records(product)
        db.session.delete(product)
        _log_change(f"Deleted product '{product_name}' ({barcode}).")
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash("Failed to delete product. It may be referenced by other records.", "error")
        return redirect(url_for("product.product_edit", barcode=barcode))

    try:
        _delete_product_image_file(image_value)
    except OSError:
        current_app.logger.exception("Failed to delete image file for product %s", barcode)
        flash("Product deleted, but its image file could not be removed.", "warning")

    flash("Product deleted successfully.", "success")
    return redirect(url_for("product.product"))
