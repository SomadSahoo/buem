Model Attributes Reference
===========================

This section provides comprehensive documentation of all building attributes used by BuEM (Building Energy Model). These attributes control the thermal behavior and energy calculations for buildings.

.. toctree::
   :maxdepth: 2

   overview
   attribute_categories
   building_properties
   component_definitions
   thermal_properties
   occupancy_profiles
   weather_data
   validation_rules

Overview
--------

BuEM uses a structured attribute system to define building characteristics. Attributes are organized into categories based on their source and behavior:

- **Weather**: Meteorological data and location
- **Fixed**: Building geometry and physical properties
- **Boolean**: Configuration flags and control options
- **Other**: Complex structured data (components, profiles)

The attribute system supports:
- Default values for all parameters
- Flexible component-based building envelope definition
- Automatic profile generation based on occupancy patterns
- Comprehensive validation and error checking

Attribute Sources
-----------------

Building attributes can come from multiple sources with the following precedence:

1. **API Payload** (highest priority): Values provided in GeoJSON request
2. **Database**: Retrieved based on building_id (if available)
3. **Defaults** (lowest priority): Built-in defaults from configuration

This layered approach allows for:
- Consistent baseline behavior with defaults
- Building-specific customization via database
- Request-specific overrides via API payload

Data Types and Validation
-------------------------

Each attribute has a defined data type and validation rules:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Type
     - Description
   * - ``FLOAT``
     - Numeric values with decimal precision
   * - ``INT``
     - Integer values only
   * - ``BOOL``
     - True/false flags
   * - ``STR``
     - Text strings
   * - ``SERIES``
     - Time series data (pandas Series)
   * - ``DATAFRAME``
     - Structured tabular data (pandas DataFrame)
   * - ``OBJECT``
     - Complex nested structures (e.g., components)
   * - ``LIST``
     - Arrays of values

Integration Notes
-----------------

For API integration, key considerations include:

**Component Structure**: The ``components`` attribute uses a hierarchical structure where each component type (Walls, Roof, etc.) has shared properties (like U-value) and individual elements with geometry.

**Time Series Alignment**: All time-based profiles (electricity, occupancy, weather) are automatically aligned to the same time index for consistent simulation.

**Profile Generation**: Electricity consumption profiles are automatically generated based on occupancy patterns unless explicitly provided.

**Validation**: All attributes undergo validation before model execution to ensure physical reasonableness and mathematical consistency.