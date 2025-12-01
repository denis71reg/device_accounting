from flask import Flask

from .audit import audit_bp
from .auth import auth_bp
from .dashboard import dashboard_bp
from .deleted import deleted_bp
from .device_types import device_types_bp
from .devices import devices_bp
from .employees import employees_bp
from .locations import locations_bp
from .users import users_bp
from .warehouses import warehouses_bp


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(audit_bp, url_prefix="/audit")
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(deleted_bp, url_prefix="/deleted")
    app.register_blueprint(device_types_bp, url_prefix="/device-types")
    app.register_blueprint(devices_bp, url_prefix="/devices")
    app.register_blueprint(employees_bp, url_prefix="/employees")
    app.register_blueprint(locations_bp, url_prefix="/locations")
    app.register_blueprint(users_bp, url_prefix="/users")
    app.register_blueprint(warehouses_bp, url_prefix="/warehouses")





