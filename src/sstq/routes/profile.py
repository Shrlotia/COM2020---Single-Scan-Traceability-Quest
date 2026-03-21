from flask import Blueprint, render_template
from flask_login import current_user

from sstq.auth_decorators import login_required
from sstq.extensions import db
from sstq.models import Badge, ChangeLog, Issue, Mission, Player

profile_bp = Blueprint("profile", __name__)

TIER_MAP = {
    "basic": "easy",
    "intermediate": "normal",
    "advanced": "hard",
    "easy": "easy",
    "normal": "normal",
    "hard": "hard",
}


@profile_bp.route("/profile", methods=["GET"])
@login_required
def profile():
    player = Player.query.filter_by(user_id=current_user.user_id).first()

    missions = []
    badges = []
    mission_runs = []
    progress = {
        "points": 0,
        "missions_total": 0,
        "missions_correct": 0,
        "accuracy": 0,
        "tier_counts": {"easy": 0, "normal": 0, "hard": 0},
    }

    if player:
        missions = (
            Mission.query.filter_by(player_id=player.player_id)
            .order_by(Mission.mission_id.desc())
            .all()
        )
        badges = (
            Badge.query.filter_by(player_id=player.player_id)
            .order_by(Badge.badge_id.desc())
            .all()
        )

        missions_correct = sum(
            1
            for mission in missions
            if (mission.player_answer or "").strip().lower() == (mission.answer or "").strip().lower()
        )

        tier_counts = {
            "easy": 0,
            "normal": 0,
            "hard": 0,
        }

        for mission in missions:
            tier_counts[TIER_MAP.get((mission.tier or "").lower(), "easy")] += 1

        progress = {
            "points": player.points,
            "missions_total": len(missions),
            "missions_correct": missions_correct,
            "accuracy": round((missions_correct / len(missions)) * 100, 1) if missions else 0,
            "tier_counts": tier_counts,
        }

        mission_runs = (
            Mission.query.filter(
                Mission.player_id == player.player_id,
                Mission.mission_group_id.isnot(None),
                Mission.question_number == 1,
                Mission.completed_at.isnot(None),
            )
            .order_by(Mission.completed_at.desc(), Mission.mission_id.desc())
            .limit(12)
            .all()
        )

    my_issues = (
        Issue.query.filter_by(user_id=current_user.user_id)
        .order_by(Issue.issue_id.desc())
        .limit(20)
        .all()
    )

    my_changes = (
        ChangeLog.query.filter_by(user_id=current_user.user_id)
        .order_by(ChangeLog.timestamp.desc())
        .limit(20)
        .all()
    )

    issue_status_breakdown = dict(
        db.session.query(Issue.status, db.func.count(Issue.issue_id))
        .filter(Issue.user_id == current_user.user_id)
        .group_by(Issue.status)
        .all()
    )

    return render_template(
        "profile.html",
        player=player,
        missions=missions,
        mission_runs=mission_runs,
        badges=badges,
        progress=progress,
        my_issues=my_issues,
        my_changes=my_changes,
        issue_status_breakdown=issue_status_breakdown,
    )
