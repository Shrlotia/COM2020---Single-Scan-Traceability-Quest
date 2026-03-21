from pathlib import Path

from sstq.extensions import db
from sstq.models import Breakdown, Claim, Evidence, Issue, Product, Stage


def test_delete_product_removes_related_records_and_image(logged_in_client, app_instance):
    barcode = "0123456789123"
    image_url = "/static/uploads/products/delete-me.jpg"

    with app_instance.app_context():
        product = Product(
            barcode=barcode,
            name="Delete Me",
            category="Food",
            brand="Brand X",
            description="Product slated for deletion",
            image=image_url,
        )
        db.session.add(product)
        db.session.flush()

        db.session.add(
            Stage(
                product_barcode=barcode,
                stage_type="Processing",
                country="United Kingdom",
                description="Process step",
            )
        )
        db.session.add(
            Breakdown(
                product_barcode=barcode,
                breakdown_name="Ingredient",
                country="Italy",
                percentage=100.0,
            )
        )

        claim = Claim(
            product_barcode=barcode,
            claim_type="Origin",
            claim_text="Sourced under a verified process.",
        )
        db.session.add(claim)
        db.session.flush()

        db.session.add(
            Evidence(
                claim_id=claim.claim_id,
                evidence_type="Certificate",
                summary="Backs the claim.",
            )
        )
        db.session.add(
            Issue(
                claim_id=claim.claim_id,
                issue_type="Accuracy",
                description="Needs review.",
            )
        )
        db.session.commit()

        image_path = Path(app_instance.static_folder) / "uploads" / "products" / "delete-me.jpg"
        image_path.parent.mkdir(parents=True, exist_ok=True)
        image_path.write_text("fake image data", encoding="utf-8")

    response = logged_in_client.post(f"/product/{barcode}/delete", follow_redirects=True)

    assert response.status_code == 200
    assert b"Product deleted successfully." in response.data

    with app_instance.app_context():
        assert db.session.get(Product, barcode) is None
        assert Stage.query.filter_by(product_barcode=barcode).count() == 0
        assert Breakdown.query.filter_by(product_barcode=barcode).count() == 0
        assert Claim.query.filter_by(product_barcode=barcode).count() == 0
        assert Evidence.query.count() == 0
        assert Issue.query.count() == 0

    assert not image_path.exists()
