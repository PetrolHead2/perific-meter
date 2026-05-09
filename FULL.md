# Full API Coverage — Implementation Plan

## Overview

This document maps every field returned by the Enegic API to a proposed Home Assistant sensor, and organises the work into four implementation phases. The goal is to expose all useful fields as HA entities so the integration covers the full feature set of the Perific device. Nine sensors are already live (see below); this document covers the remaining fields only.

---

## Currently Implemented

| Entity ID (example device "measurement") | Friendly name | Status |
|---|---|---|
| `sensor.perific_measurement_current_l1` | Current L1 | ✅ Live |
| `sensor.perific_measurement_current_l2` | Current L2 | ✅ Live |
| `sensor.perific_measurement_current_l3` | Current L3 | ✅ Live |
| `sensor.perific_measurement_power_import` | Power Import | ✅ Live |
| `sensor.perific_measurement_energy_import` | Energy Import | ✅ Live |
| `sensor.perific_zaptec_allowed_current` | Perific Zaptec Allowed Current | ✅ Live |
| `sensor.perific_mains_fuse` | Perific Mains Fuse | ✅ Live |
| `sensor.perific_safe_mode_current` | Perific Safe Mode Current | ✅ Live |
| `sensor.perific_charging_mode` | Perific Charging Mode | ✅ Live |

---

## Phase 1 — Additional Meter Sensors

Source: `PhaseRealTime.data` via `PUT /getlatestpackets`. Polled every 30 s.

`imin` and `imax` are **already present** in `ItemPacketData` in `perific/client.py` (lines 31–32). No model changes required — only new entries in `METER_SENSOR_TYPES` in `sensor.py`.

### Current Min — L1 / L2 / L3

| Property | L1 | L2 | L3 |
|---|---|---|---|
| **Proposed entity_id** | `sensor.perific_measurement_current_min_l1` | `sensor.perific_measurement_current_min_l2` | `sensor.perific_measurement_current_min_l3` |
| **Friendly name** | Current Min L1 | Current Min L2 | Current Min L3 |
| **API field** | `imin[0]` | `imin[1]` | `imin[2]` |
| **Unit** | A | A | A |
| **device_class** | `current` | `current` | `current` |
| **state_class** | `measurement` | `measurement` | `measurement` |
| **value_fn** | `_safe(d.imin, 0)` | `_safe(d.imin, 1)` | `_safe(d.imin, 2)` |

**Implementation notes:** Minimum current recorded within the reporting interval (between polls). Useful for detecting periods of genuinely low load. Uses the existing `_safe()` helper — no new code needed beyond adding the three sensor descriptions.

### Current Max — L1 / L2 / L3

| Property | L1 | L2 | L3 |
|---|---|---|---|
| **Proposed entity_id** | `sensor.perific_measurement_current_max_l1` | `sensor.perific_measurement_current_max_l2` | `sensor.perific_measurement_current_max_l3` |
| **Friendly name** | Current Max L1 | Current Max L2 | Current Max L3 |
| **API field** | `imax[0]` | `imax[1]` | `imax[2]` |
| **Unit** | A | A | A |
| **device_class** | `current` | `current` | `current` |
| **state_class** | `measurement` | `measurement` | `measurement` |
| **value_fn** | `_safe(d.imax, 0)` | `_safe(d.imax, 1)` | `_safe(d.imax, 2)` |

**Implementation notes:** Maximum current within the reporting interval. Useful for detecting peak demand events that occur between 30-second polls and would otherwise be invisible. Same `_safe()` helper, same three-entry pattern.

### Energy Import — L1 / L2 / L3 (per-phase)

| Property | L1 | L2 | L3 |
|---|---|---|---|
| **Proposed entity_id** | `sensor.perific_measurement_energy_import_l1` | `sensor.perific_measurement_energy_import_l2` | `sensor.perific_measurement_energy_import_l3` |
| **Friendly name** | Energy Import L1 | Energy Import L2 | Energy Import L3 |
| **API field** | `qmax[0]` | `qmax[1]` | `qmax[2]` |
| **Unit** | kWh | kWh | kWh |
| **device_class** | `energy` | `energy` | `energy` |
| **state_class** | `total_increasing` | `total_increasing` | `total_increasing` |
| **value_fn** | `round(d.qmax[0] / 19_565_000, 1) if d.qmax and len(d.qmax) > 0 else None` | `round(d.qmax[1] / 19_565_000, 1) if d.qmax and len(d.qmax) > 1 else None` | `round(d.qmax[2] / 19_565_000, 1) if d.qmax and len(d.qmax) > 2 else None` |

**Implementation notes:** Per-phase breakdown of the cumulative energy counter. Useful for unbalanced-load analysis — a three-phase installation with a single-phase EV charger will show a large asymmetry between phases. The existing `_Q_TO_KWH = 19_565_000` constant is reused. Compatible with the HA Energy Dashboard once `state_class: total_increasing` is set.

---

## Phase 2 — Additional Reporter Sensors

Source: `GET /getreporterssettingsforuser`. Polled every 60 s.

`client.py:getReporterSettings()` merges `SimpleSettings` and `UserSettings` into a single flat dict. Fields at the **root level** of the reporter object (`ReporterId`, `InstallationId`, `AlgorithmType`, `DataType`) are **not** in the merged dict and require a one-line change to `getReporterSettings()` to extract them:

```python
settings["AlgorithmType"] = first.get("AlgorithmType")
```

All other sensors below use `d.get(key)` directly against the merged dict.

### Charger Fuse

| Property | Value |
|---|---|
| **Proposed entity_id** | `sensor.perific_charger_fuse` |
| **Friendly name** | Perific Charger Fuse |
| **API field** | `ChargerFuseLevel` (SimpleSettings) |
| **Unit** | A |
| **device_class** | `current` |
| **state_class** | `measurement` |
| **value_fn** | `d.get("ChargerFuseLevel")` |

**Implementation notes:** Per-charger fuse ceiling, as distinct from `MainsFuseLevel` (whole-house). Additive — no structural changes.

### Phase Current Override — L1 / L2 / L3

| Property | L1 | L2 | L3 |
|---|---|---|---|
| **Proposed entity_id** | `sensor.perific_phase_override_l1` | `sensor.perific_phase_override_l2` | `sensor.perific_phase_override_l3` |
| **Friendly name** | Perific Phase Override L1 | Perific Phase Override L2 | Perific Phase Override L3 |
| **API field** | `PhaseCurrentOverride[0]` | `PhaseCurrentOverride[1]` | `PhaseCurrentOverride[2]` |
| **Unit** | A | A | A |
| **device_class** | `current` | `device_class` | `current` |
| **state_class** | `measurement` | `measurement` | `measurement` |
| **value_fn** | `_phase_override(d, 0)` | `_phase_override(d, 1)` | `_phase_override(d, 2)` |

`_phase_override` helper (add to `sensor.py`):
```python
def _phase_override(d: dict, i: int) -> float | None:
    lst = d.get("PhaseCurrentOverride") or []
    if i >= len(lst):
        return None
    val = lst[i]
    return None if val == -1 else float(val)
```

**Implementation notes:** `-1` is the sentinel for "automatic, no override active" — must return `None` / `unknown` rather than `-1 A`. When a value other than `-1` is present, Perific is actively holding that phase to that current limit. The helper returns `None` for the sentinel; HA will display the state as `unknown`.

### Delay Resume

| Property | Value |
|---|---|
| **Proposed entity_id** | `sensor.perific_delay_resume` |
| **Friendly name** | Perific Delay Resume |
| **API field** | `DelayResume` (SimpleSettings) |
| **Unit** | s |
| **device_class** | `duration` |
| **state_class** | `measurement` |
| **value_fn** | `d.get("DelayResume")` |

**Implementation notes:** Seconds the charger waits before resuming after a stop event. Rarely changes but useful to surface for diagnostics.

### Solar Enabled

| Property | Value |
|---|---|
| **Proposed entity_id** | `binary_sensor.perific_solar_enabled` |
| **Friendly name** | Perific Solar Enabled |
| **API field** | `SolarSettings.Enabled` (UserSettings) |
| **Platform** | `binary_sensor` (not `sensor`) |
| **value_fn** | `bool((d.get("SolarSettings") or {}).get("Enabled", False))` |

**Implementation notes:** Requires adding `binary_sensor.py` to the integration and registering `Platform.BINARY_SENSOR` in `__init__.py`. `SolarSettings` may be `null` (when solar mode is unconfigured) — guard with `or {}` before accessing nested keys.

### Solar Max Level

| Property | Value |
|---|---|
| **Proposed entity_id** | `sensor.perific_solar_max_level` |
| **Friendly name** | Perific Solar Max Level |
| **API field** | `SolarSettings.SolarMaxLevel` (UserSettings) |
| **Unit** | A |
| **device_class** | `current` |
| **state_class** | `measurement` |
| **value_fn** | `(d.get("SolarSettings") or {}).get("SolarMaxLevel")` |

**Implementation notes:** Maximum charger current in solar mode. Returns `None` when `SolarSettings` is null.

### Solar Start Level

| Property | Value |
|---|---|
| **Proposed entity_id** | `sensor.perific_solar_start_level` |
| **Friendly name** | Perific Solar Start Level |
| **API field** | `SolarSettings.SolarStartLevel` (UserSettings) |
| **Unit** | A |
| **device_class** | `current` |
| **state_class** | `measurement` |
| **value_fn** | `(d.get("SolarSettings") or {}).get("SolarStartLevel")` |

**Implementation notes:** Minimum surplus export current required before solar charging starts. **Can be negative** — a negative value means the house must be exporting at least that many amps before charging begins. `device_class: current` accepts negative values; no special handling needed.

### Previous Mode

| Property | Value |
|---|---|
| **Proposed entity_id** | `sensor.perific_previous_mode` |
| **Friendly name** | Perific Previous Mode |
| **API field** | `PreviousMode` (UserSettings) |
| **Unit** | — |
| **device_class** | none |
| **state_class** | none |
| **value_fn** | `d.get("PreviousMode")` |

**Implementation notes:** The mode active before the current one. Mostly static. Consider a slow poll (300 s) rather than 60 s for this and `algorithm_type`.

### Algorithm Type

| Property | Value |
|---|---|
| **Proposed entity_id** | `sensor.perific_algorithm_type` |
| **Friendly name** | Perific Algorithm Type |
| **API field** | `AlgorithmType` (reporter root level — not in merged dict today) |
| **Unit** | — |
| **device_class** | none |
| **state_class** | none |
| **value_fn** | `d.get("AlgorithmType")` |

**Implementation notes:** Requires the one-line change to `client.py:getReporterSettings()` noted at the top of this section to extract the root-level field into the settings dict. Essentially static; consider fetching once at setup or using a slow poll.

---

## Phase 3 — Derived / Template Sensors

These sensors are computable from already-live entities and belong in `configuration.yaml`, not in the integration itself. No Python changes required.

### Available Current — L1 / L2 / L3

Headroom remaining before the mains fuse trips, per phase.

```yaml
template:
  - sensor:
      - name: "Available Current L1"
        unit_of_measurement: "A"
        device_class: current
        state_class: measurement
        state: >
          {{ (states('sensor.perific_mains_fuse') | float(0))
             - (states('sensor.perific_measurement_current_l1') | float(0)) | round(1) }}
      - name: "Available Current L2"
        unit_of_measurement: "A"
        device_class: current
        state_class: measurement
        state: >
          {{ (states('sensor.perific_mains_fuse') | float(0))
             - (states('sensor.perific_measurement_current_l2') | float(0)) | round(1) }}
      - name: "Available Current L3"
        unit_of_measurement: "A"
        device_class: current
        state_class: measurement
        state: >
          {{ (states('sensor.perific_mains_fuse') | float(0))
             - (states('sensor.perific_measurement_current_l3') | float(0)) | round(1) }}
```

Useful for EV charging headroom display and automations that need to know how close each phase is to its fuse limit.

### Total Current

Sum of all three phase currents.

```yaml
template:
  - sensor:
      - name: "Total Current"
        unit_of_measurement: "A"
        device_class: current
        state_class: measurement
        state: >
          {{ (states('sensor.perific_measurement_current_l1') | float(0))
             + (states('sensor.perific_measurement_current_l2') | float(0))
             + (states('sensor.perific_measurement_current_l3') | float(0)) | round(1) }}
```

### Phase Override Active

`true` when Perific is actively overriding at least one phase (any `PhaseCurrentOverride[n] != -1`).

Requires Phase 2 `phase_override_l1/l2/l3` sensors to be implemented first.

```yaml
template:
  - binary_sensor:
      - name: "Perific Phase Override Active"
        state: >
          {{ states('sensor.perific_phase_override_l1') not in ['unknown', 'unavailable', 'none']
             or states('sensor.perific_phase_override_l2') not in ['unknown', 'unavailable', 'none']
             or states('sensor.perific_phase_override_l3') not in ['unknown', 'unavailable', 'none'] }}
```

---

## Phase 4 — Energy Dashboard Integration

### Per-phase energy sensors (requires Phase 1)

Once Phase 1 per-phase energy sensors (`energy_import_l1/l2/l3`) are live with `state_class: total_increasing`, each can be added to the HA Energy Dashboard individually as a grid consumption source. This allows phase-level cost attribution for households with single-phase or mixed loads.

### Utility meter — hourly / daily / monthly

Full configuration for all three cycle types based on the existing total energy sensor:

```yaml
utility_meter:
  perific_energy_import_hour:
    source: sensor.perific_measurement_energy_import
    cycle: hourly

  perific_energy_import_day:
    source: sensor.perific_measurement_energy_import
    cycle: daily

  perific_energy_import_month:
    source: sensor.perific_measurement_energy_import
    cycle: monthly
```

These produce sensors equivalent to Tibber's `accumulated_consumption_current_hour` / day / month without requiring a Tibber subscription. Per-phase equivalents can be added by repeating the block with `energy_import_l1/l2/l3` as the source.

### Powercalc

The [Powercalc](https://github.com/bramstroker/homeassistant-powercalc) integration can wrap `sensor.perific_measurement_power_import` as a real power source to auto-generate energy tracking without manually configuring `utility_meter`:

```yaml
powercalc:
  sensors:
    - entity_id: sensor.perific_measurement_power_import
      name: Perific House Power
      mode: real_power
      real_power_entity_id: sensor.perific_measurement_power_import
```

This produces `sensor.perific_house_power_energy` automatically, which can be added to the Energy Dashboard. Note that Powercalc uses its own integration method internally; for most uses `utility_meter` is simpler and sufficient.

---

## Implementation Order (Recommended)

1. **Phase 1** — Lowest effort. `imin` and `imax` are already in `ItemPacketData`; per-phase energy reuses `_Q_TO_KWH`. Only `sensor.py` changes. Adds 9 sensors with zero model or coordinator changes.

2. **Phase 3** — Zero integration changes. Add template and binary_sensor blocks to `configuration.yaml` immediately; no restart of the integration required.

3. **Phase 2** — Additive reporter sensors. Most require only new entries in `REPORTER_SENSOR_TYPES`. The `PhaseCurrentOverride` sensors need a small helper function. `solar_enabled` requires a new `binary_sensor.py` platform file. `algorithm_type` requires one line in `client.py`. Tackle in sub-steps: fuse + delay first, then solar sensors, then `algorithm_type`.

4. **Phase 4** — Builds on Phase 1 (per-phase energy sensors must be live before adding them to the Energy Dashboard). The `utility_meter` YAML can be added at any time; Powercalc is optional.

---

## Open Questions

The following require live API verification before implementing Phase 2 fully:

- **Does `imin`/`imax` actually appear in the `PhaseRealTime` response for this hardware?** The Pydantic model accepts them (`Optional`, default `None`) so the integration won't break if they're absent, but the sensors will remain `unknown` until confirmed present in a real packet.

- **Does `SolarSettings` ever become non-null in `SimpleSettings`?** The user's live session showed `SolarSettings: null` in SimpleSettings and a populated object in UserSettings. It is unclear whether SimpleSettings.SolarSettings ever carries useful data or is always null.

- **Is `PowerTariff` ever populated — and if so, what is its structure?** The live session showed `PowerTariff: null`. If it carries tariff schedule or price data it may be worth exposing, but the structure is unknown without a live sample.

- **Are there other endpoints beyond `getlatestpackets`, `getreporterssettingsforuser`, and `getaccountoverview`?** The Enegic API is not publicly documented. There may be historical data, event log, or firmware endpoints not yet discovered.
