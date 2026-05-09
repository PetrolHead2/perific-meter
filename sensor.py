"""Perific Meter sensor platform."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import PerificCoordinator, PerificReporterCoordinator
from .entity import PerificEntity
from .perific import ItemPacketData

_LOGGER = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _safe(lst: list[float] | None, index: int) -> float | None:
    """Return lst[index] or None if the list is absent or too short."""
    if lst and len(lst) > index:
        return lst[index]
    return None


# ── Meter sensor descriptions ──────────────────────────────────────────────────

@dataclass(frozen=True, kw_only=True)
class PerificMeterSensorDescription(SensorEntityDescription):
    """SensorEntityDescription extended with a value extractor for meter data."""
    value_fn: Callable[[ItemPacketData], float | None]


_Q_TO_KWH = 19_565_000  # raw qmax units per kWh (1 unit ≈ 0.184 J, empirically derived)


METER_SENSOR_TYPES: tuple[PerificMeterSensorDescription, ...] = (
    PerificMeterSensorDescription(
        key="current_l1",
        name="Current L1",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=1,
        value_fn=lambda d: _safe(d.iavg, 0),
    ),
    PerificMeterSensorDescription(
        key="current_l2",
        name="Current L2",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=1,
        value_fn=lambda d: _safe(d.iavg, 1),
    ),
    PerificMeterSensorDescription(
        key="current_l3",
        name="Current L3",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=1,
        value_fn=lambda d: _safe(d.iavg, 2),
    ),
    PerificMeterSensorDescription(
        key="power_import_total",
        name="Power Import",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
        # No direct power field; estimate using 230 V nominal per phase.
        value_fn=lambda d: round(sum(d.iavg[:3]) * 230) if d.iavg and len(d.iavg) >= 3 else None,
    ),
    PerificMeterSensorDescription(
        key="energy_import_total",
        name="Energy Import",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=1,
        # Sum qmax across L1-L3 and convert to kWh.
        value_fn=lambda d: round(sum(d.qmax[:3]) / _Q_TO_KWH, 1) if d.qmax and len(d.qmax) >= 3 else None,
    ),
)


# ── Reporter sensor descriptions ───────────────────────────────────────────────

@dataclass(frozen=True, kw_only=True)
class PerificReporterSensorDescription(SensorEntityDescription):
    """SensorEntityDescription extended with a value extractor for reporter data."""
    value_fn: Callable[[dict], float | str | None]


REPORTER_SENSOR_TYPES: tuple[PerificReporterSensorDescription, ...] = (
    PerificReporterSensorDescription(
        key="zaptec_allowed_current",
        name="Perific Zaptec Allowed Current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=0,
        value_fn=lambda d: d.get("AllowedCurrent"),
    ),
    PerificReporterSensorDescription(
        key="zaptec_mains_fuse",
        name="Perific Mains Fuse",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=0,
        value_fn=lambda d: d.get("MainsFuseLevel"),
    ),
    PerificReporterSensorDescription(
        key="zaptec_safe_mode_current",
        name="Perific Safe Mode Current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=0,
        value_fn=lambda d: d.get("SafeModeCurrent"),
    ),
    PerificReporterSensorDescription(
        key="zaptec_charging_mode",
        name="Perific Charging Mode",
        device_class=None,
        state_class=None,
        native_unit_of_measurement=None,
        value_fn=lambda d: d.get("Mode"),
    ),
)


# ── Platform setup ─────────────────────────────────────────────────────────────

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up all Perific sensor entities for this config entry."""
    meter_coord, reporter_coord = config_entry.runtime_data

    entities: list[SensorEntity] = []

    # One set of meter sensors per device (API returns ItemType "Measurement")
    for device in meter_coord.devices:
        for desc in METER_SENSOR_TYPES:
            entities.append(PerificMeterSensor(meter_coord, device.id, desc))

    # Account-level reporter sensors (no device loop)
    for desc in REPORTER_SENSOR_TYPES:
        entities.append(PerificReporterSensor(reporter_coord, config_entry.entry_id, desc))

    async_add_entities(entities)


# ── Entity classes ─────────────────────────────────────────────────────────────

class PerificMeterSensor(PerificEntity, SensorEntity):
    """Sensor entity backed by the per-meter coordinator (PhaseRealTime data)."""

    entity_description: PerificMeterSensorDescription

    def __init__(
        self,
        coordinator: PerificCoordinator,
        device_id: int,
        description: PerificMeterSensorDescription,
    ) -> None:
        PerificEntity.__init__(self, coordinator, device_id)
        SensorEntity.__init__(self)
        self.entity_description = description
        # unique_id is stable: {device_id}_{sensor_key}
        # Preserves current_l1/l2/l3 and voltage_l1/l2/l3 from the original integration.
        self._attr_unique_id = f"{self.device.id}_{description.key}"
        # Override _attr_name = None inherited from PerificEntity so HA uses the
        # description name ("Current L1", etc.) rather than treating this entity
        # as the device itself (which produces sensor.main, sensor.main_2, …).
        self._attr_name = description.name

    @property
    def native_value(self) -> float | None:
        """Return the sensor value extracted from PhaseRealTime packet data."""
        packets = self.coordinator.get_device_data(self.device.id)
        if not packets or not packets.phase_real_time:
            return None
        try:
            return self.entity_description.value_fn(packets.phase_real_time.data)
        except Exception:
            _LOGGER.exception(
                "Error computing value for sensor '%s' on device %s",
                self.entity_description.key,
                self.device.id,
            )
            return None


class PerificReporterSensor(CoordinatorEntity[PerificReporterCoordinator], SensorEntity):
    """Sensor entity backed by the account-level reporter coordinator."""

    _attr_has_entity_name = True
    entity_description: PerificReporterSensorDescription

    def __init__(
        self,
        coordinator: PerificReporterCoordinator,
        entry_id: str,
        description: PerificReporterSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.key}"

    @property
    def native_value(self) -> float | str | None:
        """Return the value extracted from the latest reporter settings dict."""
        if not self.coordinator.data:
            return None
        try:
            return self.entity_description.value_fn(self.coordinator.data)
        except Exception:
            _LOGGER.exception(
                "Error computing value for reporter sensor '%s'",
                self.entity_description.key,
            )
            return None
