import csv
import io

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for
from flask_login import current_user

from sstq.auth_decorators import roles_required
from sstq.extensions import db
from sstq.models import Badge, ChangeLog, Claim, Evidence, Issue, Mission, Player, Product, Stage, User

admin_bp = Blueprint("admin", __name__)


def _player_for_user(user_id):
    return Player.query.filter_by(user_id=user_id).first()


def _delete_player_progress(player):
    if not player:
        return
    Badge.query.filter_by(player_id=player.player_id).delete(synchronize_session=False)
    Mission.query.filter_by(player_id=player.player_id).delete(synchronize_session=False)
    db.session.delete(player)


def _delete_mission_group(row):
    if not row:
        return 0
    if row.mission_group_id:
        return Mission.query.filter_by(
            player_id=row.player_id,
            mission_group_id=row.mission_group_id,
        ).delete(synchronize_session=False)
    db.session.delete(row)
    return 1


@admin_bp.route("/admin", methods=["GET"])
@roles_required("verifier", "admin")
def admin():
    issue_rows = (
        db.session.query(Issue, Claim, Product, User)
        .join(Claim, Issue.claim_id == Claim.claim_id)
        .join(Product, Claim.product_barcode == Product.barcode)
        .outerjoin(User, Issue.user_id == User.user_id)
        .order_by(Issue.issue_id.desc())
        .limit(80)
        .all()
    )

    recent_changes = (
        db.session.query(ChangeLog, User)
        .join(User, ChangeLog.user_id == User.user_id)
        .order_by(ChangeLog.timestamp.desc())
        .limit(60)
        .all()
    )

    user_rows = (
        db.session.query(User, Player)
        .outerjoin(Player, Player.user_id == User.user_id)
        .order_by(User.role.asc(), User.username.asc())
        .all()
    )

    mission_rows = (
        db.session.query(Mission, User)
        .join(Player, Player.player_id == Mission.player_id)
        .join(User, User.user_id == Player.user_id)
        .filter(Mission.question_number == 1)
        .order_by(Mission.mission_id.desc())
        .limit(60)
        .all()
    )

    stats = {
        "products": Product.query.count(),
        "stages": Stage.query.count(),
        "claims": Claim.query.count(),
        "evidence": Evidence.query.count(),
        "issues_open": Issue.query.filter(Issue.status.in_(["open", "in_review"])).count(),
        "issues_total": Issue.query.count(),
        "users": User.query.count(),
        "missions": Mission.query.count(),
    }

    status_breakdown = dict(
        db.session.query(Issue.status, db.func.count(Issue.issue_id))
        .group_by(Issue.status)
        .all()
    )

    user_summaries = []
    for user, player in user_rows:
        mission_count = Mission.query.filter_by(player_id=player.player_id).count() if player else 0
        badge_count = Badge.query.filter_by(player_id=player.player_id).count() if player else 0
        issue_count = Issue.query.filter_by(user_id=user.user_id).count()
        user_summaries.append(
            {
                "user": user,
                "player": player,
                "mission_count": mission_count,
                "badge_count": badge_count,
                "issue_count": issue_count,
            }
        )

    return render_template(
        "admin.html",
        issue_rows=issue_rows,
        recent_changes=recent_changes,
        stats=stats,
        status_breakdown=status_breakdown,
        user_summaries=user_summaries,
        mission_rows=mission_rows,
    )


@admin_bp.route("/admin/users/create", methods=["POST"])
@roles_required("admin")
def create_user():
    username = (request.form.get("username") or "").strip()
    password = (request.form.get("password") or "").strip()
    role = (request.form.get("role") or "consumer").strip().lower()

    if not username or not password:
        flash("Username and password are required.", "error")
        return redirect(url_for("admin.admin"))

    if role not in {"consumer", "verifier", "admin"}:
        flash("Invalid role.", "error")
        return redirect(url_for("admin.admin"))

    if User.query.filter_by(username=username).first():
        flash("Username already exists.", "error")
        return redirect(url_for("admin.admin"))

    try:
        user = User(username=username, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        db.session.add(
            ChangeLog(
                user_id=current_user.user_id,
                change_summary=f"Created user '{username}' with role '{role}'.",
            )
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash("Failed to create user.", "error")
        return redirect(url_for("admin.admin"))

    flash("User created.", "success")
    return redirect(url_for("admin.admin"))


@admin_bp.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@roles_required("admin")
def delete_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash("User not found.", "error")
        return redirect(url_for("admin.admin"))

    if user.user_id == current_user.user_id:
        flash("You cannot delete your own account from admin.", "error")
        return redirect(url_for("admin.admin"))

    try:
        player = _player_for_user(user.user_id)
        _delete_player_progress(player)
        Issue.query.filter_by(user_id=user.user_id).update({"user_id": None}, synchronize_session=False)
        ChangeLog.query.filter_by(user_id=user.user_id).delete(synchronize_session=False)
        username = user.username
        db.session.delete(user)
        db.session.flush()
        db.session.add(
            ChangeLog(
                user_id=current_user.user_id,
                change_summary=f"Deleted user '{username}'.",
            )
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash("Failed to delete user.", "error")
        return redirect(url_for("admin.admin"))

    flash("User deleted.", "success")
    return redirect(url_for("admin.admin"))


@admin_bp.route("/admin/users/<int:user_id>/missions/clear", methods=["POST"])
@roles_required("admin")
def clear_user_missions(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash("User not found.", "error")
        return redirect(url_for("admin.admin"))

    player = _player_for_user(user.user_id)
    if not player:
        flash("This user has no player profile yet.", "error")
        return redirect(url_for("admin.admin"))

    try:
        mission_count = Mission.query.filter_by(player_id=player.player_id).count()
        Badge.query.filter_by(player_id=player.player_id).delete(synchronize_session=False)
        Mission.query.filter_by(player_id=player.player_id).delete(synchronize_session=False)
        player.points = 0
        db.session.add(
            ChangeLog(
                user_id=current_user.user_id,
                change_summary=f"Cleared {mission_count} mission rows for user '{user.username}'.",
            )
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash("Failed to clear user missions.", "error")
        return redirect(url_for("admin.admin"))

    flash("User missions cleared.", "success")
    return redirect(url_for("admin.admin"))


@admin_bp.route("/admin/missions/<int:mission_id>/delete", methods=["POST"])
@roles_required("admin")
def delete_mission_group(mission_id):
    row = db.session.get(Mission, mission_id)
    if not row:
        flash("Mission not found.", "error")
        return redirect(url_for("admin.admin"))

    player = db.session.get(Player, row.player_id)
    username = db.session.get(User, player.user_id).username if player else "unknown"

    try:
        deleted_rows = _delete_mission_group(row)
        db.session.flush()
        db.session.add(
            ChangeLog(
                user_id=current_user.user_id,
                change_summary=f"Deleted mission group starting at row #{mission_id} for user '{username}' ({deleted_rows} row(s)).",
            )
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash("Failed to delete mission group.", "error")
        return redirect(url_for("admin.admin"))

    flash("Mission group deleted.", "success")
    return redirect(url_for("admin.admin"))


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
                change_summary=f"Issue #{issue.issue_id} status changed from '{old_status}' to '{new_status}'.",
            )
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash("Failed to update issue.", "error")
        return redirect(url_for("admin.admin"))

    flash("Issue updated.", "success")
    return redirect(url_for("admin.admin"))


@admin_bp.route("/admin/issues/<int:issue_id>/delete", methods=["POST"])
@roles_required("verifier", "admin")
def delete_issue(issue_id):
    issue = db.session.get(Issue, issue_id)
    if not issue:
        flash("Issue not found.", "error")
        return redirect(url_for("admin.admin"))

    try:
        db.session.delete(issue)
        db.session.add(
            ChangeLog(
                user_id=current_user.user_id,
                change_summary=f"Deleted issue #{issue_id}.",
            )
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash("Failed to delete issue.", "error")
        return redirect(url_for("admin.admin"))

    flash("Issue deleted.", "success")
    return redirect(url_for("admin.admin"))


@admin_bp.route("/admin/logs/clear", methods=["POST"])
@roles_required("admin")
def clear_logs():
    try:
        ChangeLog.query.delete(synchronize_session=False)
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash("Failed to clear logs.", "error")
        return redirect(url_for("admin.admin"))

    flash("Change log cleared.", "success")
    return redirect(url_for("admin.admin"))


@admin_bp.route("/admin/logs/download", methods=["GET"])
@roles_required("admin")
def download_logs():
    rows = (
        db.session.query(ChangeLog, User)
        .join(User, ChangeLog.user_id == User.user_id)
        .order_by(ChangeLog.timestamp.desc())
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["log_id", "timestamp", "username", "role", "change_summary"])
    for log, user in rows:
        writer.writerow([log.log_id, log.timestamp, user.username, user.role, log.change_summary])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=change_log_export.csv"},
    )
