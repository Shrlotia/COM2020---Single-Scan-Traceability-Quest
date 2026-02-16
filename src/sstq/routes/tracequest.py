import random

from flask import Blueprint, flash, render_template, request
from flask_login import current_user

from sstq.auth_decorators import login_required
from sstq.extensions import db
from sstq.models import Badge, Breakdown, Claim, Mission, Player, Product, Stage

tracequest_bp = Blueprint("tracequest", __name__)

TIER_POINTS = {
    "basic": 10,
    "intermediate": 20,
    "advanced": 30,
}


def _ensure_player():
    player = Player.query.filter_by(user_id=current_user.user_id).first()
    if player:
        return player

    player = Player(user_id=current_user.user_id, points=0)
    db.session.add(player)
    db.session.commit()
    return player


def _clean_text(value):
    return str(value or "").strip()


def _mission_stats(player):
    missions = Mission.query.filter_by(player_id=player.player_id).all()
    correct = sum(
        1
        for mission in missions
        if _clean_text(mission.player_answer).lower() == _clean_text(mission.answer).lower()
    )
    total = len(missions)

    tier_counts = {
        "basic": sum(1 for mission in missions if mission.tier == "basic"),
        "intermediate": sum(1 for mission in missions if mission.tier == "intermediate"),
        "advanced": sum(1 for mission in missions if mission.tier == "advanced"),
    }

    return {
        "total": total,
        "correct": correct,
        "accuracy": round((correct / total) * 100, 1) if total else 0,
        "tier_counts": tier_counts,
    }


def _award_badges(player, stats):
    existing = {badge.name for badge in player.badges}
    new_badges = []

    badge_rules = [
        ("First Steps", "basic", stats["total"] >= 1),
        ("Sharp Eyes", "intermediate", stats["correct"] >= 5),
        ("Trace Master", "advanced", stats["correct"] >= 12),
    ]

    for name, tier, unlocked in badge_rules:
        if unlocked and name not in existing:
            badge = Badge(player_id=player.player_id, name=name, tier=tier)
            db.session.add(badge)
            new_badges.append(name)

    return new_badges


def _options_from_pool(answer, pool):
    options = []
    seen = set()

    def add_option(value):
        clean = _clean_text(value)
        if not clean:
            return
        key = clean.lower()
        if key in seen:
            return
        seen.add(key)
        options.append(clean)

    add_option(answer)
    random.shuffle(pool)
    for item in pool:
        add_option(item)
        if len(options) >= 4:
            break

    while len(options) < 4:
        add_option(f"Option {len(options) + 1}")

    random.shuffle(options)
    return options[:4]


def _make_basic_question(product):
    mode = random.choice(["brand", "category", "barcode"])

    if mode == "brand":
        answer = product.brand
        pool = [item.brand for item in Product.query.limit(20).all()]
        return {
            "tier": "basic",
            "question": "What is this product's brand?",
            "answer": answer,
            "choices": _options_from_pool(answer, pool),
            "explanation": "Check Product Detail > Brand.",
        }

    if mode == "category":
        answer = product.category
        pool = [item.category for item in Product.query.limit(20).all()]
        return {
            "tier": "basic",
            "question": "Which category does this product belong to?",
            "answer": answer,
            "choices": _options_from_pool(answer, pool),
            "explanation": "Check Product Detail > Category.",
        }

    answer = product.barcode
    pool = [item.barcode for item in Product.query.limit(20).all()]
    return {
        "tier": "basic",
        "question": "Which barcode matches this product?",
        "answer": answer,
        "choices": _options_from_pool(answer, pool),
        "explanation": "Check Product Detail > Barcode.",
    }


def _make_intermediate_question(product):
    stages = sorted(product.stages, key=lambda stage: stage.stage_id)
    breakdowns = sorted(product.breakdowns, key=lambda row: row.breakdown_id)
    claims = sorted(product.claims, key=lambda claim: claim.claim_id)

    candidates = []

    if stages:
        answer = stages[0].country
        pool = [stage.country for stage in Stage.query.limit(40).all()]
        candidates.append(
            {
                "tier": "intermediate",
                "question": "In timeline, where does the first stage happen?",
                "answer": answer,
                "choices": _options_from_pool(answer, pool),
                "explanation": "Check Product Detail > Timeline first row.",
            }
        )

        answer = str(len(stages))
        pool = ["1", "2", "3", "4", "5", "6", "7"]
        candidates.append(
            {
                "tier": "intermediate",
                "question": "How many timeline stages does this product have?",
                "answer": answer,
                "choices": _options_from_pool(answer, pool),
                "explanation": "Count rows in Product Detail > Timeline.",
            }
        )

    if breakdowns:
        largest = max(breakdowns, key=lambda row: row.percentage)
        answer = largest.country
        pool = [row.country for row in Breakdown.query.limit(40).all()]
        candidates.append(
            {
                "tier": "intermediate",
                "question": "Which country has the largest origin share?",
                "answer": answer,
                "choices": _options_from_pool(answer, pool),
                "explanation": "Check Product Detail > Origin Breakdown.",
            }
        )

    if claims:
        answer = str(len(claims))
        pool = ["0", "1", "2", "3", "4", "5", "6"]
        candidates.append(
            {
                "tier": "intermediate",
                "question": "How many claim cards are shown for this product?",
                "answer": answer,
                "choices": _options_from_pool(answer, pool),
                "explanation": "Count cards in Product Detail > Claim Cards.",
            }
        )

    if not candidates:
        return _make_basic_question(product)

    return random.choice(candidates)


def _make_advanced_question(product):
    stages = product.stages
    breakdowns = product.breakdowns
    claims = product.claims

    candidates = []

    if claims:
        verified_count = sum(1 for claim in claims if (claim.confidence_label or "").lower() == "verified")
        answer = str(verified_count)
        pool = ["0", "1", "2", "3", "4", "5"]
        candidates.append(
            {
                "tier": "advanced",
                "question": "How many claims are marked 'verified'?",
                "answer": answer,
                "choices": _options_from_pool(answer, pool),
                "explanation": "Open Claim Evidence View and check confidence labels.",
            }
        )

        evidence_counts = [(claim, len(claim.evidence)) for claim in claims]
        top_claim, _ = max(evidence_counts, key=lambda item: item[1])
        answer = top_claim.claim_type
        pool = [claim.claim_type for claim in Claim.query.limit(30).all()]
        candidates.append(
            {
                "tier": "advanced",
                "question": "Which claim type has the most evidence entries?",
                "answer": answer,
                "choices": _options_from_pool(answer, pool),
                "explanation": "Compare evidence counts in Claim Evidence View.",
            }
        )

    if stages and breakdowns:
        answer = "Timeline"
        if len(breakdowns) > len(stages):
            answer = "Origin Breakdown"
        elif len(breakdowns) == len(stages):
            answer = "Equal"

        candidates.append(
            {
                "tier": "advanced",
                "question": "Which section has more rows: Timeline or Origin Breakdown?",
                "answer": answer,
                "choices": _options_from_pool(answer, ["Timeline", "Origin Breakdown", "Equal"]),
                "explanation": "Count rows in both sections on Product Detail.",
            }
        )

    if not candidates:
        return _make_intermediate_question(product)

    return random.choice(candidates)


def _generate_mission(product, tier):
    if tier == "basic":
        return _make_basic_question(product)
    if tier == "intermediate":
        return _make_intermediate_question(product)
    return _make_advanced_question(product)


@tracequest_bp.route("/trace_quest", methods=["GET", "POST"])
@login_required
def tracequest():
    player = _ensure_player()

    products = Product.query.order_by(Product.name.asc()).limit(200).all()
    selected_barcode = request.form.get("product_barcode") or (products[0].barcode if products else "")
    selected_tier = (request.form.get("tier") or "basic").strip().lower()
    if selected_tier not in {"basic", "intermediate", "advanced"}:
        selected_tier = "basic"

    current_mission = None
    mission_result = None
    unlocked_badges = []

    if request.method == "POST":
        action = (request.form.get("action") or "").strip().lower()
        selected_product = db.session.get(Product, selected_barcode)

        if not selected_product:
            flash("Please choose a valid product.", "error")
        elif action == "generate":
            current_mission = _generate_mission(selected_product, selected_tier)
        elif action == "submit":
            question = _clean_text(request.form.get("mission_question"))
            answer = _clean_text(request.form.get("mission_answer"))
            explanation = _clean_text(request.form.get("mission_explanation"))
            options_raw = _clean_text(request.form.get("mission_options"))
            player_answer = _clean_text(request.form.get("player_answer"))

            if not all([question, answer, explanation, options_raw, player_answer]):
                flash("Mission data is incomplete. Generate a new question.", "error")
            else:
                is_correct = player_answer.lower() == answer.lower()
                gained_points = TIER_POINTS.get(selected_tier, 10) if is_correct else 0

                mission_record = Mission(
                    player_id=player.player_id,
                    tier=selected_tier,
                    question=question[:128],
                    player_answer=player_answer[:128],
                    answer=answer[:128],
                    all_answers=options_raw[:128],
                    explanation=explanation[:256],
                )
                db.session.add(mission_record)

                if gained_points:
                    player.points += gained_points

                stats_after = _mission_stats(player)
                unlocked_badges = _award_badges(player, stats_after)
                db.session.commit()

                mission_result = {
                    "correct": is_correct,
                    "answer": answer,
                    "player_answer": player_answer,
                    "gained_points": gained_points,
                    "explanation": explanation,
                }

                if unlocked_badges:
                    flash(f"New badge unlocked: {', '.join(unlocked_badges)}", "success")

    stats = _mission_stats(player)
    recent_missions = (
        Mission.query.filter_by(player_id=player.player_id)
        .order_by(Mission.mission_id.desc())
        .limit(12)
        .all()
    )
    badges = Badge.query.filter_by(player_id=player.player_id).order_by(Badge.badge_id.desc()).all()

    return render_template(
        "tracequest.html",
        products=products,
        selected_barcode=selected_barcode,
        selected_tier=selected_tier,
        current_mission=current_mission,
        mission_result=mission_result,
        stats=stats,
        player=player,
        recent_missions=recent_missions,
        badges=badges,
    )
