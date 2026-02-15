from flask import Blueprint, render_template
from sstq.auth_decorators import roles_required

admin_bp = Blueprint("admin", __name__)

# this endpoint actually contains all of the added/updated products for a VERIFIER (not necessarily an admin)
@admin_bp.route("/admin", methods=["GET"])
@roles_required("verifier", "admin")
def admin():
    return render_template("admin.html")