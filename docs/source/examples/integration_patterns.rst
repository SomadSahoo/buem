Integration Patterns
====================

Common architectural patterns for integrating BuEM with other energy modeling systems.

Pattern 1: Direct API Integration
----------------------------------

**Use Case**: Simple building analysis in existing applications.

.. code-block:: python

    class BuEMIntegration:
        def __init__(self, api_url):
            self.api_url = api_url
        
        def analyze_building(self, building_data):
            response = requests.post(f"{self.api_url}/api/geojson", json=building_data)
            return response.json()

Pattern 2: Queue-Based Processing
---------------------------------

**Use Case**: High-volume building analysis with job queues.

.. code-block:: python

    # Using Celery or similar task queue
    @celery_app.task
    def analyze_building_async(building_id, building_data):
        result = buem_api.analyze(building_data)
        store_result(building_id, result)
        return result

Pattern 3: Microservice Architecture
------------------------------------

**Use Case**: BuEM as part of larger microservice ecosystem.

.. code-block:: yaml

    # docker-compose.yml
    services:
      buem-api:
        image: buem:latest
        ports:
          - "5000:5000"
        environment:
          - BUEM_WEATHER_DIR=/data/weather
      
      building-service:
        image: building-analyzer:latest
        depends_on:
          - buem-api
        environment:
          - BUEM_API_URL=http://buem-api:5000

Pattern 4: Event-Driven Integration
-----------------------------------

**Use Case**: Reactive building analysis triggered by external events.

.. code-block:: python

    # Event handler for building updates
    def on_building_updated(event):
        building_data = event['building_data']
        analysis_result = buem_client.analyze(building_data)
        publish_event('building_analyzed', analysis_result)

For detailed implementation examples, see :doc:`../api_integration/examples`.