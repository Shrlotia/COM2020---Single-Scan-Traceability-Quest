# imports all tools for requesting and responding to HTTP requests, as well as the 'app', 'db' and 'Contact' elements
from flask import request, jsonify, render_template
from config import app, db

# connects to the index (/) of the web app and shows the default view
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

# when this file is ran, the DB is created and application is started
if __name__ == "__main__":  
    with app.app_context():
        db.create_all()
        
    app.run(debug=True)