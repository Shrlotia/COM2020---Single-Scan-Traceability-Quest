# imports the 'db' object from 'config.py'
from config import db

# represents a DB table
class Contact(db.Model):
    # variables have their data type and properties listed
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80), unique=False, nullable=False)
    last_name = db.Column(db.String(80), unique=False, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    
    # allows for data to be passed as JSON through HTTP requests
    def to_json(self):
        return {
            # use camel case for JSON
            "id": self.id,
            "firstName": self.first_name,
            "lastName": self.last_name,
            "email": self.email
        }
    