from datetime import timedelta
import logging
from pydantic import BaseModel

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .hub import Hub
from .perific import LatestItemPackets, LatestPackets

_LOGGER = logging.getLogger(__name__)


class Device(BaseModel):
    id: int
    name: str
    type: str
    mac: str | None = None


class PerificCoordinator(DataUpdateCoordinator[list[LatestItemPackets]]):
    """Coordinator for per-meter packet data (~30 s polling)."""

    def __init__(self, hass: HomeAssistant, hub: Hub) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Perific Coordinator",
            update_interval=timedelta(seconds=30),
        )
        self.hub = hub
        self.devices: list[Device] = []

    async def _async_update_data(self) -> list[LatestItemPackets]:
        try:
            result = await self.hub.get_sensor_data()
            return result or []
        except Exception as e:
            _LOGGER.exception("Failed to update sensor data: %s", e)
            return []

    def get_device(self, device_id: int) -> Device | None:
        """Return the Device with the given id, or None."""
        for device in self.devices:
            if device.id == device_id:
                return device
        return None

    def get_device_data(self, device_id: int) -> LatestPackets | None:
        """Return the LatestPackets for the given device, or None."""
        if not self.data:
            _LOGGER.warning("No data available in coordinator")
            return None
        for item in self.data:
            if item.item_id == device_id:
                return item.latest_packets
        return None


class PerificReporterCoordinator(DataUpdateCoordinator[dict]):
    """Coordinator for account-level Zaptec reporter settings (~60 s polling)."""

    def __init__(self, hass: HomeAssistant, hub: Hub) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Perific Reporter Coordinator",
            update_interval=timedelta(seconds=60),
        )
        self.hub = hub

    async def _async_update_data(self) -> dict:
        try:
            result = await self.hub.get_reporter_settings()
            return result or {}
        except Exception as e:
            _LOGGER.exception("Failed to update reporter settings: %s", e)
            return {}
