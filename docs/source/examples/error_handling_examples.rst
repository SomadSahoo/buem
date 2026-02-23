Error Handling Examples
=======================

Comprehensive error handling strategies for robust BuEM integration.

Validation Error Handling
-------------------------

.. code-block:: python

    def handle_validation_errors(response):
        if response.status_code == 422:
            error_data = response.json().get('error', {})
            details = error_data.get('details', [])
            
            print(f"Validation failed: {error_data.get('message')}")
            for detail in details:
                print(f"  - {detail}")
            
            # Extract specific validation issues
            if any('latitude' in detail for detail in details):
                print("Issue: Invalid coordinate values")
            if any('components' in detail for detail in details): 
                print("Issue: Building component specification error")

Retry Logic Implementation
--------------------------

.. code-block:: python

    import time
    
    def api_request_with_retry(url, data, max_retries=3):
        for attempt in range(max_retries):
            try:
                response = requests.post(url, json=data, timeout=30)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code >= 500:
                    # Server error - retry
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        print(f"Server error, retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                else:
                    # Client error - don't retry
                    handle_client_error(response)
                    return None
                    
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    print(f"Timeout, retry {attempt + 1}/{max_retries}")
                    time.sleep(2 ** attempt)
                else:
                    print("Request timed out after all retries")
                    return None
                    
        return None

Graceful Degradation
--------------------

.. code-block:: python

    def analyze_with_fallback(building_data):
        try:
            # Try primary BuEM instance
            return buem_primary.analyze(building_data)
        except Exception as e1:
            print(f"Primary API failed: {e1}")
            
            try:
                # Fallback to secondary instance
                return buem_secondary.analyze(building_data)
            except Exception as e2:
                print(f"Secondary API also failed: {e2}")
                
                # Return simplified estimate
                return estimate_simple_loads(building_data)

For more examples, see :doc:`../api_integration/error_handling`.