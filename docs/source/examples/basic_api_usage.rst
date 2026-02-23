Basic API Usage
===============

This section demonstrates fundamental BuEM API usage patterns for single building analysis.

Quick Example
-------------

.. code-block:: python

    import requests
    
    # Simple building request
    building_data = {
        "type": "FeatureCollection",
        "features": [{
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
                            "Walls": {"U": 1.5, "elements": [{"id": "Wall_1", "area": 80.0, "azimuth": 180.0, "tilt": 90.0}]},
                            "Ventilation": {"elements": [{"id": "Vent_1", "air_changes": 0.5}]}
                        }
                    }
                }
            }
        }]
    }
    
    # Submit to BuEM API
    response = requests.post(
        "http://localhost:5000/api/geojson",
        json=building_data
    )
    
    # Extract results
    if response.status_code == 200:
        results = response.json()
        feature = results["features"][0]
        thermal = feature["properties"]["buem"]["thermal_load_profile"]
        
        print(f"Heating demand: {thermal['heating_total_kWh']:.0f} kWh/year")
        print(f"Cooling demand: {thermal['cooling_total_kWh']:.0f} kWh/year")

Step-by-Step Guide
------------------

1. **Prepare Building Data**
   Define building geometry and thermal properties in GeoJSON format.

2. **Submit API Request**
   Send POST request to ``/api/geojson`` endpoint.

3. **Process Results**
   Extract thermal load profile from response.

Error Handling
--------------

.. code-block:: python

    try:
        response = requests.post(url, json=data, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        return None

For detailed examples, see the main :doc:`../api_integration/examples` section.