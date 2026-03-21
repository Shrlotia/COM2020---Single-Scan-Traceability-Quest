import json
import random
import uuid
from collections import Counter

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
    "easy": {"label": "Easy", "points": 10, "description": "Quick passport facts and product basics."},
    "normal": {"label": "Normal", "points": 20, "description": "Interpret timeline, breakdown, and claim sections."},
    "hard": {"label": "Hard", "points": 30, "description": "Work through comparisons, counts, and evidence-backed reasoning."},
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


def _category_labels():
    return [item["label"] for item in MISSION_CATEGORIES]


def _metadata_questions(product, category_products, difficulty, selected_category_label):
    all_brands = [item.brand for item in category_products]
    all_names = [item.name for item in category_products]
    all_barcodes = [item.barcode for item in category_products]
    questions = [
        _question(
            product,
            difficulty,
            "brand",
            f"Which brand is listed for {product.name}?",
            product.brand,
            _options_from_pool(product.brand, all_brands),
            "Check Product Detail > Brand.",
            "Brand",
            url_for("product.product_detail", barcode=product.barcode),
        ),
        _question(
            product,
            difficulty,
            "barcode",
            f"Which barcode matches {product.name}?",
            product.barcode,
            _options_from_pool(product.barcode, all_barcodes),
            "Check Product Detail > Barcode.",
            "Barcode",
            url_for("product.product_detail", barcode=product.barcode),
        ),
        _question(
            product,
            difficulty,
            "name_from_barcode",
            f"Which product name matches barcode {product.barcode}?",
            product.name,
            _options_from_pool(product.name, all_names),
            "Use the product title on Product Detail.",
            "Product Detail",
            url_for("product.product_detail", barcode=product.barcode),
        ),
        _question(
            product,
            difficulty,
            "mission_category",
            f"Which mission category should include {product.name}?",
            selected_category_label,
            _options_from_pool(selected_category_label, _category_labels()),
            "Use the category labels shown for the product.",
            "Category",
            url_for("product.product_detail", barcode=product.barcode),
        ),
        _question(
            product,
            difficulty,
            "image_presence",
            f"Does {product.name} currently have a display image on the product page?",
            "Yes" if product.image else "No",
            _options_from_pool("Yes" if product.image else "No", ["Yes", "No"]),
            "Check the image area at the top of Product Detail.",
            "Product Image",
            url_for("product.product_detail", barcode=product.barcode),
        ),
    ]
    return questions


def _normal_questions(product, category_products):
    questions = []
    stages = sorted(product.stages, key=lambda row: row.stage_id)
    breakdowns = sorted(product.breakdowns, key=lambda row: row.breakdown_id)
    claims = sorted(product.claims, key=lambda row: row.claim_id)

    if stages:
        country_pool = [stage.country for item in category_products for stage in item.stages]
        stage_type_pool = [stage.stage_type for item in category_products for stage in item.stages]
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
                    "first_stage_country",
                    f"Where does the first timeline stage happen for {product.name}?",
                    stages[0].country,
                    _options_from_pool(stages[0].country, country_pool),
                    "Use the first row in Product Detail > Timeline.",
                    "Timeline",
                    url_for("product.product_detail", barcode=product.barcode) + "#timeline",
                ),
                _question(
                    product,
                    "normal",
                    "last_stage_type",
                    f"What is the last timeline stage type shown for {product.name}?",
                    stages[-1].stage_type,
                    _options_from_pool(stages[-1].stage_type, stage_type_pool),
                    "Use the last row in Product Detail > Timeline.",
                    "Timeline",
                    url_for("product.product_detail", barcode=product.barcode) + "#timeline",
                ),
            ]
        )

    if breakdowns:
        country_pool = [row.country for item in category_products for row in item.breakdowns]
        largest = max(breakdowns, key=lambda row: row.percentage)
        questions.extend(
            [
                _question(
                    product,
                    "normal",
                    "largest_origin_country",
                    f"Which country contributes the largest origin share for {product.name}?",
                    largest.country,
                    _options_from_pool(largest.country, country_pool),
                    "Find the largest percentage in Product Detail > Origin Breakdown.",
                    "Origin Breakdown",
                    url_for("product.product_detail", barcode=product.barcode) + "#origin-breakdown",
                ),
                _question(
                    product,
                    "normal",
                    "largest_origin_name",
                    f"Which breakdown item has the largest share for {product.name}?",
                    largest.breakdown_name,
                    _options_from_pool(largest.breakdown_name, [row.breakdown_name for item in category_products for row in item.breakdowns]),
                    "Check the item with the biggest percentage in Product Detail > Origin Breakdown.",
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
                    "first_claim_type",
                    f"Which claim type appears first for {product.name}?",
                    claims[0].claim_type,
                    _options_from_pool(claims[0].claim_type, claim_type_pool),
                    "Use the first claim card in Product Detail > Claim Cards.",
                    "Claim Cards",
                    url_for("product.product_detail", barcode=product.barcode) + "#claim-cards",
                ),
                _question(
                    product,
                    "normal",
                    "first_claim_confidence",
                    f"What confidence label is shown on the first claim card for {product.name}?",
                    claims[0].confidence_label or "No label",
                    _options_from_pool(claims[0].confidence_label or "No label", confidence_pool + ["Verified", "Partially verified", "Unverified", "No label"]),
                    "Check the first card in Product Detail > Claim Cards.",
                    "Claim Cards",
                    url_for("product.product_detail", barcode=product.barcode) + "#claim-cards",
                ),
            ]
        )

    return questions


def _hard_questions(product, category_products, selected_category_label):
    questions = []
    stages = sorted(product.stages, key=lambda row: row.stage_id)
    breakdowns = sorted(product.breakdowns, key=lambda row: row.breakdown_id)
    claims = sorted(product.claims, key=lambda row: row.claim_id)

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

    if stages and breakdowns:
        section_answer = "Timeline"
        if len(breakdowns) > len(stages):
            section_answer = "Origin Breakdown"
        elif len(breakdowns) == len(stages):
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
        verified_count = sum(1 for claim in claims if _normalize(claim.confidence_label) == "verified")
        questions.append(
            _question(
                product,
                "hard",
                "verified_claim_count",
                f"How many claims for {product.name} are marked verified?",
                str(verified_count),
                _number_choices(verified_count, 0, 6),
                "Open the claim cards or evidence view and count the verified labels.",
                "Claim Cards",
                url_for("product.product_detail", barcode=product.barcode) + "#claim-cards",
            )
        )

        evidence_counts = [(claim, len(claim.evidence)) for claim in claims]
        top_claim, _ = max(evidence_counts, key=lambda item: item[1])
        questions.append(
            _question(
                product,
                "hard",
                "top_evidence_claim",
                f"Which claim type has the most evidence entries for {product.name}?",
                top_claim.claim_type,
                _options_from_pool(top_claim.claim_type, [claim.claim_type for claim in claims]),
                "Use Product Evidence View and compare the evidence blocks under each claim.",
                "Evidence View",
                url_for("product.product_evidence", barcode=product.barcode),
            )
        )

    brand_counts = Counter(_clean_text(item.brand) for item in category_products if _clean_text(item.brand))
    if brand_counts:
        most_common_brand, count = brand_counts.most_common(1)[0]
        if count > 1:
            questions.append(
                _question(
                    product,
                    "hard",
                    "brand_frequency",
                    f"Which brand appears most often in the {selected_category_label} category list?",
                    most_common_brand,
                    _options_from_pool(most_common_brand, list(brand_counts.keys())),
                    "Use the product cards and compare brand repetition within the selected mission category.",
                    "Category Product List",
                    url_for("tracequest.tracequest"),
                    key_scope=selected_category_label,
                )
            )

    category_size = len(category_products)
    questions.append(
        _question(
            product,
            "hard",
            "category_size",
            f"How many products are currently available in the selected {selected_category_label} mission category?",
            str(category_size),
            _number_choices(category_size, max(0, category_size - 6), category_size + 6),
            "Use the category overview on the Trace Quest page.",
            "Mission Category Overview",
            url_for("tracequest.tracequest"),
            key_scope=selected_category_label,
        )
    )

    return questions


def _fallback_pack(category_key, difficulty, category_products):
    fallback_questions = []
    category_label = CATEGORY_INDEX[category_key]["label"]
    for product in category_products:
        fallback_questions.extend(_metadata_questions(product, category_products, difficulty, category_label))
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
        candidates.extend(_metadata_questions(product, category_products, difficulty, category_label))
        if difficulty == "normal":
            candidates.extend(_normal_questions(product, category_products))
        elif difficulty == "hard":
            candidates.extend(_hard_questions(product, category_products, category_label))

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
