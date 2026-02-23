Model Attributes Overview
=========================

BuEM building model attributes define the physical and operational characteristics of buildings for energy analysis.

Attribute Categories
-------------------

**Building Geometry**
  - Floor area, building height, number of storeys
  - Orientation and window-to-wall ratios
  - Building footprint and shape factors

**Thermal Properties**
  - Wall, roof, and floor insulation values
  - Window specifications and thermal bridging
  - Air tightness and ventilation characteristics

**Occupancy Patterns**
  - Occupant density and schedules
  - Internal heat gains from people, equipment, lighting
  - Domestic hot water usage patterns

**Climate Data**
  - Geographic coordinates for weather data
  - Site-specific conditions and microclimate
  - Seasonal variation adjustments

Attribute Validation
-------------------

All building attributes undergo validation:

- **Type Checking**: Ensure correct data types (numbers, strings, booleans)
- **Range Validation**: Check values are within physical/realistic limits
- **Dependency Checks**: Validate relationships between related attributes
- **Completeness**: Verify all required attributes are provided

For detailed attribute specifications, see the following sections:

- :doc:`building_properties` - Physical building characteristics
- :doc:`thermal_properties` - Thermal performance specifications  
- :doc:`occupancy_profiles` - Occupancy and usage patterns
- :doc:`weather_data` - Climate and weather data requirements
- :doc:`validation_rules` - Validation rules and error handling