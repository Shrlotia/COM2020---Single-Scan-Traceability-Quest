from sstq.extensions import db
from sstq.models import Breakdown, Claim, Evidence, Mission, Player, Product, Stage


def _seed_tracequest_product(app_instance):
    with app_instance.app_context():
        product = Product(
            barcode="SNACK-001",
            name="Quest Snack",
            category="Snacks",
            brand="Trace Brand",
            description="Product used for dynamic mission generation tests.",
        )
        db.session.add(product)
        db.session.flush()

        db.session.add_all(
            [
                Stage(
                    product_barcode=product.barcode,
                    stage_type="Raw Materials",
                    country="Spain",
                    description="Ingredients sourced.",
                ),
                Stage(
                    product_barcode=product.barcode,
                    stage_type="Assembly",
                    country="United Kingdom",
                    description="Final assembly.",
                ),
                Breakdown(
                    product_barcode=product.barcode,
                    breakdown_name="Cocoa",
                    country="Spain",
                    percentage=60,
                    notes="Primary ingredient",
                ),
                Breakdown(
                    product_barcode=product.barcode,
                    breakdown_name="Sugar",
                    country="Brazil",
                    percentage=40,
                    notes="Secondary ingredient",
                ),
            ]
        )

        claim = Claim(
            product_barcode=product.barcode,
            claim_type="Origin",
            claim_text="Ingredients are traceable to source countries.",
            confidence_label="verified",
            rationale="Checked against supplier evidence.",
        )
        db.session.add(claim)
        db.session.flush()

        db.session.add(
            Evidence(
                claim_id=claim.claim_id,
                evidence_type="Certificate",
                issuer="Trace Lab",
                summary="Supports the origin claim.",
            )
        )
        db.session.commit()


def test_tracequest_creates_dynamic_mission_history(logged_in_client, app_instance):
    _seed_tracequest_product(app_instance)

    response = logged_in_client.post(
        "/trace_quest",
        data={"mission_category": "snacks", "difficulty": "easy"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/misson/" in response.headers["Location"]

    with app_instance.app_context():
        player = Player.query.first()
        rows = Mission.query.filter_by(player_id=player.player_id).order_by(Mission.question_number.asc()).all()

        assert len(rows) == 6
        assert len({row.mission_group_id for row in rows}) == 1
        assert all(row.completed_at is None for row in rows)
        assert all(row.player_answer == "" for row in rows)
        assert all(row.product_barcode == "SNACK-001" for row in rows)


def test_mission_rows_become_history_after_submission(logged_in_client, app_instance):
    _seed_tracequest_product(app_instance)
    logged_in_client.post(
        "/trace_quest",
        data={"mission_category": "snacks", "difficulty": "easy"},
        follow_redirects=False,
    )

    with app_instance.app_context():
        player = Player.query.first()
        rows = Mission.query.filter_by(player_id=player.player_id).order_by(Mission.question_number.asc()).all()
        mission_id = rows[0].mission_id
        answers = {f"answer_{row.question_number}": row.answer for row in rows}

    response = logged_in_client.post(
        f"/misson/{mission_id}",
        data=answers,
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app_instance.app_context():
        player = Player.query.first()
        rows = Mission.query.filter_by(player_id=player.player_id).order_by(Mission.question_number.asc()).all()

        assert all(row.completed_at is not None for row in rows)
        assert all(row.score == 6 for row in rows)
        assert player.points > 0
