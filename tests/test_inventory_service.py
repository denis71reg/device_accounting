from da.extensions import db
from da.models import Device, DeviceType, Location
from da.services.inventory import InventoryService


def test_inventory_service_flow(app, seed_basics):
    with app.app_context():
        location = db.session.get(Location, seed_basics["location_id"])
        device_type = db.session.get(DeviceType, seed_basics["device_type_id"])

        device = InventoryService.create_device(
            inventory_number="INV-2",
            model="Lenovo ThinkPad",
            type_id=device_type.id,
            location_id=location.id,
            serial_number="SN123",
            notes="Закуплен для тестов",
        )

        InventoryService.update_device(device, model="Lenovo ThinkPad X1 Carbon")
        refreshed = db.session.get(Device, device.id)
        assert refreshed.model == "Lenovo ThinkPad X1 Carbon"

        InventoryService.delete_device(refreshed)
        assert db.session.get(Device, device.id) is None

