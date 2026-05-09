"""The Perific Meter integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import API_URL
from .coordinator import Device, PerificCoordinator, PerificReporterCoordinator
from .hub import Hub

_LOGGER = logging.getLogger(__name__)
_PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Perific Meter from a config entry."""
    try:
        hub = Hub(API_URL)
        logged_in = await hub.authenticate(entry.data["username"], entry.data["password"])
        if not logged_in:
            _LOGGER.error("Authentication failed for user: %s", entry.data["username"])
            return False

        meter_coord = PerificCoordinator(hass, hub)
        reporter_coord = PerificReporterCoordinator(hass, hub)

        # Fetch device list before the first sensor-data refresh so that
        # coordinator.devices is populated when sensor.py iterates it.
        raw_devices = await hub.fetch_devices()
        meter_coord.devices = [
            Device(id=item.id, name=item.name, type=item.item_type, mac=item.mac_address)
            for item in raw_devices
        ]
        _LOGGER.info("Perific: found %d device(s): %s", len(meter_coord.devices),
                     [d.name for d in meter_coord.devices])

        await meter_coord.async_config_entry_first_refresh()
        await reporter_coord.async_config_entry_first_refresh()

        # Store both coordinators as a tuple; sensor.py unpacks them.
        entry.runtime_data = (meter_coord, reporter_coord)

        await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)
        return True

    except Exception as e:
        _LOGGER.exception("Unexpected error during setup: %s", e)
        return False


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry and stop both coordinators."""
    return await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)
