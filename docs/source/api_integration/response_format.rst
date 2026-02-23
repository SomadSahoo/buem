Response Data Format
====================

BuEM returns results in GeoJSON format with thermal load analysis results added to each building feature.

Response Structure
------------------

**Top Level Response**

.. code-block:: json

    {
      "type": "FeatureCollection",
      "processed_at": "2026-02-23T10:30:00Z",
      "processing_elapsed_s": 2.45,
      "features": [...]
    }

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Field
     - Type
     - Description
   * - ``type``
     - string
     - Always "FeatureCollection"
   * - ``processed_at``
     - string
     - ISO 8601 timestamp of processing completion
   * - ``processing_elapsed_s``
     - number
     - Total processing time in seconds
   * - ``features``
     - array
     - Array of processed building features

Feature Structure
-----------------

Each feature contains the original building data plus thermal analysis results:

.. code-block:: json

    {
      "type": "Feature",
      "id": "B001",
      "geometry": { "type": "Point", "coordinates": [-0.1278, 51.5074] },
      "properties": {
        "buem": {
          "building_attributes": {...},
          "thermal_load_profile": {...}
        }
      }
    }

Thermal Load Profile
--------------------

The ``thermal_load_profile`` object contains the main analysis results:

**Summary Statistics**

.. code-block:: json

    {
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

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Field
     - Type
     - Description
   * - ``heating_total_kWh``
     - number
     - Annual heating energy demand (kWh)
   * - ``heating_peak_kW``
     - number
     - Peak heating power demand (kW)
   * - ``cooling_total_kWh``
     - number
     - Annual cooling energy demand (kWh, absolute value)
   * - ``cooling_peak_kW``
     - number
     - Peak cooling power demand (kW, absolute value)
   * - ``electricity_total_kWh``
     - number
     - Annual electricity consumption (kWh)
   * - ``electricity_peak_kW``
     - number
     - Peak electricity demand (kW)
   * - ``start_time``
     - string
     - Start of simulation period (ISO 8601)
   * - ``end_time``
     - string
     - End of simulation period (ISO 8601)
   * - ``n_points``
     - integer
     - Number of hourly data points (typically 8760)
   * - ``elapsed_s``
     - number
     - Processing time for this building (seconds)
   * - ``timeseries_file``
     - string
     - Download URL for detailed timeseries (optional)

Energy Values Interpretation
----------------------------

**Heating Values**
- Positive values indicate heating demand
- Units: kWh for total, kW for peak
- Represents thermal energy needed to maintain comfort

**Cooling Values**  
- Model outputs negative values for cooling
- API returns absolute values for consistency
- Units: kWh for total, kW for peak
- Represents thermal energy to be removed

**Electricity Values**
- Represents building electricity consumption (lighting, appliances, etc.)
- Does not include HVAC electricity consumption
- Based on occupancy patterns and building use

Timeseries Data Format
----------------------

When ``include_timeseries=true`` is specified in the request, detailed hourly data is available for download.

**File Access**

The ``timeseries_file`` field provides a download URL:

.. code-block:: bash

    curl -X GET "http://localhost:5000/api/files/buem_ts_abc123.json.gz" \\
         --output timeseries.json.gz

**File Structure**

The compressed JSON file contains:

.. code-block:: json

    {
      "index": [
        "2018-01-01T00:00:00Z",
        "2018-01-01T01:00:00Z",
        "2018-01-01T02:00:00Z",
        "..."
      ],
      "heat": [2.1, 2.3, 2.0, 1.8, "..."],
      "cool": [-0.5, -0.8, -0.2, 0.0, "..."],
      "electricity": [0.8, 0.9, 0.7, 0.6, "..."]
    }

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Array
     - Units
     - Description
   * - ``index``
     - ISO 8601
     - Hourly timestamps for the simulation year
   * - ``heat``
     - kW
     - Hourly heating power demand (positive values)
   * - ``cool``
     - kW
     - Hourly cooling power demand (negative values)
   * - ``electricity``
     - kW
     - Hourly electricity consumption (positive values)

Error Handling in Responses
---------------------------

**Feature-Level Errors**

If a building fails to process, the feature will contain an error field:

.. code-block:: json

    {
      "type": "Feature",
      "id": "B002",
      "properties": {
        "buem": {
          "building_attributes": {...},
          "error": "Building attribute validation failed: components.Walls.U must be positive"
        }
      }
    }

**Partial Results**

Features with errors are still included in the response to provide transparency about processing status.

Data Quality Indicators
-----------------------

**NaN/Infinite Value Handling**

BuEM automatically sanitizes results:
- NaN values are replaced with 0.0
- Infinite values are capped at ±1e9
- Warnings are logged for data quality issues

**Missing Data**

If timeseries data cannot be generated:
- Summary values may be 0.0
- ``n_points`` will reflect actual data availability
- ``start_time`` and ``end_time`` may be null

Complete Example Response
-------------------------

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
              "building_attributes": {
                "latitude": 51.5074,
                "longitude": -0.1278,
                "A_ref": 100.0,
                "components": {...}
              },
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

Integration Notes
-----------------

**Units Consistency**
- All energy values use kWh (kilowatt-hours)
- All power values use kW (kilowatts)  
- All timestamps use ISO 8601 format with UTC timezone

**File Lifecycle**
- Timeseries files are automatically generated with unique names
- Files persist for download but may be cleaned up after a retention period
- Download files immediately after receiving the response

**Performance Considerations**
- Large timeseries files (8760+ points) can be several MB when compressed
- Consider batch downloading for multiple buildings
- Timeseries generation adds ~0.5-1s to processing time per building

Next Steps
----------

Continue to :doc:`error_handling` for detailed error response information.