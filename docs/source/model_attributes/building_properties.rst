Building Properties
==================

Physical building characteristics and geometric properties.

Required Properties
------------------

**Coordinates**

.. code-block:: json

    {
        "coordinates": {
            "latitude": 46.5197,
            "longitude": 6.566
        }
    }

- **latitude**: Geographic latitude (-90 to 90 degrees)
- **longitude**: Geographic longitude (-180 to 180 degrees)

**Building Type**

.. code-block:: json

    {
        "building_type": "residential"
    }

- **Options**: "residential", "commercial", "industrial", "mixed_use"
- **Impact**: Affects default occupancy schedules and equipment loads

**Floor Area**

.. code-block:: json

    {
        "floor_area": 120.5
    }

- **Unit**: Square meters (m²)
- **Range**: 10 to 100,000 m²
- **Description**: Total conditioned floor area

Optional Properties
------------------

**Building Geometry**

.. code-block:: json

    {
        "building_height": 8.5,
        "storeys": 3,
        "window_to_wall_ratio": 0.25,
        "orientation": 180
    }

- **building_height**: Total building height in meters
- **storeys**: Number of floors
- **window_to_wall_ratio**: Fraction of wall area that is windows (0-1)
- **orientation**: Building orientation in degrees (0=North, 90=East)

**Shape Factors**

.. code-block:: json

    {
        "shape_factor": 0.75,
        "wall_area": 240.0,
        "roof_area": 120.0,
        "window_area": 30.0
    }

- **shape_factor**: Building compactness ratio
- **wall_area**: Total exterior wall area in m²
- **roof_area**: Roof surface area in m²
- **window_area**: Total window area in m²

Default Values
--------------

When optional properties are not specified, BuEM applies defaults based on building type:

**Residential Buildings**

.. code-block:: python

    defaults = {
        "storeys": 2,
        "building_height": 6.0,  # 3m per storey
        "window_to_wall_ratio": 0.15,
        "orientation": 180,  # South-facing
        "shape_factor": 0.8
    }

**Commercial Buildings**

.. code-block:: python

    defaults = {
        "storeys": 3,
        "building_height": 12.0,  # 4m per storey
        "window_to_wall_ratio": 0.4,
        "orientation": 180,
        "shape_factor": 0.6
    }

Calculated Properties
--------------------

Some properties are automatically calculated from provided values:

**Wall Area Calculation**

.. code-block:: python

    # If not provided, calculated from floor area and geometry
    perimeter = 4 * sqrt(floor_area)  # Assumes square building
    wall_area = perimeter * building_height - window_area

**Roof Area Calculation**

.. code-block:: python

    # For flat roofs
    roof_area = floor_area
    
    # For sloped roofs (if roof_type specified)
    roof_area = floor_area * roof_slope_factor

Validation Rules
---------------

**Consistency Checks**

- Window area cannot exceed total wall area
- Building height must be consistent with number of storeys
- Shape factor must be between 0.1 and 1.0

**Physical Constraints**

- Floor area per storey should be reasonable (10-10,000 m²)
- Window-to-wall ratio cannot exceed 0.9
- Building height limited to 300m (practical construction limit)

For thermal property specifications, see :doc:`thermal_properties`.