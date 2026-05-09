from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import PerificCoordinator, Device
from .const import DOMAIN

import logging

_LOGGER = logging.getLogger(__name__)


class PerificEntity(CoordinatorEntity[PerificCoordinator]):
    """Base entity for Perific meter devices.

    _attr_has_entity_name = True means HA prepends the device name in the UI.
    _attr_name = None so each sensor's SensorEntityDescription.name is used
    as the entity name directly — no manual prefix needed.
    """

    _attr_has_entity_name = True
    _attr_name = None
    device: Device

    def __init__(self, coordinator: PerificCoordinator, device_id: int) -> None:
        super().__init__(coordinator)
        device = coordinator.get_device(device_id)
        if not device:
            _LOGGER.error("Device with ID %s not found in coordinator", device_id)
            raise ValueError(f"Device with ID {device_id} not found")
        self.device = device
        self._attr_device_info = DeviceInfo(
            connections={(CONNECTION_NETWORK_MAC, self.device.mac)},
            identifiers={(DOMAIN, self.device.id)},
            manufacturer="Perific Technologies AB",
            model="Perific Max/One",
            name=self.device.name,
        )
