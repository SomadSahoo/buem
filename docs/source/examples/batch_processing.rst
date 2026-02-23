Batch Processing
================

Process multiple buildings efficiently using BuEM's batch processing capabilities.

Multiple Buildings in Single Request
-------------------------------------

.. code-block:: python

    # Create multiple building variants
    buildings = []
    for i, u_value in enumerate([1.0, 1.5, 2.0]):
        building = {
            "type": "Feature",
            "id": f"Building_{i+1:02d}",
            "geometry": {"type": "Point", "coordinates": [5.0, 52.0]},
            "properties": {
                "buem": {
                    "building_attributes": {
                        "latitude": 52.0,
                        "longitude": 5.0, 
                        "A_ref": 100.0,
                        "components": {
                            "Walls": {"U": u_value, "elements": [{"id": "Wall_1", "area": 80.0, "azimuth": 180.0, "tilt": 90.0}]},
                            "Ventilation": {"elements": [{"id": "Vent_1", "air_changes": 0.5}]}
                        }
                    }
                }
            }
        }
        buildings.append(building)
    
    # Submit batch request
    batch_request = {
        "type": "FeatureCollection", 
        "features": buildings
    }
    
    response = requests.post("http://localhost:5000/api/geojson", json=batch_request)

Performance Considerations
--------------------------

- **Batch Size**: Optimal batch size is 10-50 buildings
- **Timeout**: Increase timeout for larger batches
- **Memory**: Each building uses ~5MB memory during processing
- **Parallel Processing**: API processes buildings in sequence

Error Recovery
--------------

For robust batch processing, handle partial failures:

.. code-block:: python

    def process_building_batch(buildings):
        # Try batch processing first
        try:
            return process_batch(buildings)
        except Exception:
            # Fall back to individual processing
            results = []
            for building in buildings:
                try:
                    result = process_single(building)
                    results.append(result)
                except Exception as e:
                    print(f"Building {building['id']} failed: {e}")
            return results

For complete implementation, see :doc:`../api_integration/examples`.