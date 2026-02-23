API Endpoints Reference
=======================

BuEM provides RESTful API endpoints for building energy model processing.

Base URL
--------

When running locally: ``http://localhost:5000/api``

Core Endpoints
--------------

POST /api/geojson
~~~~~~~~~~~~~~~~~

Submit building data for thermal analysis.

**Request**

- **Method**: ``POST``
- **Content-Type**: ``application/json``
- **Body**: GeoJSON FeatureCollection or Feature

**Parameters**

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 50

   * - Parameter
     - Type
     - Required
     - Description
   * - ``include_timeseries``
     - boolean
     - No
     - Include detailed timeseries data export (default: false)
   * - ``use_milp``
     - boolean
     - No
     - Use MILP solver for optimization (default: false)

**Example Request**

.. code-block:: bash

    curl -X POST \\
      "http://localhost:5000/api/geojson?include_timeseries=true" \\
      -H "Content-Type: application/json" \\
      -d @sample_request.geojson

**Response**

- **Status**: ``200 OK``
- **Content-Type**: ``application/json``
- **Body**: GeoJSON FeatureCollection with thermal load results

**Example Response**

.. code-block:: json

    {
      "type": "FeatureCollection",
      "processed_at": "2026-02-23T10:30:00Z",
      "processing_elapsed_s": 2.45,
      "features": [
        {
          "type": "Feature",
          "id": "B001",
          "geometry": { "type": "Point", "coordinates": [-0.1278, 51.5074] },
          "properties": {
            "buem": {
              "building_attributes": { "..." },
              "thermal_load_profile": {
                "heating_total_kWh": 15420.5,
                "heating_peak_kW": 8.2,
                "cooling_total_kWh": 3250.1,
                "cooling_peak_kW": 4.1,
                "electricity_total_kWh": 4200.0,
                "electricity_peak_kW": 2.1,
                "start_time": "2018-01-01T00:00:00Z",
                "end_time": "2018-12-31T23:00:00Z",
                "n_points": 8760,
                "elapsed_s": 1.23,
                "timeseries_file": "/api/files/buem_ts_abc123.json.gz"
              }
            }
          }
        }
      ]
    }

GET /api/files/{filename}
~~~~~~~~~~~~~~~~~~~~~~~~~

Download timeseries data files.

**Request**

- **Method**: ``GET``
- **Path**: ``/api/files/{filename}``

**Parameters**

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 50

   * - Parameter
     - Type
     - Required
     - Description
   * - ``filename``
     - string
     - Yes
     - Filename from timeseries_file response field

**Response**

- **Status**: ``200 OK``
- **Content-Type**: ``application/gzip``
- **Body**: Gzipped JSON file with timeseries data

**Example Request**

.. code-block:: bash

    curl -X GET \\
      "http://localhost:5000/api/files/buem_ts_abc123.json.gz" \\
      --output timeseries.json.gz

**Timeseries File Format**

When decompressed, the JSON structure is:

.. code-block:: json

    {
      "index": [
        "2018-01-01T00:00:00Z",
        "2018-01-01T01:00:00Z",
        "..."
      ],
      "heat": [2.1, 2.3, 2.0, "..."],
      "cool": [-0.5, -0.8, -0.2, "..."],
      "electricity": [0.8, 0.9, 0.7, "..."]
    }

Utility Endpoints
-----------------

GET /api/health
~~~~~~~~~~~~~~~

Health check endpoint.

**Response**

.. code-block:: json

    {
      "status": "healthy",
      "version": "1.0.0",
      "timestamp": "2026-02-23T10:30:00Z"
    }

GET /api/attributes/schema
~~~~~~~~~~~~~~~~~~~~~~~~~~

Get JSON schema for building attributes.

**Response**

.. code-block:: json

    {
      "type": "object",
      "properties": {
        "latitude": {"type": "number", "minimum": -90, "maximum": 90},
        "longitude": {"type": "number", "minimum": -180, "maximum": 180},
        "A_ref": {"type": "number", "minimum": 0},
        "components": {
          "type": "object",
          "properties": {
            "Walls": {"..."},
            "Roof": {"..."},
            "...": "..."
          }
        }
      }
    }

Error Responses
---------------

All endpoints return consistent error responses:

**Client Errors (4xx)**

.. list-table::
   :header-rows: 1
   :widths: 15 85

   * - Status Code
     - Description
   * - ``400 Bad Request``
     - Invalid JSON format or missing required fields
   * - ``404 Not Found``
     - Requested file or endpoint not found
   * - ``422 Unprocessable Entity``
     - Valid JSON but invalid building attributes

**Server Errors (5xx)**

.. list-table::
   :header-rows: 1
   :widths: 15 85

   * - Status Code
     - Description
   * - ``500 Internal Server Error``
     - Model execution error or server-side issue

**Error Response Format**

.. code-block:: json

    {
      "error": {
        "code": "VALIDATION_ERROR",
        "message": "Building attribute validation failed",
        "details": [
          "components.Walls.U must be a positive number",
          "latitude is required"
        ]
      },
      "timestamp": "2026-02-23T10:30:00Z"
    }

Rate Limiting
-------------

Currently, no rate limiting is implemented. For production deployments, consider implementing rate limiting at the reverse proxy level.

Authentication
--------------

The current API does not require authentication. For production deployments, implement authentication as needed (API keys, OAuth2, etc.).

Next Steps
----------

Continue to :doc:`request_format` to understand the input data format in detail.