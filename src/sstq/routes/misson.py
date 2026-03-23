import json
from datetime import datetime, timezone

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from sstq.auth_decorators import login_required
from sstq.extensions import db
from sstq.models import Badge, Mission, Product
from sstq.routes.tracequest import (
    DIFFICULTY_CONFIG,
    _award_badges,
    _clean_text,
    _display_tier,
    _ensure_player,
    _mission_stats,
    _normalize,
)

misson_bp = Blueprint("misson", __name__)


def _deserialize_choices(raw_text):
    if not raw_text:
        return []

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        return []

    return [_clean_text(item) for item in data if _clean_text(item)]


def _load_mission_group(misson_id, player_id):
    row = db.session.get(Mission, misson_id)
    if not row or row.player_id != player_id:
        return None, None

    if row.mission_group_id:
        group_rows = (
            Mission.query.filter_by(player_id=player_id, mission_group_id=row.mission_group_id)
            .order_by(Mission.question_number.asc(), Mission.mission_id.asc())
            .all()
        )
        return row, group_rows

    return row, [row]


def _tip_payload(product):
    stages = sorted(product.stages, key=lambda row: row.stage_id)
    breakdowns = sorted(product.breakdowns, key=lambda row: row.breakdown_id)
    claims = sorted(product.claims, key=lambda row: row.claim_id)
    evidence_rows = []
    for claim in claims:
        for evidence in sorted(claim.evidence, key=lambda row: row.evidence_id):
            evidence_rows.append(
                f"{evidence.evidence_type} · {evidence.issuer or '-'} · {evidence.date.date() if evidence.date else '-'}"
            )

    return {
        "name": product.name,
        "barcode": product.barcode,
        "brand": product.brand,
        "category": product.category,
        "description": product.description,
        "stages": [
            f"{stage.stage_type} · {stage.country}"
            for stage in stages[:5]
        ],
        "breakdowns": [
            f"{row.breakdown_name} · {row.country} · {row.percentage:.0f}%"
            for row in breakdowns[:4]
        ],
        "claims": [
            f"{claim.claim_type} · {claim.confidence_label or 'No label'}"
            for claim in claims[:4]
        ],
        "evidence": evidence_rows[:4],
        "evidence_count": sum(len(claim.evidence) for claim in claims),
    }


@misson_bp.route("/misson", methods=["GET"])
@login_required
def misson():
    return redirect(url_for("tracequest.tracequest"))


@misson_bp.route("/misson/<int:misson_id>", methods=["GET", "POST"])
@login_required
def misson_detail(misson_id):
    player = _ensure_player()
    first_row, mission_rows = _load_mission_group(misson_id, player.player_id)
    if not first_row:
        abort(404)

    if request.method == "POST":
        if first_row.completed_at is not None:
            flash("This misson has already been completed.", "error")
            return redirect(url_for("misson.misson_detail", misson_id=misson_id))

        score = 0
        gained_points = 0
        for row in mission_rows:
            player_answer = _clean_text(request.form.get(f"answer_{row.question_number}"))
            if not player_answer:
                flash("Please answer all 6 questions before submitting.", "error")
                return redirect(url_for("misson.misson_detail", misson_id=misson_id))

            row.player_answer = player_answer[:128]
            is_correct = _normalize(player_answer) == _normalize(row.answer)
            if is_correct:
                score += 1
                gained_points += DIFFICULTY_CONFIG.get(_normalize(row.tier), DIFFICULTY_CONFIG["easy"])["points"]

        completed_at = datetime.now(timezone.utc)
        for row in mission_rows:
            row.score = score
            row.completed_at = completed_at

        player.points += gained_points
        unlocked_badges = _award_badges(player, _mission_stats(player))
        db.session.commit()

        if unlocked_badges:
            flash(f"New badge unlocked: {', '.join(unlocked_badges)}", "success")

        return redirect(url_for("misson.misson_detail", misson_id=misson_id))

    review_rows = []
    for row in mission_rows:
        product = db.session.get(Product, row.product_barcode) if row.product_barcode else None
        choices = _deserialize_choices(row.choice_blob) or [_clean_text(item) for item in row.all_answers.split(",") if _clean_text(item)]
        review_rows.append(
            {
                "mission_id": row.mission_id,
                "question_number": row.question_number,
                "product_name": row.product_name,
                "product_barcode": row.product_barcode,
                "question": row.question,
                "choices": choices,
                "player_answer": row.player_answer,
                "answer": row.answer,
                "correct": row.completed_at is not None and _normalize(row.player_answer) == _normalize(row.answer),
                "explanation": row.explanation,
                "section_label": row.section_label or "Product Detail",
                "section_url": row.section_url or url_for("product.product_detail", barcode=row.product_barcode),
                "tip_payload": _tip_payload(product) if product else None,
            }
        )

    badges = Badge.query.filter_by(player_id=player.player_id).order_by(Badge.badge_id.desc()).all()

    return render_template(
        "misson.html",
        player=player,
        badges=badges,
        stats=_mission_stats(player),
        mission_first=first_row,
        mission_tier_label=_display_tier(first_row.tier),
        mission_rows=review_rows,
        mission_completed=first_row.completed_at is not None,
        mission_score=first_row.score if first_row.score is not None else 0,
        mission_total=first_row.total_questions or len(review_rows),
        mission_tip_mode=_normalize(first_row.tier),
    )
