from flask import Blueprint, render_template

home_bp = Blueprint("home", __name__)

# connects to the index (/) of the web app and shows the homepage, full of useful information
# the 'GET' part tells us what HTTP requests the endpoint can handle (this one just shows data)
@home_bp.route("/", methods=["GET"])
def home():
    # render a html template (webpage); this doesn't refresh the browser window
    return render_template("home.html")