Error Handling
==============

BuEM provides comprehensive error handling to help diagnose and resolve integration issues.

Error Response Format
---------------------

All API errors follow a consistent JSON structure:

.. code-block:: json

    {
      "error": {
        "code": "ERROR_TYPE",
        "message": "Human readable error description",
        "details": [...],
        "request_id": "uuid",
        "timestamp": "2026-02-23T10:30:00Z"
      }
    }

HTTP Status Codes
-----------------

**Client Errors (4xx)**

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Status Code
     - Description
   * - ``400 Bad Request``
     - Invalid JSON format, malformed GeoJSON structure
   * - ``422 Unprocessable Entity``  
     - Valid JSON but invalid building attributes or validation failed
   * - ``404 Not Found``
     - Requested file or endpoint does not exist
   * - ``405 Method Not Allowed``
     - HTTP method not supported for endpoint
   * - ``413 Payload Too Large``
     - Request exceeds maximum size limits

**Server Errors (5xx)**

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Status Code
     - Description
   * - ``500 Internal Server Error``
     - Model execution error, unexpected server failure
   * - ``503 Service Unavailable``  
     - Server temporarily unavailable or overloaded
   * - ``507 Insufficient Storage``
     - Cannot save timeseries data due to disk space

Error Categories
----------------

**VALIDATION_ERROR**

Building attributes fail validation rules.

.. code-block:: json

    {
      "error": {
        "code": "VALIDATION_ERROR",
        "message": "Building attribute validation failed",
        "details": [
          "components.Walls.U must be a positive number",
          "latitude must be between -90 and 90",
          "components.Windows.elements[0].area exceeds parent wall area"
        ]
      }
    }

**GEOJSON_ERROR**

Invalid GeoJSON structure.

.. code-block:: json

    {
      "error": {
        "code": "GEOJSON_ERROR", 
        "message": "Invalid GeoJSON format",
        "details": [
          "Missing required field: type",
          "features must be an array"
        ]
      }
    }

**MODEL_ERROR**

Thermal model execution failure.

.. code-block:: json

    {
      "error": {
        "code": "MODEL_ERROR",
        "message": "Thermal model execution failed", 
        "details": [
          "Convergence failure in thermal solver",
          "Building ID: B001"
        ]
      }
    }

**FILE_ERROR**

File operations failure.

.. code-block:: json

    {
      "error": {
        "code": "FILE_ERROR",
        "message": "Cannot access requested file",
        "details": [
          "File not found: buem_ts_missing123.json.gz",
          "File may have expired or been cleaned up"
        ]
      }
    }

Common Error Scenarios
----------------------

**Missing Required Attributes**

.. code-block:: json

    {
      "error": {
        "code": "VALIDATION_ERROR",
        "message": "Required attributes missing",
        "details": [
          "properties.buem.building_attributes is required",
          "components.Walls is required"
        ]
      }
    }

**Invalid Numeric Values**

.. code-block:: json

    {
      "error": {
        "code": "VALIDATION_ERROR", 
        "message": "Invalid numeric values",
        "details": [
          "A_ref must be positive (got: -100)",
          "U values cannot be zero or negative"
        ]
      }
    }

**Weather Data Issues**

.. code-block:: json

    {
      "error": {
        "code": "MODEL_ERROR",
        "message": "Weather data unavailable",
        "details": [
          "Weather CSV not found at configured path",
          "Check BUEM_WEATHER_DIR environment variable"
        ]
      }
    }

Debugging Tips
--------------

**Request Validation**

1. Validate JSON syntax with a JSON linter
2. Check GeoJSON structure with online validators
3. Verify all required building attributes are present
4. Ensure numeric values are within valid ranges

**Model Execution Issues**

1. Check thermal properties are physically reasonable
2. Verify total window area doesn't exceed wall area  
3. Ensure air changes and U-values are positive
4. Review coordinate system (lat/lon) for location

**File Download Problems**

1. Download files immediately after API response
2. Check available disk space on server
3. Verify file permissions for results directory
4. Files may have retention policies and expire

Error Recovery Strategies
-------------------------

**Retry Logic**

For transient server errors (5xx), implement exponential backoff:

.. code-block:: python

    import time
    import requests

    def api_call_with_retry(url, data, max_retries=3):
        for attempt in range(max_retries):
            try:
                response = requests.post(url, json=data)
                if response.status_code < 500:
                    return response
                time.sleep(2 ** attempt)
            except requests.RequestException:
                time.sleep(2 ** attempt)
        return None

**Batch Processing Recovery**

For large batches, process features individually on errors:

.. code-block:: python

    def process_building_batch(buildings):
        successful = []
        failed = []
        
        # Try batch first
        try:
            response = api_call({"type": "FeatureCollection", "features": buildings})
            return response
        except Exception:
            # Fall back to individual processing
            for building in buildings:
                try:
                    result = api_call({"type": "Feature", **building})
                    successful.append(result)
                except Exception as e:
                    failed.append({"building": building["id"], "error": str(e)})
        
        return {"successful": successful, "failed": failed}

**Validation Pre-check**

Validate requests locally before sending to API:

.. code-block:: python

    def validate_building_request(feature):
        errors = []
        
        # Check required structure
        if "properties" not in feature:
            errors.append("Missing properties")
        
        attrs = feature.get("properties", {}).get("buem", {}).get("building_attributes", {})
        
        # Check required attributes
        required = ["latitude", "longitude", "A_ref", "components"]
        for field in required:
            if field not in attrs:
                errors.append(f"Missing required field: {field}")
        
        # Check numeric ranges
        if "latitude" in attrs:
            lat = attrs["latitude"]
            if not -90 <= lat <= 90:
                errors.append(f"Invalid latitude: {lat}")
        
        return errors

Production Considerations
-------------------------

**Logging and Monitoring**

- Log all API responses with status codes
- Monitor error rates and patterns  
- Set up alerts for high error rates or specific error types
- Track processing times for performance monitoring

**Error Notification**

.. code-block:: python

    def handle_api_error(response):
        if response.status_code >= 400:
            error_data = response.json().get("error", {})
            
            # Log structured error data
            logger.error("BuEM API Error", extra={
                "error_code": error_data.get("code"),
                "message": error_data.get("message"),
                "details": error_data.get("details"),
                "status_code": response.status_code
            })
            
            # Send alerts for critical errors
            if response.status_code >= 500:
                send_alert(f"BuEM API server error: {error_data.get('message')}")

Next Steps
----------

Continue to :doc:`examples` for complete integration examples showing error handling in practice.