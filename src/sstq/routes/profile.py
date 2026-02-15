from flask import Blueprint, render_template
from sstq.auth_decorators import login_required

profile_bp = Blueprint("profile", __name__)

# shows a profile page for each player with their stats, completed missions and potential leaderboard (2nd sprint only)
@profile_bp.route("/profile", methods=["GET"])
@login_required
def profile():
    return render_template("profile.html")