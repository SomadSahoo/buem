Component Definitions
====================

The ``components`` attribute defines the building envelope structure using a hierarchical system. Each component type has shared properties and individual elements with specific geometry.

Components Overview
-------------------

The components structure organizes building envelope elements into logical groups:

.. code-block:: json

    {
      "components": {
        "Walls": {...},
        "Roof": {...}, 
        "Floor": {...},
        "Windows": {...},
        "Doors": {...},
        "Ventilation": {...}
      }
    }

Each component type follows this pattern:

- **Shared Properties**: Applied to all elements of that type (e.g., U-value)
- **Elements Array**: Individual instances with specific geometry and orientation

Component Structure
-------------------

**Generic Component Format**

.. code-block:: json

    {
      "ComponentType": {
        "U": 1.5,                    // Shared thermal property
        "other_property": "value",    // Type-specific shared properties
        "elements": [
          {
            "id": "Element_1",        // Unique identifier  
            "area": 100.0,            // Element area (m²)
            "azimuth": 180.0,         // Orientation (degrees)
            "tilt": 30.0,             // Tilt angle (degrees)
            // ... other element-specific properties
          }
        ]
      }
    }

Walls Component
---------------

Defines opaque wall surfaces of the building envelope.

**Shared Properties**

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Property
     - Type
     - Description
   * - ``U``
     - number
     - Thermal transmittance (W/m²K)
   * - ``b_transmission``
     - number
     - Transmission adjustment factor (default: 1.0)

**Element Properties**

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Property
     - Type
     - Description
   * - ``id``
     - string
     - Unique wall element identifier
   * - ``area``
     - number
     - Wall surface area (m²)
   * - ``azimuth``
     - number
     - Wall orientation (degrees, 0=North, 90=East)
   * - ``tilt``
     - number
     - Wall tilt (degrees, 0=horizontal, 90=vertical)

**Example**

.. code-block:: json

    {
      "Walls": {
        "U": 1.61,
        "b_transmission": 1.0,
        "elements": [
          {
            "id": "Wall_1", 
            "area": 1226.9, 
            "azimuth": 0.0, 
            "tilt": 0.0
          },
          {
            "id": "Wall_2", 
            "area": 2000, 
            "azimuth": 90.0, 
            "tilt": 0.0
          }
        ]
      }
    }

Roof Component
--------------

Defines roof surfaces exposed to outdoor conditions.

**Shared Properties**

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Property
     - Type
     - Description
   * - ``U``
     - number
     - Thermal transmittance (W/m²K)

**Element Properties**

Same as walls, but typically with non-zero tilt angles.

**Example**

.. code-block:: json

    {
      "Roof": {
        "U": 1.54,
        "elements": [
          {
            "id": "Roof_1",
            "area": 497.7,
            "azimuth": 135.0,
            "tilt": 30.0
          }
        ]
      }
    }

Floor Component
---------------

Defines floor surfaces in contact with ground or other thermal zones.

**Shared Properties**

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Property
     - Type
     - Description
   * - ``U``
     - number
     - Thermal transmittance (W/m²K)

**Element Properties**

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Property
     - Type
     - Description
   * - ``id``
     - string
     - Unique floor element identifier
   * - ``area``
     - number
     - Floor surface area (m²)
   * - ``azimuth``
     - number
     - Floor orientation (typically 180° for ground contact)
   * - ``tilt``
     - number
     - Floor tilt (typically 90° for ground contact)

**Example**

.. code-block:: json

    {
      "Floor": {
        "U": 1.72,
        "elements": [
          {
            "id": "Floor_1",
            "area": 469.0,
            "azimuth": 180.0,
            "tilt": 90.0
          }
        ]
      }
    }

Windows Component
-----------------

Defines transparent or translucent window openings.

**Shared Properties**

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Property
     - Type
     - Description
   * - ``U``
     - number
     - Thermal transmittance (W/m²K)
   * - ``g_gl``
     - number
     - Solar energy transmittance (0-1)

**Element Properties**

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Property
     - Type
     - Description
   * - ``id``
     - string
     - Unique window element identifier
   * - ``area``
     - number
     - Window area (m²)
   * - ``surface``
     - string
     - Parent wall element ID (optional)
   * - ``azimuth``
     - number
     - Window orientation (degrees)
   * - ``tilt``
     - number
     - Window tilt (degrees)

**Example**

.. code-block:: json

    {
      "Windows": {
        "U": 5.2,
        "g_gl": 0.5,
        "elements": [
          {
            "id": "Win_1",
            "area": 78.4,
            "surface": "Wall_1",
            "azimuth": 0.0,
            "tilt": 0.0
          },
          {
            "id": "Win_2", 
            "area": 347.2,
            "surface": "Wall_2",
            "azimuth": 90.0,
            "tilt": 0.0
          }
        ]
      }
    }

Doors Component
---------------

Defines doors and other openings in the building envelope.

**Shared Properties**

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Property
     - Type
     - Description
   * - ``U``
     - number
     - Thermal transmittance (W/m²K)

**Element Properties**

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Property
     - Type
     - Description
   * - ``id``
     - string
     - Unique door element identifier
   * - ``area``
     - number
     - Door area (m²)
   * - ``surface``
     - string
     - Parent wall element ID (optional)
   * - ``azimuth``
     - number
     - Door orientation (degrees)
   * - ``tilt``
     - number
     - Door tilt (typically 90° for vertical doors)

**Example**

.. code-block:: json

    {
      "Doors": {
        "U": 3.5,
        "elements": [
          {
            "id": "Door_1",
            "area": 58.8,
            "surface": "Wall_1", 
            "azimuth": 0.0,
            "tilt": 90.0
          }
        ]
      }
    }

Ventilation Component
---------------------

Defines air exchange rates and ventilation systems.

**Element Properties**

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Property
     - Type
     - Description
   * - ``id``
     - string
     - Unique ventilation element identifier
   * - ``air_changes``
     - number
     - Air changes per hour (1/h)

**Example**

.. code-block:: json

    {
      "Ventilation": {
        "elements": [
          {
            "id": "Vent_1",
            "air_changes": 0.5
          }
        ]
      }
    }

Element Relationships
---------------------

**Parent-Child References**

Windows and doors can reference parent wall surfaces:

.. code-block:: json

    {
      "Walls": {
        "elements": [
          {"id": "Wall_1", "area": 100.0, "...": "..."}
        ]
      },
      "Windows": {
        "elements": [
          {
            "id": "Win_1",
            "area": 10.0,
            "surface": "Wall_1",  // References Wall_1
            "...": "..."
          }
        ]
      }
    }

**Validation Rules**

- Referenced parent surfaces must exist
- Window/door areas should not exceed parent wall area
- Element IDs must be unique within each component type
- All areas must be positive numbers

Orientation Conventions
-----------------------

**Azimuth Angles**

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Direction
     - Azimuth (degrees)
   * - North
     - 0°
   * - East
     - 90°
   * - South
     - 180°
   * - West
     - 270°

**Tilt Angles**

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Orientation
     - Tilt (degrees)
   * - Horizontal
     - 0°
   * - Sloped roof
     - 30-45°
   * - Vertical wall
     - 90° (or 0° for simplified modeling)

Component Defaults
------------------

When components are not specified, minimal defaults are used:

.. code-block:: json

    {
      "components": {
        "Walls": {
          "U": 1.61,
          "elements": [
            {"id": "Wall_1", "area": 1226.9, "azimuth": 0.0, "tilt": 0.0}
          ]
        },
        "Roof": {
          "U": 1.54, 
          "elements": [
            {"id": "Roof_1", "area": 497.7, "azimuth": 135.0, "tilt": 30.0}
          ]
        },
        "Floor": {
          "U": 1.72,
          "elements": [
            {"id": "Floor_1", "area": 469.0, "azimuth": 180.0, "tilt": 90.0}
          ]
        },
        "Ventilation": {
          "elements": [
            {"id": "Vent_1", "air_changes": 0.5}
          ]
        }
      }
    }

Integration Best Practices
---------------------------

**Component Building Strategy**

1. **Start with envelope**: Define Walls, Roof, Floor first
2. **Add openings**: Windows and doors reference wall elements  
3. **Define ventilation**: Set appropriate air change rates
4. **Validate relationships**: Ensure parent references exist
5. **Check areas**: Window/door areas ≤ parent wall areas

**Common Patterns**

.. code-block:: python

    # Simple building (single zone)
    components = {
        "Walls": {"U": 1.5, "elements": [...]},
        "Roof": {"U": 1.0, "elements": [...]}, 
        "Floor": {"U": 2.0, "elements": [...]},
        "Windows": {"U": 3.0, "g_gl": 0.6, "elements": [...]},
        "Ventilation": {"elements": [{"id": "Vent_1", "air_changes": 0.5}]}
    }

Next Steps
----------

Continue to :doc:`thermal_properties` for detailed information about thermal calculations and material properties.