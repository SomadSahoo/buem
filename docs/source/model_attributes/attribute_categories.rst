Attribute Categories
====================

BuEM organizes building attributes into distinct categories based on their source, behavior, and usage patterns. Understanding these categories helps in proper integration and data management.

Category Definitions
--------------------

WEATHER
~~~~~~~

Attributes related to meteorological data and geographic location.

- **Purpose**: Define climate conditions for thermal calculations
- **Data Sources**: Weather files, location coordinates
- **Update Frequency**: Typically static for a simulation year
- **Examples**: temperature profiles, solar irradiance, latitude/longitude

.. list-table:: Weather Attributes
   :header-rows: 1
   :widths: 25 15 60

   * - Attribute
     - Type
     - Description
   * - ``weather``
     - DATAFRAME
     - Complete weather dataset with T, GHI, DNI, DHI columns
   * - ``latitude``
     - FLOAT
     - Geographic latitude (-90 to 90 degrees)
   * - ``longitude``
     - FLOAT
     - Geographic longitude (-180 to 180 degrees)

FIXED
~~~~~

Static building properties that define physical characteristics.

- **Purpose**: Define building geometry, materials, and system properties
- **Data Sources**: Building databases, architectural drawings, measured data
- **Update Frequency**: Rarely changes for existing buildings
- **Examples**: areas, U-values, room height, reference area

.. list-table:: Key Fixed Attributes
   :header-rows: 1  
   :widths: 25 15 60

   * - Attribute
     - Type
     - Description
   * - ``A_ref``
     - FLOAT
     - Reference floor area (m²)
   * - ``h_room``
     - FLOAT
     - Average room height (m)
   * - ``design_T_min``
     - FLOAT
     - Design minimum temperature (°C)
   * - ``comfortT_lb``
     - FLOAT
     - Comfort temperature lower bound (°C)
   * - ``comfortT_ub``
     - FLOAT
     - Comfort temperature upper bound (°C)
   * - ``thermalClass``
     - STR
     - Thermal mass class (light/medium/heavy)

BOOLEAN
~~~~~~~

Configuration flags that enable/disable specific model features.

- **Purpose**: Control model behavior and calculation methods
- **Data Sources**: User preferences, building control systems
- **Update Frequency**: Can vary by simulation scenario
- **Examples**: control strategies, refurbishment options

.. list-table:: Boolean Attributes
   :header-rows: 1
   :widths: 25 15 60

   * - Attribute
     - Type
     - Description
   * - ``refurbishment``
     - BOOL
     - Enable refurbishment calculations (deprecated)
   * - ``force_refurbishment``
     - BOOL
     - Force refurbishment decisions (deprecated)
   * - ``occControl``
     - BOOL
     - Enable occupancy-based control (deprecated)
   * - ``nightReduction``
     - BOOL
     - Enable night temperature reduction (deprecated)
   * - ``capControl``
     - BOOL
     - Enable capacity control (deprecated)
   * - ``ventControl``
     - BOOL
     - Enable ventilation control
   * - ``control``
     - BOOL
     - Master control flag for smart strategies
   * - ``onlyEnergyInvest``
     - BOOL
     - Focus on energy investments only
   * - ``use_provided_elecLoad``
     - BOOL
     - Use provided electricity profile vs. generated

OTHER
~~~~~

Complex structured data that doesn't fit standard categories.

- **Purpose**: Define building components and complex relationships
- **Data Sources**: Detailed building specifications, component libraries
- **Update Frequency**: Varies by data type and use case
- **Examples**: component hierarchies, roof configurations

.. list-table:: Other Attributes
   :header-rows: 1
   :widths: 25 15 60

   * - Attribute
     - Type
     - Description
   * - ``components``
     - OBJECT
     - Hierarchical building envelope definition
   * - ``roofs``
     - LIST
     - Array of roof configurations for solar analysis

Time Series Attributes
----------------------

Several attributes contain time series data aligned with the weather data index:

**Electricity Profiles**

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Attribute
     - Type
     - Description
   * - ``elecLoad``
     - SERIES
     - Hourly electricity consumption profile (kW)
   * - ``Q_ig``
     - SERIES
     - Internal heat gains profile (kW)

**Occupancy Profiles** 

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Attribute
     - Type
     - Description
   * - ``occ_nothome``
     - SERIES
     - Away from home occupancy (0-1, 0=home, 1=away)
   * - ``occ_sleeping``
     - SERIES
     - Sleeping occupancy (0-1, 0=awake, 1=sleeping)

Profile Generation Parameters
-----------------------------

Attributes that control automatic profile generation:

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Attribute
     - Type
     - Description
   * - ``num_persons``
     - INT
     - Number of occupants for electricity profile generation
   * - ``year``
     - INT
     - Year for profile generation (affects holiday patterns)
   * - ``seed``
     - INT
     - Random seed for reproducible profile generation

Category Usage in API Integration
---------------------------------

**Request Payload Strategy**

When building API requests, consider which categories to include:

.. code-block:: json

    {
      "building_attributes": {
        // WEATHER category - location specific
        "latitude": 52.0,
        "longitude": 5.0,
        
        // FIXED category - building specific  
        "A_ref": 2064,
        "h_room": 2.5,
        
        // BOOLEAN category - scenario specific
        "use_provided_elecLoad": false,
        "control": true,
        
        // OTHER category - detailed specification
        "components": {
          "Walls": {...},
          "Roof": {...}
        }
      }
    }

**Default Behavior**

- WEATHER: Uses built-in weather data if not specified
- FIXED: Uses typical multi-family house defaults
- BOOLEAN: Conservative defaults (most features disabled)
- OTHER: Minimal viable building component structure

**Priority Handling**

The system resolves attributes with this priority:
1. API payload values (if provided)
2. Database values (if building_id lookup succeeds)
3. Category defaults (always available)

Validation by Category
----------------------

Each category has specific validation rules:

**WEATHER**
- Coordinates must be within valid geographic ranges
- Weather data must have required columns (T, GHI, DNI, DHI)
- Time index must be complete with no gaps

**FIXED**
- All geometric values must be positive
- Temperature ranges must be physically reasonable
- Areas and volumes must be consistent

**BOOLEAN** 
- Simple true/false validation
- No cross-dependencies currently enforced

**OTHER**
- Complex structural validation
- Component relationships must be valid
- Element references must exist

Next Steps
----------

Continue to :doc:`building_properties` for detailed specifications of building geometry and physical properties.