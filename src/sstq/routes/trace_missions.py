import random

from flask import Blueprint, flash, render_template, request,  current_app, jsonify
from flask_login import current_user

from sstq.auth_decorators import login_required
from sstq.extensions import db
from sstq.models import Badge, Breakdown, Claim, Mission, Player, Product, Stage

from .tracequest import _make_basic_question, _make_intermediate_question, _make_advanced_question, get_player_rankings, _ensure_player

quiz_bp = Blueprint("quiz", __name__)

TIER_POINTS = {
    "basic": 10,
    "intermediate": 20,
    "advanced": 30,
}

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

def _generate_quiz(category, selected_tier):
        
    products = Product.query.filter_by(category=category).all()
    selected_products = random.sample(products, min(6, len(products)))

    if selected_tier not in ["Basic", "Intermediate", "Advanced", "Adaptive"]:
        selected_tier = "Basic"
                                
    questions = []

    if selected_tier == "Basic":
        for product in selected_products:
            questions.append(_make_basic_question(product))
        return questions
                                                                        
    elif selected_tier == "Intermediate":
        for product in selected_products:
            questions.append(_make_intermediate_question(product))
        return questions
                                    
    elif selected_tier == "Advanced":
        for product in selected_products:
            questions.append(_make_advanced_question(product))
        return questions

@quiz_bp.route("/quiz_game", methods=["GET", "POST"])
@login_required
def quiz_game():
    if request.method == "GET":
        player = _ensure_player()
        player_rankings = get_player_rankings()
        categories = db.session.query(Product.category).distinct().all()
        categories = [c[0] for c in categories]
        return render_template(
            "quiz.html",
            player=player, 
            categories=categories,
            player_rankings=player_rankings
        )

    products = Product.query.order_by(Product.name.asc()).limit(200).all()
    
    selected_tier = (request.form.get("tier") or "basic").strip().lower()
    if selected_tier not in {"Basic", "Intermediate", "Advanced", "Adaptive"}:
        selected_tier = "basic"

    current_mission = None
    mission_result = None
    unlocked_badges = []

    if request.method == "POST":

        data = request.get_json()
    
        tier, category = data.get("tier", {}), data.get("category", {})

        questions = _generate_quiz(category, tier)

        return jsonify(questions)

def get_feedback():
    ok=0