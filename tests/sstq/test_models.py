from sstq.config import db
from sstq.models import User, Product, Stage, Claim, Evidence, Player
from sqlalchemy.exc import IntegrityError
import pytest

def test_create_user(client):
    with client.application.app_context():
        user = User(username="johnny", role="consumer")
        user.set_password("abcd1234")

        db.session.add(user)
        db.session.commit()

        saved = User.query.filter_by(username="johnny").first()

        assert saved is not None
        assert saved.check_password("abcd1234")
        #each value needs to have its own hash, so for the same value you will get the same hash even if it's not the same object
        assert saved.password_hash != "abcd1234"

def test_duplicate_username_raises(client):
    with client.application.app_context():
        u1 = User(username="johnny", role="consumer")
        u1.set_password("1234")

        db.session.add(u1)
        db.session.commit()

        u2 = User(username="johnny", role="consumer")
        u2.set_password("1234")

        db.session.add(u2)

        with pytest.raises(IntegrityError):
            db.session.commit()

def test_user_roles(client):
    with client.application.app_context():
        user = User(username="simba", role="admin")
        user.set_password("abcd1234")

        db.session.add(user)
        db.session.commit()

        #only users with the role "admin" should pass these checks
        assert user.is_admin
        assert not user.is_consumer
        assert not user.is_verifier

#test to ensure that the foreign key correctly links to the product, and verify that the SQLAlchemy backreferences are bidirectionally valid.
def test_product_stage_relationship(client):
    with client.application.app_context():
        product = Product(   
            barcode="77777",
            name="Chips",
            category="Snacks",
            brand="Doritos",
            description="Doritos Tortilla Chips Tangy Cheese"
        )

        stage = Stage(
            product_barcode="77777",
            stage_type="Processing",
            country="United States",
            description="Processed here"
        )

        db.session.add_all([product, stage])
        db.session.commit()

        assert product.stages
        assert product.stages[0].stage_type == "Processing"

#Same as testing the relationship of product and stage 
def test_claim_evidence_relationship(client):
    with client.application.app_context():
        product = Product(
            barcode="8888",
            name="Chips",
            category="Snacks",
            brand="Doritos",
            description="Doritos Tortilla Chips Tangy Cheese"
        )

        claim = Claim(
            product_barcode="8888",
            claim_type="Organic Certification",
            claim_text="abcdefg"
        )

        evidence = Evidence(
            claim=claim,
            evidence_type="Certificate"
        )

        db.session.add_all([product, claim, evidence])
        db.session.commit()

        assert evidence.claim == claim
        assert claim.evidence[0].evidence_type == "Certificate"

#test the 1 to 1 relationship between user and player
def test_user_player_relationship(client):
    with client.application.app_context():
        user = User(username="faker", role="consumer")
        user.set_password("abcd1234")
        db.session.add(user)
        db.session.commit()
        #players can create an account using a valid user_id
        player = Player(user_id=user.user_id)
        db.session.add(player)
        db.session.commit()

        assert user.player.player_id == player.player_id