Examples and Use Cases
======================

This section provides practical examples of using BuEM API for building energy analysis and integration scenarios.

.. toctree::
   :maxdepth: 2

   basic_api_usage
   batch_processing
   integration_patterns
   error_handling_examples
   performance_optimization

Quick Start Example
-------------------

**Simple Building Analysis**

.. code-block:: python

    import requests
    import json

    # Define a simple building
    building_data = {
        "type": "Feature",
        "id": "example_building",
        "geometry": {"type": "Point", "coordinates": [5.0, 52.0]},
        "properties": {
            "buem": {
                "building_attributes": {
                    "latitude": 52.0,
                    "longitude": 5.0,
                    "A_ref": 100.0,
                    "components": {
                        "Walls": {
                            "U": 1.5,
                            "elements": [{"id": "Wall_1", "area": 80.0, "azimuth": 180.0, "tilt": 90.0}]
                        },
                        "Roof": {
                            "U": 1.0, 
                            "elements": [{"id": "Roof_1", "area": 100.0, "azimuth": 180.0, "tilt": 30.0}]
                        },
                        "Ventilation": {
                            "elements": [{"id": "Vent_1", "air_changes": 0.5}]
                        }
                    }
                }
            }
        }
    }

    # Submit to BuEM API
    response = requests.post(
        "http://localhost:5000/api/geojson",
        json={"type": "FeatureCollection", "features": [building_data]}
    )

    # Extract results
    if response.status_code == 200:
        results = response.json()
        thermal_profile = results["features"][0]["properties"]["buem"]["thermal_load_profile"]
        
        print(f"Annual heating demand: {thermal_profile['heating_total_kWh']:.1f} kWh")
        print(f"Annual cooling demand: {thermal_profile['cooling_total_kWh']:.1f} kWh")
        print(f"Peak heating load: {thermal_profile['heating_peak_kW']:.1f} kW")
    else:
        print(f"Error: {response.status_code} - {response.text}")

Common Integration Patterns
---------------------------

**Pattern 1: Single Building Analysis**
- Submit individual building data
- Immediate response with thermal loads
- Suitable for interactive applications

**Pattern 2: Batch Processing**
- Submit multiple buildings in FeatureCollection
- Process entire neighborhoods or districts
- Optimized for bulk analysis

**Pattern 3: Timeseries Analysis** 
- Request detailed hourly data
- Download compressed timeseries files
- Suitable for detailed energy system modeling

**Pattern 4: Parameter Studies**
- Vary building attributes systematically
- Compare different design scenarios
- Support retrofit and optimization studies

Example Scenarios
-----------------

**Scenario 1: Building Certification**
Calculate energy performance for building energy labels and certifications.

**Scenario 2: District Energy Planning**
Analyze multiple buildings to size district heating/cooling systems.

**Scenario 3: Retrofit Analysis**
Compare energy performance before and after building improvements.

**Scenario 4: Urban Energy Mapping**
Generate city-wide energy demand maps for infrastructure planning.

Next Steps
----------

Explore specific examples:
- :doc:`basic_api_usage` for step-by-step API usage
- :doc:`batch_processing` for handling multiple buildings
- :doc:`integration_patterns` for system integration approaches