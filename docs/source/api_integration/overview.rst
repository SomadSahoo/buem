API Overview
============

BuEM (Building Energy Model) provides a REST API specifically designed for integration with external building simulation tools and energy management systems.

Architecture
------------

The BuEM API follows a microservices architecture pattern:

::

    External System → Docker Container → BuEM API → Thermal Model → Results

Key Features
------------

**Synchronous Processing**
  All API calls are processed synchronously, ensuring predictable response times and easier integration patterns.

**GeoJSON Standard**
  Input and output data use the GeoJSON standard for spatial building data, making integration with GIS systems straightforward.

**Comprehensive Error Handling** 
  Detailed error messages and status codes help diagnose integration issues quickly.

**Timeseries Data Export**
  Optional detailed timeseries data export for in-depth analysis.

**Docker Ready**
  Fully containerized for easy deployment and scaling.

Integration Patterns
-------------------

**Direct API Calls**
  Simple HTTP requests for single building analysis.

**Batch Processing**
  Submit multiple buildings in a single GeoJSON FeatureCollection.

**Webhook Integration** *(Future)*
  Asynchronous processing with webhook callbacks for long-running jobs.

Data Flow
---------

1. **Input**: GeoJSON FeatureCollection with building attributes
2. **Processing**: Thermal model execution with weather data
3. **Output**: GeoJSON response with thermal load results
4. **Optional**: Compressed timeseries file download

Performance Characteristics
---------------------------

- **Single Building**: ~1-3 seconds typical response time
- **Batch (10+ buildings)**: Scales linearly with building count  
- **Memory Usage**: ~50MB baseline + 5MB per building
- **Accuracy**: Validated against EN ISO 52016 standard

Next Steps
----------

Continue to :doc:`docker_setup` for deployment instructions or :doc:`api_endpoints` for detailed API reference.