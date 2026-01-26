# flask is imported to create the web app, sqlalchemy for the SQLite DB and falsk_cors for potential errors
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

# creates a new flask web application with its root as '/config.py'
app = Flask(__name__)
CORS(app)

# sets the name and location of the DB
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///trace_quest.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True

# creates a new SQLite DB
db = SQLAlchemy(app)