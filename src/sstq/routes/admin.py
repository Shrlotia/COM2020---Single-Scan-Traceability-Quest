from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from sstq.auth_decorators import roles_required
from sstq.extensions import db
from sstq.models import ChangeLog, Claim, Evidence, Issue, Product, Stage, User

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin", methods=["GET"])
@roles_required("verifier", "admin")
def admin():
    issue_rows = (
        db.session.query(Issue, Claim, Product, User)
        .join(Claim, Issue.claim_id == Claim.claim_id)
        .join(Product, Claim.product_barcode == Product.barcode)
        .outerjoin(User, Issue.user_id == User.user_id)
        .order_by(Issue.issue_id.desc())
        .limit(60)
        .all()
    )

    recent_changes = (
        db.session.query(ChangeLog, User)
        .join(User, ChangeLog.user_id == User.user_id)
        .order_by(ChangeLog.timestamp.desc())
        .limit(20)
        .all()
    )

    stats = {
        "products": Product.query.count(),
        "stages": Stage.query.count(),
        "claims": Claim.query.count(),
        "evidence": Evidence.query.count(),
        "issues_open": Issue.query.filter(Issue.status.in_(["open", "in_review"])).count(),
        "issues_total": Issue.query.count(),
    }

    status_breakdown = dict(
        db.session.query(Issue.status, db.func.count(Issue.issue_id))
        .group_by(Issue.status)
        .all()
    )

    return render_template(
        "admin.html",
        issue_rows=issue_rows,
        recent_changes=recent_changes,
        stats=stats,
        status_breakdown=status_breakdown,
    )


@admin_bp.route("/admin/issues/<int:issue_id>/update", methods=["POST"])
@roles_required("verifier", "admin")
def update_issue(issue_id):
    issue = db.session.get(Issue, issue_id)
    if not issue:
        flash("Issue not found.", "error")
        return redirect(url_for("admin.admin"))

    allowed_statuses = {"open", "in_review", "resolved", "rejected"}
    new_status = (request.form.get("status") or "").strip().lower()
    resolution_note = (request.form.get("resolution_note") or "").strip()

    if new_status not in allowed_statuses:
        flash("Invalid status update.", "error")
        return redirect(url_for("admin.admin"))

    old_status = issue.status

    try:
        issue.status = new_status
        issue.resolution_note = resolution_note or None
        db.session.add(
            ChangeLog(
                user_id=current_user.user_id,
                change_summary=(
                    f"Issue #{issue.issue_id} status changed from '{old_status}' to '{new_status}'."
                ),
            )
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash("Failed to update issue.", "error")
        return redirect(url_for("admin.admin"))

    flash("Issue updated.", "success")
    return redirect(url_for("admin.admin"))
