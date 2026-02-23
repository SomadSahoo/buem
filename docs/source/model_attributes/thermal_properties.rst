Thermal Properties
==================

Building envelope thermal characteristics for heat transfer calculations.

U-Values (Thermal Transmittance)
-------------------------------

U-values specify heat transfer coefficients for building elements.

**Wall Thermal Properties**

.. code-block:: json

    {
        "u_value_wall": 0.25,
        "wall_construction": "insulated_cavity"
    }

- **u_value_wall**: W/(m²·K) - Heat transfer coefficient through walls
- **Range**: 0.1 to 2.0 W/(m²·K)
- **Typical values**: 0.15-0.3 (new), 0.5-1.5 (existing)

**Roof Thermal Properties**

.. code-block:: json

    {
        "u_value_roof": 0.18,
        "roof_construction": "insulated_flat"
    }

- **u_value_roof**: W/(m²·K) - Heat transfer through roof
- **Range**: 0.1 to 2.0 W/(m²·K)
- **Typical values**: 0.12-0.25 (new), 0.4-1.2 (existing)

**Floor Thermal Properties**

.. code-block:: json

    {
        "u_value_floor": 0.22,
        "floor_type": "ground_floor"
    }

- **u_value_floor**: W/(m²·K) - Heat transfer through floor
- **Options**: "ground_floor", "suspended", "basement"

**Window Thermal Properties**

.. code-block:: json

    {
        "u_value_window": 1.1,
        "window_type": "double_glazed",
        "solar_heat_gain_coefficient": 0.5
    }

- **u_value_window**: W/(m²·K) - Heat transfer through windows
- **Range**: 0.7 to 6.0 W/(m²·K)
- **solar_heat_gain_coefficient**: Fraction of solar radiation transmitted (0-1)

Thermal Mass
-----------

**Building Thermal Mass Properties**

.. code-block:: json

    {
        "thermal_mass": "medium",
        "thermal_capacity": 250000,
        "thermal_time_constant": 72
    }

- **thermal_mass**: "light", "medium", "heavy"
- **thermal_capacity**: J/(K) - Building heat capacity
- **thermal_time_constant**: Hours - Thermal response time

**Material Types and Thermal Mass**

.. list-table::
   :header-rows: 1

   * - Construction Type
     - Thermal Mass
     - Typical Capacity (J/K per m²)
     - Time Constant (hours)
   * - Timber frame
     - Light
     - 100,000 - 150,000
     - 24 - 48
   * - Masonry cavity
     - Medium
     - 200,000 - 300,000
     - 48 - 96
   * - Concrete/Masonry
     - Heavy
     - 350,000 - 500,000
     - 96 - 168

Air Tightness and Ventilation
-----------------------------

**Air Change Rates**

.. code-block:: json

    {
        "air_change_rate": 0.5,
        "mechanical_ventilation": true,
        "heat_recovery_efficiency": 0.8
    }

- **air_change_rate**: h⁻¹ - Air changes per hour
- **mechanical_ventilation**: Boolean - Presence of mechanical ventilation
- **heat_recovery_efficiency**: 0-1 - Heat recovery effectiveness

**Infiltration Characteristics**

.. code-block:: json

    {
        "infiltration_rate": 0.3,
        "air_permeability": 5.0,
        "envelope_tightness": "average"
    }

- **infiltration_rate**: h⁻¹ - Uncontrolled air leakage
- **air_permeability**: m³/(h·m²) at 50 Pa
- **envelope_tightness**: "tight", "average", "leaky"

Thermal Bridging
---------------

**Linear Thermal Bridges**

.. code-block:: json

    {
        "thermal_bridge_factor": 0.05,
        "thermal_bridges": {
            "balconies": 0.8,
            "structural_elements": 0.6,
            "window_frames": 0.4
        }
    }

- **thermal_bridge_factor**: Additional heat loss factor
- **Individual bridge values**: W/(m·K) - Linear thermal transmittance

Construction Standards
---------------------

**Pre-defined Construction Types**

BuEM includes standard construction types with typical thermal properties:

.. code-block:: json

    {
        "construction_standard": "passive_house",
        "construction_year": 2020
    }

**Available Standards:**

- **passive_house**: U-wall≤0.15, U-roof≤0.15, U-window≤0.8
- **minergie**: Swiss energy standard
- **code_compliance**: Local building code minimum
- **retrofit**: Improved existing building
- **heritage**: Historic building constraints

**Year-Based Defaults**

When construction year is provided, typical thermal properties are applied:

.. list-table::
   :header-rows: 1

   * - Construction Period
     - U-Wall (W/m²K)
     - U-Roof (W/m²K)
     - U-Window (W/m²K)
     - Air Changes (h⁻¹)
   * - Before 1970
     - 1.4
     - 1.2
     - 5.5
     - 1.5
   * - 1970-1990
     - 0.8
     - 0.6
     - 3.0
     - 1.0
   * - 1990-2010
     - 0.4
     - 0.3
     - 1.8
     - 0.7
   * - After 2010
     - 0.25
     - 0.18
     - 1.1
     - 0.5

Validation and Constraints
-------------------------

**Physical Limits**

- U-values must be positive and realistic
- Thermal capacity must match building mass
- Air change rates within feasible ranges

**Consistency Checks**

- Thermal mass must align with construction type
- Heat recovery only applicable with mechanical ventilation
- Thermal bridges should reflect construction details

For occupancy-related thermal loads, see :doc:`occupancy_profiles`.