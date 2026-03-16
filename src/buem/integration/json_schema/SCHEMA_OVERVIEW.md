# BUEM API Schema Overview — v3

Visual reference for the v3 request and response schemas.

**Legend**
- `*` = required field
- `-` = optional field
- `{ v, u }` = measurement quantity: `{ "value": number, "unit": string }`

---

## Request Schema

```mermaid
flowchart TD
    classDef obj  fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a,font-weight:bold
    classDef leaf fill:#f8fafc,stroke:#94a3b8,color:#1e293b
    classDef sep  fill:#f0fdf4,stroke:#22c55e,color:#14532d,font-weight:bold
    classDef meas fill:#fef9c3,stroke:#f59e0b,color:#78350f

    FC["FeatureCollection
    ───────────────
    * type: FeatureCollection
    * features[ ]
    - timeStamp"]:::obj

    FEAT["Feature
    ───────────────
    * type: Feature
    * id
    * geometry
    * properties"]:::obj

    GEO["geometry
    ───────────────
    * type: Point
    * coordinates [lon, lat, elev?]
    -- authoritative location --
    used for weather station lookup"]:::leaf

    PROPS["properties
    ───────────────
    * start_time
    * end_time
    - resolution (default: 60)
    - resolution_unit (default: minutes)
    * buem"]:::obj

    BUEM["buem
    ───────────────
    * building
    * envelope
    - thermal
    - solver"]:::obj

    BUILD["building
    ───────────────
    - A_ref { v, unit: m2 }
    - h_room { v, unit: m }
    - n_storeys
    - building_type
    - construction_period
    - country (ISO 3166-1)
    - attic_condition
    - cellar_condition
    - neighbour_status"]:::sep

    ENV["envelope
    ───────────────
    * elements[ ]"]:::sep

    EL["envelope_element
    ───────────────
    * id  (user-defined)
    * type  wall / roof / floor /
            window / door / ventilation
    * area { v, unit: m2 }  [not ventilation]
    * azimuth { v, unit: deg }  [not ventilation]
    * tilt { v, unit: deg }  [not ventilation]
    - surface  (parent wall id)"]:::leaf

    THERM["thermal
    ───────────────
    - n_air_infiltration { v, unit: 1/h }
    - n_air_use { v, unit: 1/h }
    - c_m { v, unit: kJ/(m2K) }
    - thermal_class  light/medium/heavy
    - comfortT_lb { v, unit: degC }
    - comfortT_ub { v, unit: degC }
    - design_T_min { v, unit: degC }
    - F_sh_hor { v, unit: - }
    - F_sh_vert { v, unit: - }
    - F_f { v, unit: - }
    - F_w { v, unit: - }
    - element_properties[ ]"]:::sep

    TEL["thermal_element
    ───────────────
    * id  (ref to envelope element)
    - U { v, unit: W/(m2K) }
    - b_transmission { v, unit: - }
    - g_gl { v, unit: - }  (windows)
    - air_changes { v, unit: 1/h }  (ventilation)"]:::leaf

    SOLV["solver
    ───────────────
    - use_milp  (default: false)
    - parallel_thermal  (default: true)
    - use_chunked_processing  (default: true)"]:::sep

    FC --> FEAT
    FEAT --> GEO
    FEAT --> PROPS
    PROPS --> BUEM
    BUEM --> BUILD
    BUEM --> ENV
    BUEM --> THERM
    BUEM --> SOLV
    ENV --> EL
    THERM --> TEL
```

> `geometry.coordinates` is the single source of truth for location — used for weather station lookup. Latitude and longitude are not duplicated inside `buem`.

---

## Envelope / Thermal Split

Geometry and thermal performance are separated and linked by element `id`. Any number of elements per type is allowed.

```mermaid
flowchart LR
    classDef geo fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a
    classDef thm fill:#fef9c3,stroke:#f59e0b,color:#78350f

    subgraph env["envelope.elements"]
        E1["id: Wall_3
        type: wall
        area: { value: 30.0, unit: m2 }
        azimuth: { value: 180.0, unit: deg }
        tilt: { value: 90.0, unit: deg }"]:::geo

        E2["id: Win_2
        type: window
        area: { value: 8.0, unit: m2 }
        azimuth: { value: 180.0, unit: deg }
        tilt: { value: 90.0, unit: deg }
        surface: Wall_3"]:::geo
    end

    subgraph thm["thermal.element_properties"]
        T1["id: Wall_3
        U: { value: 1.6, unit: W/(m2K) }
        b_transmission: { value: 1.0, unit: - }"]:::thm

        T2["id: Win_2
        U: { value: 2.8, unit: W/(m2K) }
        g_gl: { value: 0.6, unit: - }"]:::thm
    end

    E1 -. "same id" .-> T1
    E2 -. "same id" .-> T2
```

---

## Response Schema

The response echoes all four `buem` request nodes and appends `thermal_load_profile` and `model_metadata`.

```mermaid
flowchart TD
    classDef obj   fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a,font-weight:bold
    classDef added fill:#dcfce7,stroke:#22c55e,color:#14532d,font-weight:bold
    classDef leaf  fill:#f8fafc,stroke:#94a3b8,color:#1e293b
    classDef opt   fill:#f1f5f9,stroke:#94a3b8,color:#475569

    FC["FeatureCollection
    ───────────────
    * type
    * features[ ]
    - timeStamp
    + processed_at
    + processing_elapsed_s
    + * metadata"]:::obj

    META["* metadata
    ───────────────
    * total_features
    * successful_features
    * failed_features
    - validation_warnings"]:::leaf

    BUEM["buem
    ───────────────
    * building  (echoed)
    * envelope  (echoed)
    - thermal   (echoed)
    - solver    (echoed)
    + * thermal_load_profile
    + - model_metadata"]:::added

    TLP["thermal_load_profile
    ───────────────
    * start_time
    * end_time
    * resolution
    * resolution_unit
    * summary
    - timeseries
    - timeseries_file"]:::obj

    SUM["summary
    ───────────────
    * heating
    * cooling
    * electricity
    - total_energy_demand { v, unit: kWh }
    - peak_heating_load { v, unit: kW }
    - peak_cooling_load { v, unit: kW }
    - energy_intensity { v, unit: kWh/m2 }"]:::obj

    ES["energy_summary
    (heating / cooling / electricity)
    ───────────────
    * total { v, unit: kWh }
    * max { v, unit: kW }
    * min { v, unit: kW }
    * mean { v, unit: kW }
    - median { v, unit: kW }
    - std { v, unit: kW }"]:::leaf

    TS["timeseries
    (only if ?include_timeseries=true)
    ───────────────
    * unit  kW / W / MW
    * timestamps[ ]
    * heating[ ]
    * cooling[ ]
    * electricity[ ]"]:::opt

    MM["model_metadata
    ───────────────
    - model_version
    - solver_used
    - processing_time { v, unit: s }
    - weather_year
    - parallel_thermal
    - use_chunked_processing
    - validation_warnings[ ]"]:::leaf

    FC --> META
    FC --> BUEM
    BUEM --> TLP
    BUEM --> MM
    TLP --> SUM
    TLP --> TS
    SUM --> ES
```

---

## Measurement Type Library

All measurable quantities use `{ "value": number, "unit": string }`. The `unit` field defaults to SI when omitted.

### Request quantities

| $defs key | Allowed units | SI default |
|---|---|---|
| `area_qty` | `m2`, `ft2` | `m2` |
| `length_qty` | `m`, `ft` | `m` |
| `angle_qty` | `deg`, `rad` | `deg` |
| `u_value_qty` | `W/(m2K)`, `BTU/(h.ft2.F)` | `W/(m2K)` |
| `air_change_qty` | `1/h` | `1/h` |
| `heat_capacity_qty` | `kJ/(m2K)`, `BTU/(ft2.F)` | `kJ/(m2K)` |
| `temperature_qty` | `degC`, `degF` | `degC` |
| `dimensionless_qty` | `-` | `-` |

### Response quantities

| $defs key | Allowed units | Default |
|---|---|---|
| `energy_qty` | `kWh`, `MWh`, `Wh` | `kWh` |
| `power_qty` | `kW`, `W`, `MW` | `kW` |
| `energy_intensity_qty` | `kWh/m2`, `kWh/ft2` | `kWh/m2` |
| `duration_qty` | `s`, `ms`, `min` | `s` |

---

## TABULA Parameter Alignment

Fields in `thermal` map directly to IEE TABULA database parameters:

| v3 schema field | TABULA field | Unit | Default |
|---|---|---|---|
| `n_air_infiltration` | `n_air_infiltration` | 1/h | 0.5 |
| `n_air_use` | `n_air_use` | 1/h | 0.5 |
| `c_m` | `c_m` | kJ/(m2K) | 165.0 |
| `design_T_min` | `Theta_e` | degC | -12.0 |
| `F_sh_hor` | `F_sh_hor` | - | 0.80 |
| `F_sh_vert` | `F_sh_vert` | - | 0.75 |
| `F_f` | `F_f` | - | 0.20 |
| `F_w` | `F_w` | - | 1.00 |
| `g_gl` (per element) | `g_gl_n_Window_1/2` | - | 0.50 |
| `b_transmission` (per element) | `b_Transmission_*` | - | 1.00 |
