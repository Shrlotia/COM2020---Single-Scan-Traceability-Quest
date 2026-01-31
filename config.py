# flask is imported to create the web app, sqlalchemy for the SQLite DB and falsk_cors for potential errors
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os

# creates a new flask web application with its root as '/config.py'
app = Flask(__name__)
CORS(app)

# THE CODE BELOW defines the secret (encryption key) for the web app (its thanks to this that authentication can be secure)
# furthermore, by running the second line in the terminal, that value is stored as an environment variable, taking it out
# of the program and making the encryption secure (this will only be used once the app is fully finished and deployed) 

# app.secret_key = os.environ.get("SECRET_KEY", "backup")
# export SECRET_KEY="x"

app.secret_key = "temp"

# sets the name and location of the DB
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///trace_quest.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# creates a new SQLite DB
db = SQLAlchemy(app)