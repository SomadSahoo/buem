Performance Optimization
========================

Optimization strategies for high-performance BuEM integration.

Connection Pooling
------------------

.. code-block:: python

    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    
    class OptimizedBuEMClient:
        def __init__(self, base_url):
            self.base_url = base_url
            self.session = requests.Session()
            
            # Connection pooling
            adapter = HTTPAdapter(
                pool_connections=10,
                pool_maxsize=20,
                max_retries=Retry(total=3, backoff_factor=1)
            )
            self.session.mount('http://', adapter)
            self.session.mount('https://', adapter)
        
        def analyze(self, building_data):
            return self.session.post(f"{self.base_url}/api/geojson", json=building_data)

Batch Size Optimization
-----------------------

.. code-block:: python

    def optimal_batch_processing(buildings, batch_size=25):
        """Process buildings in optimal batch sizes."""
        
        results = []
        for i in range(0, len(buildings), batch_size):
            batch = buildings[i:i + batch_size]
            
            batch_request = {
                "type": "FeatureCollection",
                "features": batch
            }
            
            start_time = time.time()
            response = buem_client.analyze(batch_request)
            elapsed = time.time() - start_time
            
            print(f"Batch {i//batch_size + 1}: {len(batch)} buildings in {elapsed:.2f}s")
            results.extend(response['features'])
            
            # Rate limiting
            if elapsed < 1.0:
                time.sleep(1.0 - elapsed)
        
        return results

Caching Strategy
----------------

.. code-block:: python

    import hashlib
    import json
    
    class CachedBuEMClient:
        def __init__(self, base_url, cache_dir=".cache"):
            self.client = BuEMClient(base_url)
            self.cache_dir = Path(cache_dir)
            self.cache_dir.mkdir(exist_ok=True)
        
        def analyze(self, building_data):
            # Generate cache key from building attributes
            attrs = building_data['properties']['buem']['building_attributes']
            cache_key = hashlib.md5(json.dumps(attrs, sort_keys=True).encode()).hexdigest()
            cache_file = self.cache_dir / f"{cache_key}.json"
            
            # Check cache
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    return json.load(f)
            
            # Compute and cache result
            result = self.client.analyze(building_data)
            with open(cache_file, 'w') as f:
                json.dump(result, f)
            
            return result

Parallel Processing
-------------------

.. code-block:: python

    from concurrent.futures import ThreadPoolExecutor
    
    def parallel_building_analysis(buildings, max_workers=4):
        """Process buildings in parallel threads."""
        
        def analyze_single(building):
            feature_collection = {
                "type": "FeatureCollection",
                "features": [building]
            }
            return buem_client.analyze(feature_collection)
        
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_building = {
                executor.submit(analyze_single, building): building 
                for building in buildings
            }
            
            for future in concurrent.futures.as_completed(future_to_building):
                building = future_to_building[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"Building {building['id']} failed: {e}")
        
        return results

For additional optimization techniques, see :doc:`../technical/performance`.