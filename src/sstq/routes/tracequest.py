from flask import Blueprint, render_template
from sstq.auth_decorators import login_required

tracequest_bp = Blueprint("tracequest", __name__)

# allows the player to play 'Trace Quest' with a given product
@tracequest_bp.route("/trace_quest", methods=["GET"])
@login_required
def tracequest():
    return render_template("tracequest.html")