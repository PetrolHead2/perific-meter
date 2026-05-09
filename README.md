# Perific Meter

A Home Assistant custom integration for the Perific / Enegic load balancer. Provides real-time household current and power sensors, cumulative energy tracking, and Zaptec EV charger reporter data.

The Perific device is a current-transformer load balancer — it measures current per phase only, not voltage. Power is estimated using a fixed 230 V nominal assumption. Voltage sensors are not available.

---

## Sensors

### Meter sensors

Sourced from the `PhaseRealTime` packet. Polled every **30 seconds** per device.

Entity IDs follow the pattern `sensor.perific_{device_name}_{key}` where `{device_name}` is the name assigned to the device in the Enegic cloud (e.g. `measurement`).

| Sensor | Unit | Notes |
|---|---|---|
| Current L1 | A | Average current on phase 1 (`iavg[0]`) |
| Current L2 | A | Average current on phase 2 (`iavg[1]`) |
| Current L3 | A | Average current on phase 3 (`iavg[2]`) |
| Power Import | W | Estimated as `sum(iavg[0:3]) × 230 V` — no direct power measurement |
| Energy Import | kWh | Cumulative lifetime counter; `sum(qmax[0:3]) / 19,565,000` |

### Zaptec reporter sensors

Sourced from the account-level Zaptec reporter settings. Polled every **60 seconds**.

| Sensor | Unit | Notes |
|---|---|---|
| Perific Zaptec Allowed Current | A | 0 A means "no override" in Open mode, not zero current; live only in Smart / Price mode |
| Perific Mains Fuse | A | House fuse ceiling configured in Enegic cloud |
| Perific Safe Mode Current | A | Charger fallback current if cloud communication drops |
| Perific Charging Mode | — | `Open` / `Smart` / `Price` / `Solar` |

---

## Installation

### Via HACS (recommended)

1. In HACS → **Integrations** → ⋮ → **Custom repositories**
2. Add `https://github.com/PetrolHead2/perific-meter`, category **Integration**
3. Install **Perific Meter**
4. Restart Home Assistant

### Manual

1. Copy `custom_components/perific_meter/` into your HA `config/custom_components/` directory
2. Restart Home Assistant

---

## Configuration

After restarting, add the integration via:

**Settings → Devices & Services → Add Integration → search "Perific"**

Required credentials:

| Field | Description |
|---|---|
| Username | Your Enegic / Perific account email |
| Password | Your Enegic / Perific account password |

The integration authenticates against `api.enegic.com` and re-authenticates automatically on token expiry (401 response).

---

## Energy Dashboard

`sensor.perific_measurement_energy_import` (or whichever name your device produces) is compatible with the Home Assistant **Energy Dashboard** as a grid consumption source (`device_class: energy`, `state_class: total_increasing`).

To produce an hourly-resetting consumption counter equivalent to Tibber's `accumulated_consumption_current_hour`, add to `configuration.yaml`:

```yaml
utility_meter:
  perific_energy_import_hour:
    source: sensor.perific_measurement_energy_import
    cycle: hourly
```

Adjust the source entity ID to match your actual device name.

---

## Known Limitations

- **Estimated power.** Power is calculated as `iavg × 230 V nominal`. Accuracy depends on actual grid voltage staying close to 230 V; no direct power measurement is available.
- **30-second poll lag.** Readings are stale during fast-changing events (e.g. EV charging ramp-up). This is acceptable for smoothed or averaged inputs but not for near-real-time control.
- **Lifetime cumulative counter.** `Energy Import` is a monotonically increasing lifetime counter — do not reset it. Use a `utility_meter` helper for period-based tracking.
- **Allowed Current = 0 A in Open mode** is correct behaviour (sentinel value, not a measurement). It becomes a live reading only in Smart or Price mode.
- **Cloud dependency.** The API (`api.enegic.com`) requires an active Perific cloud account. Local-only operation is not supported.

---

## API

The integration calls the following endpoints on `https://api.enegic.com`:

| Method | Endpoint | Purpose | Interval |
|---|---|---|---|
| `PUT` | `/createtoken` | Authenticate; returns bearer token | On setup / token expiry |
| `GET` | `/getaccountoverview` | List all items (meters, chargers) | On setup |
| `PUT` | `/getlatestpackets` | Fetch current/energy packet data | Every 30 s |
| `GET` | `/getreporterssettingsforuser` | Fetch Zaptec reporter settings | Every 60 s |

Authentication uses a bearer token passed as `X-Authorization` header. Tokens are valid for approximately one year. On a `401` response the hub re-authenticates automatically using the stored credentials.

---

## Requirements

- `aiohttp >= 3.11.0`
- `pydantic >= 2.10.0`

---

## License

MIT
