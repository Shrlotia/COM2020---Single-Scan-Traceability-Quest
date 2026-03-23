import json
import random
import uuid

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from sstq.auth_decorators import login_required
from sstq.extensions import db
from sstq.models import Badge, Mission, Player, Product

tracequest_bp = Blueprint("tracequest", __name__)

MISSION_CATEGORIES = [
    {"key": "snacks", "label": "Snacks", "tokens": {"snacks"}},
    {"key": "beverages", "label": "Beverages", "tokens": {"beverages"}},
    {"key": "plant_based_foods", "label": "Plant-based foods", "tokens": {"plant-based foods"}},
    {
        "key": "coffees",
        "label": "Coffees",
        "tokens": {
            "coffees",
            "coffee drinks",
            "coffee",
            "instant coffees",
            "ground coffees",
            "coffee capsules",
            "iced coffees",
            "whole bean coffee",
            "coffee milks",
        },
    },
    {"key": "cocoa", "label": "Cocoa", "tokens": {"cocoa and its products"}},
    {"key": "sweet_snacks", "label": "Sweet snacks", "tokens": {"sweet snacks"}},
    {"key": "luxury", "label": "Luxury", "tokens": {"luxury"}},
    {"key": "all_electronics", "label": "Electronics", "tokens": {"all electronics", "electronics"}},
]

CATEGORY_INDEX = {item["key"]: item for item in MISSION_CATEGORIES}

DIFFICULTY_CONFIG = {
    "easy": {"label": "Basic", "points": 10, "description": "Read the core passport sections and identify key facts."},
    "normal": {"label": "Intermediate", "points": 20, "description": "Interpret counts, labels, and origin breakdown patterns."},
    "hard": {"label": "Advanced", "points": 30, "description": "Combine evidence, confidence, and percentage reasoning."},
}

LEGACY_TIER_MAP = {
    "basic": "easy",
    "intermediate": "normal",
    "advanced": "hard",
    "easy": "easy",
    "normal": "normal",
    "hard": "hard",
}

PACK_SIZE = 6


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


def _normalize(value):
    return _clean_text(value).casefold()


def _split_categories(raw_category):
    return [_clean_text(part) for part in str(raw_category or "").split(",") if _clean_text(part)]


def _category_tokens(product):
    return {_normalize(part) for part in _split_categories(product.category)}


def _matches_category(product, category_key):
    category = CATEGORY_INDEX.get(category_key)
    if not category:
        return False
    return bool(_category_tokens(product) & category["tokens"])


def _products_for_category(products, category_key):
    return [product for product in products if _matches_category(product, category_key)]


def _display_tier(tier):
    return DIFFICULTY_CONFIG.get(LEGACY_TIER_MAP.get(tier, tier), {}).get("label", tier.title())


def _mission_stats(player):
    missions = Mission.query.filter_by(player_id=player.player_id).all()
    correct = sum(
        1
        for mission in missions
        if _normalize(mission.player_answer) == _normalize(mission.answer)
    )

    tier_counts = {"easy": 0, "normal": 0, "hard": 0}
    for mission in missions:
        mapped = LEGACY_TIER_MAP.get(_normalize(mission.tier), "easy")
        tier_counts[mapped] += 1

    total = len(missions)
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
        ("Quest Starter", "easy", stats["total"] >= 6),
        ("Insight Hunter", "normal", stats["correct"] >= 12),
        ("Trace Expert", "hard", stats["correct"] >= 24),
    ]

    for name, tier, unlocked in badge_rules:
        if unlocked and name not in existing:
            db.session.add(Badge(player_id=player.player_id, name=name, tier=tier))
            new_badges.append(name)

    return new_badges


def _options_from_pool(answer, pool):
    options = []
    seen = set()

    def add_option(value):
        clean = _clean_text(value)
        if not clean:
            return
        key = clean.casefold()
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


def _number_choices(answer, minimum=0, maximum=10):
    answer_int = int(answer)
    pool = [str(number) for number in range(minimum, maximum + 1)]
    return _options_from_pool(str(answer_int), pool)


def _question_key(product, difficulty, slug, key_scope=None):
    return f"{difficulty}:{key_scope or product.barcode}:{slug}"


def _question(product, difficulty, slug, prompt, answer, choices, explanation, section_label, section_url, key_scope=None):
    return {
        "id": _question_key(product, difficulty, slug, key_scope=key_scope),
        "product_barcode": product.barcode,
        "product_name": product.name,
        "difficulty": difficulty,
        "question": prompt,
        "answer": _clean_text(answer),
        "choices": [_clean_text(choice) for choice in choices],
        "explanation": explanation,
        "section_label": section_label,
        "section_url": section_url,
    }


def _serialize_choices(choices):
    return json.dumps([_clean_text(choice) for choice in choices])


def _claim_label(claim):
    return claim.confidence_label or "No label"


def _product_evidence_rows(product):
    rows = []
    for claim in sorted(product.claims, key=lambda row: row.claim_id):
        for evidence in sorted(claim.evidence, key=lambda row: row.evidence_id):
            rows.append((claim, evidence))
    return rows


def _breakdown_country_totals(breakdowns):
    totals = {}
    for row in breakdowns:
        totals[row.country] = totals.get(row.country, 0.0) + float(row.percentage)
    return totals


def _section_row_counts(product):
    evidence_rows = _product_evidence_rows(product)
    return {
        "Timeline": len(product.stages),
        "Origin Breakdown": len(product.breakdowns),
        "Claim Cards": len(product.claims),
        "Evidence View": len(evidence_rows),
    }


def _basic_questions(product, category_products):
    stages = sorted(product.stages, key=lambda row: row.stage_id)
    breakdowns = sorted(product.breakdowns, key=lambda row: row.breakdown_id)
    claims = sorted(product.claims, key=lambda row: row.claim_id)
    evidence_rows = _product_evidence_rows(product)

    stage_country_pool = [stage.country for item in category_products for stage in item.stages]
    breakdown_country_pool = [row.country for item in category_products for row in item.breakdowns]
    breakdown_name_pool = [row.breakdown_name for item in category_products for row in item.breakdowns]
    claim_type_pool = [claim.claim_type for item in category_products for claim in item.claims]
    confidence_pool = [_claim_label(claim) for item in category_products for claim in item.claims]
    evidence_type_pool = [row.evidence_type for item in category_products for _, row in _product_evidence_rows(item)]

    questions = [
    ]

    if stages:
        questions.extend(
            [
                _question(
                    product,
                    "easy",
                    "first_stage_country",
                    f"Which country is shown for the first timeline stage of {product.name}?",
                    stages[0].country,
                    _options_from_pool(stages[0].country, stage_country_pool),
                    "Check the first row in Product Detail > Timeline.",
                    "Timeline",
                    url_for("product.product_detail", barcode=product.barcode) + "#timeline",
                ),
                _question(
                    product,
                    "easy",
                    "last_stage_country",
                    f"Which country is shown for the final timeline stage of {product.name}?",
                    stages[-1].country,
                    _options_from_pool(stages[-1].country, stage_country_pool),
                    "Check the last row in Product Detail > Timeline.",
                    "Timeline",
                    url_for("product.product_detail", barcode=product.barcode) + "#timeline",
                ),
            ]
        )

    if breakdowns:
        largest = max(breakdowns, key=lambda row: row.percentage)
        questions.extend(
            [
                _question(
                    product,
                    "easy",
                    "largest_origin_country",
                    f"Which country has the largest origin share for {product.name}?",
                    largest.country,
                    _options_from_pool(largest.country, breakdown_country_pool),
                    "Find the largest percentage in Product Detail > Origin Breakdown.",
                    "Origin Breakdown",
                    url_for("product.product_detail", barcode=product.barcode) + "#origin-breakdown",
                ),
                _question(
                    product,
                    "easy",
                    "largest_origin_input",
                    f"Which input has the largest origin share for {product.name}?",
                    largest.breakdown_name,
                    _options_from_pool(largest.breakdown_name, breakdown_name_pool),
                    "Match the largest percentage to its input in Origin Breakdown.",
                    "Origin Breakdown",
                    url_for("product.product_detail", barcode=product.barcode) + "#origin-breakdown",
                ),
            ]
        )

    if claims:
        first_claim = claims[0]
        questions.append(
            _question(
                product,
                "easy",
                "first_claim_confidence",
                f"What confidence label is shown on the first claim for {product.name}?",
                _claim_label(first_claim),
                _options_from_pool(_claim_label(first_claim), confidence_pool + ["verified", "partially-verified", "unverified", "No label"]),
                "Check the first card in Product Detail > Claim Cards.",
                "Claim Cards",
                url_for("product.product_detail", barcode=product.barcode) + "#claim-cards",
            )
        )

    if evidence_rows:
        first_claim, first_evidence = evidence_rows[0]
        questions.append(
            _question(
                product,
                "easy",
                "first_evidence_type",
                f"Which evidence type appears first in the evidence view for {product.name}?",
                first_evidence.evidence_type,
                _options_from_pool(first_evidence.evidence_type, evidence_type_pool),
                "Open Product Evidence View and check the first evidence item.",
                "Evidence View",
                url_for("product.product_evidence", barcode=product.barcode),
            )
        )

    return questions


def _normal_questions(product, category_products):
    questions = []
    stages = sorted(product.stages, key=lambda row: row.stage_id)
    breakdowns = sorted(product.breakdowns, key=lambda row: row.breakdown_id)
    claims = sorted(product.claims, key=lambda row: row.claim_id)

    if stages:
        country_pool = [stage.country for item in category_products for stage in item.stages]
        questions.extend(
            [
                _question(
                    product,
                    "normal",
                    "stage_count",
                    f"How many timeline stages are listed for {product.name}?",
                    str(len(stages)),
                    _number_choices(len(stages), 1, 8),
                    "Count the rows in Product Detail > Timeline.",
                    "Timeline",
                    url_for("product.product_detail", barcode=product.barcode) + "#timeline",
                ),
                _question(
                    product,
                    "normal",
                    "timeline_country_count",
                    f"How many countries appear across the timeline for {product.name}?",
                    str(len({stage.country for stage in stages})),
                    _number_choices(len({stage.country for stage in stages}), 1, 8),
                    "Count distinct countries listed in Product Detail > Timeline.",
                    "Timeline",
                    url_for("product.product_detail", barcode=product.barcode) + "#timeline",
                ),
            ]
        )

    if breakdowns:
        country_pool = [row.country for item in category_products for row in item.breakdowns]
        largest = max(breakdowns, key=lambda row: row.percentage)
        smallest = min(breakdowns, key=lambda row: row.percentage)
        questions.extend(
            [
                _question(
                    product,
                    "normal",
                    "origin_country_count",
                    f"How many countries appear in the origin breakdown for {product.name}?",
                    str(len({row.country for row in breakdowns})),
                    _number_choices(len({row.country for row in breakdowns}), 1, 6),
                    "Count distinct countries in Product Detail > Origin Breakdown.",
                    "Origin Breakdown",
                    url_for("product.product_detail", barcode=product.barcode) + "#origin-breakdown",
                ),
                _question(
                    product,
                    "normal",
                    "smallest_origin_country",
                    f"Which country has the smallest origin share for {product.name}?",
                    smallest.country,
                    _options_from_pool(smallest.country, country_pool),
                    "Find the smallest percentage in Product Detail > Origin Breakdown.",
                    "Origin Breakdown",
                    url_for("product.product_detail", barcode=product.barcode) + "#origin-breakdown",
                ),
                _question(
                    product,
                    "normal",
                    "largest_origin_percentage",
                    f"What is the largest origin share for {product.name}, rounded to a whole percent?",
                    str(int(round(largest.percentage))),
                    _number_choices(int(round(largest.percentage)), 0, 100),
                    "Read the biggest percentage in Product Detail > Origin Breakdown.",
                    "Origin Breakdown",
                    url_for("product.product_detail", barcode=product.barcode) + "#origin-breakdown",
                ),
            ]
        )

    if claims:
        confidence_pool = [claim.confidence_label or "No label" for item in category_products for claim in item.claims]
        claim_type_pool = [claim.claim_type for item in category_products for claim in item.claims]
        questions.extend(
            [
                _question(
                    product,
                    "normal",
                    "claim_count",
                    f"How many claim cards are shown for {product.name}?",
                    str(len(claims)),
                    _number_choices(len(claims), 0, 6),
                    "Count the cards in Product Detail > Claim Cards.",
                    "Claim Cards",
                    url_for("product.product_detail", barcode=product.barcode) + "#claim-cards",
                ),
                _question(
                    product,
                    "normal",
                    "verified_claim_count",
                    f"How many claims for {product.name} are marked verified?",
                    str(sum(1 for claim in claims if _normalize(claim.confidence_label) == "verified")),
                    _number_choices(sum(1 for claim in claims if _normalize(claim.confidence_label) == "verified"), 0, 6),
                    "Count verified labels in Product Detail > Claim Cards.",
                    "Claim Cards",
                    url_for("product.product_detail", barcode=product.barcode) + "#claim-cards",
                ),
                _question(
                    product,
                    "normal",
                    "first_claim_type",
                    f"Which claim type appears first for {product.name}?",
                    claims[0].claim_type,
                    _options_from_pool(claims[0].claim_type, claim_type_pool),
                    "Use the first claim card in Product Detail > Claim Cards.",
                    "Claim Cards",
                    url_for("product.product_detail", barcode=product.barcode) + "#claim-cards",
                ),
            ]
        )

        unverified_claims = [claim for claim in claims if _normalize(claim.confidence_label) == "unverified"]
        if unverified_claims:
            questions.append(
                _question(
                    product,
                    "normal",
                    "unverified_claim_type",
                    f"Which claim type is marked unverified for {product.name}?",
                    unverified_claims[0].claim_type,
                    _options_from_pool(unverified_claims[0].claim_type, claim_type_pool),
                    "Look for the unverified label in Product Detail > Claim Cards.",
                    "Claim Cards",
                    url_for("product.product_detail", barcode=product.barcode) + "#claim-cards",
                )
            )

    evidence_rows = _product_evidence_rows(product)
    if evidence_rows:
        issuer_pool = [evidence.issuer for item in category_products for _, evidence in _product_evidence_rows(item)]
        latest_claim, latest_evidence = max(
            evidence_rows,
            key=lambda row: (row[1].date or "", row[1].evidence_id),
        )
        questions.append(
            _question(
                product,
                "normal",
                "latest_evidence_issuer",
                f"Who issued the latest evidence item shown for {product.name}?",
                latest_evidence.issuer or "-",
                _options_from_pool(latest_evidence.issuer or "-", issuer_pool),
                "Open Product Evidence View and find the most recent evidence date.",
                "Evidence View",
                url_for("product.product_evidence", barcode=product.barcode),
            )
        )

    return questions


def _hard_questions(product, category_products):
    questions = []
    stages = sorted(product.stages, key=lambda row: row.stage_id)
    breakdowns = sorted(product.breakdowns, key=lambda row: row.breakdown_id)
    claims = sorted(product.claims, key=lambda row: row.claim_id)
    evidence_rows = _product_evidence_rows(product)

    if breakdowns:
        largest = max(breakdowns, key=lambda row: row.percentage)
        total_other_share = round(sum(row.percentage for row in breakdowns if row.breakdown_id != largest.breakdown_id))
        questions.append(
            _question(
                product,
                "hard",
                "other_share_total",
                f"Rounded to the nearest whole number, what is the combined percentage of all origin shares except the largest one for {product.name}?",
                str(int(total_other_share)),
                _number_choices(int(total_other_share), 0, 100),
                "Add the smaller percentages in Product Detail > Origin Breakdown.",
                "Origin Breakdown",
                url_for("product.product_detail", barcode=product.barcode) + "#origin-breakdown",
            )
        )

        country_totals = _breakdown_country_totals(breakdowns)
        repeated_countries = [(country, total) for country, total in country_totals.items() if sum(1 for row in breakdowns if row.country == country) > 1]
        if repeated_countries:
            repeated_country, repeated_total = max(repeated_countries, key=lambda item: item[1])
            questions.append(
                _question(
                    product,
                    "hard",
                    "repeated_country_total",
                    f"What is the combined share for {repeated_country} in {product.name}, rounded to a whole percent?",
                    str(int(round(repeated_total))),
                    _number_choices(int(round(repeated_total)), 0, 100),
                    "Add repeated country percentages in Product Detail > Origin Breakdown.",
                    "Origin Breakdown",
                    url_for("product.product_detail", barcode=product.barcode) + "#origin-breakdown",
                )
            )

    if stages and breakdowns:
        section_counts = {
            "Timeline": len(stages),
            "Origin Breakdown": len(breakdowns),
        }
        section_answer = max(section_counts, key=section_counts.get)
        if len(stages) == len(breakdowns):
            section_answer = "Equal"
        questions.append(
            _question(
                product,
                "hard",
                "timeline_vs_breakdown",
                f"For {product.name}, which section has more rows: Timeline or Origin Breakdown?",
                section_answer,
                _options_from_pool(section_answer, ["Timeline", "Origin Breakdown", "Equal"]),
                "Compare the row counts in the two sections on Product Detail.",
                "Timeline / Origin Breakdown",
                url_for("product.product_detail", barcode=product.barcode),
            )
        )

    if claims:
        label_counts = {}
        for claim in claims:
            label = _claim_label(claim)
            label_counts[label] = label_counts.get(label, 0) + 1
        dominant_label, dominant_count = max(label_counts.items(), key=lambda item: (item[1], item[0]))
        if list(label_counts.values()).count(dominant_count) == 1:
            questions.append(
                _question(
                    product,
                    "hard",
                    "dominant_confidence_label",
                    f"Which confidence label appears most often for {product.name}?",
                    dominant_label,
                    _options_from_pool(dominant_label, list(label_counts.keys()) + ["verified", "partially-verified", "unverified", "No label"]),
                    "Count confidence labels in Product Detail > Claim Cards.",
                    "Claim Cards",
                    url_for("product.product_detail", barcode=product.barcode) + "#claim-cards",
                )
            )

    if evidence_rows:
        latest_claim, latest_evidence = max(
            evidence_rows,
            key=lambda row: (row[1].date or "", row[1].evidence_id),
        )
        total_evidence = len(evidence_rows)
        section_counts = _section_row_counts(product)
        section_answer = max(section_counts, key=section_counts.get)
        if list(section_counts.values()).count(section_counts[section_answer]) == 1:
            questions.append(
                _question(
                    product,
                    "hard",
                    "largest_section_count",
                    f"Which passport section has the most rows for {product.name}?",
                    section_answer,
                    _options_from_pool(section_answer, ["Timeline", "Origin Breakdown", "Claim Cards", "Evidence View"]),
                    "Compare row counts across the passport sections.",
                    "Product Detail / Evidence View",
                    url_for("product.product_detail", barcode=product.barcode),
                )
            )

        questions.extend(
            [
                _question(
                    product,
                    "hard",
                    "total_evidence_count",
                    f"How many evidence items are listed for {product.name} in total?",
                    str(total_evidence),
                    _number_choices(total_evidence, 0, 12),
                    "Count all evidence entries in Product Evidence View.",
                    "Evidence View",
                    url_for("product.product_evidence", barcode=product.barcode),
                ),
                _question(
                    product,
                    "hard",
                    "latest_evidence_type",
                    f"Which evidence type is attached to the latest evidence item for {product.name}?",
                    latest_evidence.evidence_type,
                    _options_from_pool(latest_evidence.evidence_type, [row.evidence_type for item in category_products for _, row in _product_evidence_rows(item)]),
                    "Use the most recent date in Product Evidence View.",
                    "Evidence View",
                    url_for("product.product_evidence", barcode=product.barcode),
                ),
            ]
        )

    return questions


def _fallback_pack(category_key, difficulty, category_products):
    fallback_questions = []
    for product in category_products:
        fallback_questions.extend(_basic_questions(product, category_products))
    return fallback_questions


def _build_mission_pack(category_key, difficulty, category_products):
    if difficulty not in DIFFICULTY_CONFIG:
        raise ValueError("Invalid difficulty.")
    if category_key not in CATEGORY_INDEX:
        raise ValueError("Invalid category.")
    if not category_products:
        raise ValueError("No products available for this category.")

    category_label = CATEGORY_INDEX[category_key]["label"]
    shuffled_products = category_products[:]
    random.shuffle(shuffled_products)
    candidates = []

    for product in shuffled_products[: min(len(shuffled_products), 16)]:
        candidates.extend(_basic_questions(product, category_products))
        if difficulty == "normal":
            candidates.extend(_normal_questions(product, category_products))
        elif difficulty == "hard":
            candidates.extend(_normal_questions(product, category_products))
            candidates.extend(_hard_questions(product, category_products))

    if difficulty in {"normal", "hard"} and len(candidates) < PACK_SIZE:
        candidates.extend(_fallback_pack(category_key, difficulty, category_products))

    random.shuffle(candidates)
    pack_questions = []
    seen = set()
    for question in candidates:
        if question["id"] in seen:
            continue
        seen.add(question["id"])
        pack_questions.append(question)
        if len(pack_questions) == PACK_SIZE:
            break

    if len(pack_questions) < PACK_SIZE:
        raise ValueError("Not enough mission questions could be generated for this category.")

    category = CATEGORY_INDEX[category_key]
    return {
        "category_key": category_key,
        "category_label": category["label"],
        "difficulty": difficulty,
        "difficulty_label": DIFFICULTY_CONFIG[difficulty]["label"],
        "questions": pack_questions,
    }


def _category_cards(products):
    cards = []
    for category in MISSION_CATEGORIES:
        category_products = _products_for_category(products, category["key"])
        cards.append(
            {
                "key": category["key"],
                "label": category["label"],
                "count": len(category_products),
                "sample_names": [product.name for product in category_products[:3]],
            }
        )
    return cards


def _recent_attempts(player):
    missions = (
        Mission.query.filter_by(player_id=player.player_id)
        .order_by(Mission.mission_id.desc())
        .limit(18)
        .all()
    )

    rows = []
    for mission in missions:
        correct = _normalize(mission.player_answer) == _normalize(mission.answer)
        rows.append(
            {
                "mission_id": mission.mission_id,
                "tier": _display_tier(mission.tier),
                "question": mission.question,
                "player_answer": mission.player_answer,
                "correct": correct,
            }
        )
    return rows


@tracequest_bp.route("/trace_quest", methods=["GET", "POST"])
@login_required
def tracequest():
    player = _ensure_player()
    products = Product.query.order_by(Product.name.asc()).limit(200).all()
    category_cards = _category_cards(products)

    selected_category = request.form.get("mission_category") or request.args.get("category") or MISSION_CATEGORIES[0]["key"]
    if selected_category not in CATEGORY_INDEX:
        selected_category = MISSION_CATEGORIES[0]["key"]

    selected_difficulty = _normalize(request.form.get("difficulty") or request.args.get("difficulty") or "easy")
    if selected_difficulty not in DIFFICULTY_CONFIG:
        selected_difficulty = "easy"

    if request.method == "POST":
        category_products = _products_for_category(products, selected_category)
        try:
            pack = _build_mission_pack(selected_category, selected_difficulty, category_products)
        except ValueError as exc:
            flash(str(exc), "error")
        else:
            group_id = str(uuid.uuid4())
            rows = []
            for index, question in enumerate(pack["questions"], start=1):
                row = Mission(
                    player_id=player.player_id,
                    mission_group_id=group_id,
                    mission_category=pack["category_label"],
                    tier=pack["difficulty"],
                    product_barcode=question["product_barcode"],
                    product_name=question["product_name"][:128],
                    question_number=index,
                    total_questions=len(pack["questions"]),
                    question=_clean_text(question["question"])[:128],
                    player_answer="",
                    answer=_clean_text(question["answer"])[:128],
                    all_answers=", ".join(question["choices"])[:128],
                    choice_blob=_serialize_choices(question["choices"]),
                    explanation=_clean_text(question["explanation"])[:256],
                    section_label=_clean_text(question["section_label"])[:64],
                    section_url=_clean_text(question["section_url"])[:256],
                    score=None,
                    completed_at=None,
                )
                db.session.add(row)
                rows.append(row)

            db.session.commit()
            return redirect(url_for("misson.misson_detail", misson_id=rows[0].mission_id))

    stats = _mission_stats(player)
    badges = Badge.query.filter_by(player_id=player.player_id).order_by(Badge.badge_id.desc()).all()

    return render_template(
        "tracequest.html",
        player=player,
        stats=stats,
        badges=badges,
        recent_attempts=_recent_attempts(player),
        category_cards=category_cards,
        categories=MISSION_CATEGORIES,
        difficulties=DIFFICULTY_CONFIG,
        selected_category=selected_category,
        selected_difficulty=selected_difficulty,
    )
