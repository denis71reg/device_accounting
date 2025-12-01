import logging

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from ..models import Warehouse
from ..services import WarehouseService
from ..utils import admin_required

warehouses_bp = Blueprint("warehouses", __name__, template_folder="../templates")
logger = logging.getLogger(__name__)


@warehouses_bp.get("/")
@login_required
def list_warehouses():
    warehouses_with_counts = WarehouseService.get_all_warehouses_with_counts()
    return render_template("warehouses/list.html", warehouses_with_counts=warehouses_with_counts)


@warehouses_bp.route("/create", methods=["GET", "POST"])
@admin_required
def create_warehouse():
    if request.method == "POST":
        name = request.form["name"].strip()
        location_name = request.form["location_name"].strip()
        
        warehouse, error = WarehouseService.create_warehouse(name, location_name)
        
        if error:
            flash(error, "danger")
            return render_template("warehouses/form.html", warehouse=None)
            
        flash("Склад добавлен", "success")
        return redirect(url_for("warehouses.list_warehouses"))
        
    return render_template("warehouses/form.html", warehouse=None)


@warehouses_bp.route("/<int:warehouse_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_warehouse(warehouse_id: int):
    warehouse = Warehouse.query.get_or_404(warehouse_id)
    
    if request.method == "POST":
        name = request.form["name"].strip()
        location_name = request.form["location_name"].strip()
        
        success, error = WarehouseService.update_warehouse(warehouse, name, location_name)
        
        if not success:
            flash(error, "danger")
            return render_template("warehouses/form.html", warehouse=warehouse)
            
        flash("Склад обновлен", "success")
        return redirect(url_for("warehouses.list_warehouses"))
        
    return render_template("warehouses/form.html", warehouse=warehouse)


@warehouses_bp.post("/<int:warehouse_id>/delete")
@admin_required
def delete_warehouse(warehouse_id: int):
    warehouse = Warehouse.query.get_or_404(warehouse_id)
    
    success, message = WarehouseService.delete_warehouse(warehouse)
    
    if success:
        flash(message, "success")
    else:
        flash(message, "danger")
        
    return redirect(url_for("warehouses.list_warehouses"))


@warehouses_bp.get("/<int:warehouse_id>/devices")
@login_required
def warehouse_devices(warehouse_id: int):
    """Просмотр девайсов склада."""
    from ..models import Device
    
    warehouse = Warehouse.query.get_or_404(warehouse_id)
    devices = (
        Device.query
        .filter_by(warehouse_id=warehouse_id)
        .order_by(Device.created_at.desc())
        .all()
    )
    return render_template(
        "warehouses/devices.html",
        warehouse=warehouse,
        devices=devices,
    )
