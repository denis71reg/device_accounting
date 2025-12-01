from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy.orm import joinedload

from ..models import Device

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.get("/")
@login_required
def index():
    devices = (
        Device.query.filter(Device.deleted_at.is_(None))
        .options(
            joinedload(Device.type),
            joinedload(Device.location),
            joinedload(Device.owner),
            joinedload(Device.warehouse)
        )
        .order_by(Device.created_at.desc())
        .all()
    )
    return render_template("index.html", devices=devices)





