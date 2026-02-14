# imports the 'db' object from 'config.py'
from sstq.config import db

from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# table for all the products in the DB - the same ones that can be viewed in the Timeline and Trace Quest
class Product(db.Model):
    __tablename__ = "products"
    
    barcode = db.Column(db.String(32), primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    category = db.Column(db.String(128), nullable=False)
    brand = db.Column(db.String(128), nullable=False)
    description = db.Column(db.String(512), nullable=False)
    image = db.Column(db.String(256), nullable=True)
    
    # '__repr__' methods can be used to easily check/test table records
    def __repr__(self):
        return f"Barcode: {self.barcode} - Name: {self.name}"
    
# table for every possible stage in the product 'creation' process (i.e.: raw materials, processing, etc.)
class Stage(db.Model):
    __tablename__ = "stages"
    
    stage_id = db.Column(db.Integer, primary_key=True)
    product_barcode = db.Column(db.String(32), db.ForeignKey("products.barcode"), nullable=False)
    stage_type = db.Column(db.String(64), nullable=False)
    country = db.Column(db.String(128), nullable=False)
    region = db.Column(db.String(128), nullable=True)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    description = db.Column(db.String(256), nullable=False)
    
    # in the SQLAlchemy module, you can create 'backrefs' that create a 2-way connection between a table with a foreign key and the table
    # which the foreign key is pointing to. This is purely inside of python and does NOT affect the SQL at all
    # essentially, you can access the 'stage' from the 'product' and vice versa with one line of code
    product = db.relationship("Product", backref="stages")
    
    def __repr__(self):
        return f"Stage ID: {self.stage_id} - Stage Type: {self.stage_type} - {self.product}"
    
class Breakdown(db.Model):
    __tablename__ = "breakdowns"

    breakdown_id = db.Column(db.Integer, primary_key=True)
    product_barcode = db.Column(db.String(32), db.ForeignKey("products.barcode"), nullable=False)
    breakdown_name = db.Column(db.String(128), nullable=False)
    country = db.Column(db.String(128), nullable=False)
    percentage = db.Column(db.Float, nullable=False)
    notes = db.Column(db.String(256), nullable=True)

    product = db.relationship("Product", backref="breakdowns")

    def __repr__(self):
        return f"Breakdown ID: {self.breakdown_id} - Breakdown Percentage: {self.percentage} - Breakdown Country: {self.country} - {self.product}"
    
class Claim(db.Model):
    __tablename__ = "claims"

    claim_id = db.Column(db.Integer, primary_key=True)
    product_barcode = db.Column(db.String(32), db.ForeignKey("products.barcode"), nullable=False)
    claim_type = db.Column(db.String(64), nullable=False)
    claim_text = db.Column(db.String(512), nullable=False)
    confidence_label = db.Column(db.String(64), nullable=True) # verified, partially-verified or unverified
    rationale = db.Column(db.String(512), nullable=True)

    product = db.relationship("Product", backref="claims")

    def __repr__(self):
        return f"Claim ID: {self.claim_id} - Claim Type: {self.claim_type} - Confidence Label: {self.confidence_label} - {self.product}"
    
class Evidence(db.Model):
    __tablename__ = "evidence"
    
    evidence_id = db.Column(db.Integer, primary_key=True)
    claim_id = db.Column(db.Integer, db.ForeignKey("claims.claim_id"), nullable=False)
    evidence_type = db.Column(db.String(64), nullable=False)
    issuer = db.Column(db.String(128), nullable=True)
    date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    summary = db.Column(db.String(512), nullable=True)
    file_reference = db.Column(db.String(256), nullable=True)
    
    claim = db.relationship("Claim", backref="evidence")

    def __repr__(self):
        return f"Evidence ID: {self.evidence_id} - Evidence Type: {self.evidence_type} - {self.claim}"
    
class Issue(db.Model):
    __tablename__ = "issues"

    issue_id = db.Column(db.Integer, primary_key=True)
    claim_id = db.Column(db.Integer, db.ForeignKey("claims.claim_id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=True) # 'anon' (null) or user id from 'User' in 'auth.py'
    issue_type = db.Column(db.String(64), nullable=False)
    description = db.Column(db.String(512), nullable=False)
    status = db.Column(db.String(32), nullable=False, default="open")
    resolution_note = db.Column(db.String(512), nullable=True)

    claim = db.relationship("Claim", backref="issues")
    user = db.relationship("User", backref="issues")

    def __repr__(self):
        return f"Issue ID: {self.issue_id} - Claim ID for this issue: {self.claim_id} - {self.user} - Issue Type: {self.issue_type}"
    
class Player(db.Model):
    __tablename__ = "players"    
    
    player_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), unique=True, nullable=False)
    points = db.Column(db.Integer, default=0, nullable=False)
    
    user = db.relationship("User", backref=db.backref("player", uselist=False))
    
    def __repr__(self):
        return f"Player ID: {self.player_id} - {self.user}"
    
class Mission(db.Model):
    __tablename__ = "missions"
    
    mission_id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey("players.player_id"), nullable=False)
    tier = db.Column(db.String(16), nullable=False)
    question = db.Column(db.String(128), nullable=False)
    player_answer = db.Column(db.String(128), nullable=False)
    answer = db.Column(db.String(128), nullable=False)
    all_answers = db.Column(db.String(128), nullable=False) #comma separated list with no spaces
    explanation = db.Column(db.String(256), nullable=False)
    
    player = db.relationship("Player", backref="missions")
    
    def __repr__(self):
        return f"Mission ID: {self.mission_id} - {self.player} - Tier: {self.tier} - Question: {self.question} - Answer: {self.answer}"
    
class Badge(db.Model):
    __tablename__ = "badges"
    
    badge_id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey("players.player_id"), nullable=False)
    name = db.Column(db.String(128), nullable=False)
    tier = db.Column(db.String(16), nullable=False)
    
    player = db.relationship("Player", backref="badges")
    
    def __repr__(self):
        return f"Badge ID: {self.badge_id} - {self.player} - Badge Name: {self.name} - Tier: {self.tier}"
    
    
class ChangeLog(db.Model):
    __tablename__ = "changelogs"
    
    log_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    change_summary = db.Column(db.String(512), nullable=False)

    user = db.relationship("User", backref="changelogs")

    def __repr__(self):
        return f"Changelog ID: {self.log_id} - {self.user} - Timestamp: {self.timestamp}"
    
class User(db.Model, UserMixin):
    __tablename__ = "users"
    
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    role = db.Column(db.String(16), default="consumer", nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    
    def get_id(self):
        return str(self.user_id)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @property
    def is_consumer(self):
        return self.role == "consumer"
    
    @property
    def is_verifier(self):
        return self.role == "verifier"
    
    @property
    def is_admin(self):
        return self.role == "admin"
    
    def __repr__(self):
        return f"User ID: {self.user_id} - Username: {self.username} - Role: {self.role}"
