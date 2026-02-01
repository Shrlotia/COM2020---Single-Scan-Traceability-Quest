# flask is imported to create the web app, sqlalchemy for the SQLite DB and falsk_cors for potential errors
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os

# creates a new flask web application with its root as '/config.py'
app = Flask(__name__)
CORS(app)

# THE CODE BELOW defines the 'secret' (encryption key) for the web app (its thanks to this that authentication can be secure)

# os.environment.get(...) - stores the app secret in an environment variable, outside of the program (only after the app is finished) 
# os.urandom(32) - makes the secret random everytime the app is run; useful when you want users to be logged out on restart
# "temp" - makes the secret the same everytime and users can only be logged out when the browser is closed

# UN-COMMENT one of the three lines below if you need to test something

# app.secret_key = os.environ.get("SECRET_KEY", "backup")
app.secret_key = os.urandom(32)
# app.secret_key = "temp"

# by running the code below in the terminal, the value of 'x' is stored as an environment variable, taking it out
# of the program and making the encryption secure (this will only be used once the app is fully finished and deployed) 

# export SECRET_KEY="x"

# sets the name and location of the DB
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///trace_quest.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# creates a new SQLite DB
db = SQLAlchemy(app)