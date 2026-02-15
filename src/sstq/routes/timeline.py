from flask import Blueprint, render_template
from sstq.auth_decorators import login_required

timeline_bp = Blueprint("timeline", __name__)

# allows the user to check the 'Traceability Timeline' for a given product
@timeline_bp.route("/timeline", methods=["GET"])
@login_required
def timeline():
    return render_template("timeline.html")