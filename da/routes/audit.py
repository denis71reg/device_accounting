from flask import Blueprint, render_template

from ..services.audit import get_audit_logs
from ..utils import super_admin_required

audit_bp = Blueprint("audit", __name__, template_folder="../templates")


@audit_bp.route("/")
@super_admin_required
def list_logs():
    logs = get_audit_logs(limit=200)
    return render_template("audit/list.html", logs=logs)





