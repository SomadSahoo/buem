Scaling Strategies
==================

Strategies for scaling BuEM to handle high-volume building analysis workloads.

Horizontal Scaling
------------------

**Load-Based Auto Scaling:**

.. code-block:: yaml

    # Kubernetes HPA
    apiVersion: autoscaling/v2
    kind: HorizontalPodAutoscaler
    metadata:
      name: buem-hpa
    spec:
      scaleTargetRef:
        apiVersion: apps/v1
        kind: Deployment
        name: buem-api
      minReplicas: 3
      maxReplicas: 20
      metrics:
      - type: Resource
        resource:
          name: cpu
          target:
            type: Utilization
            averageUtilization: 70
      - type: Resource
        resource:
          name: memory
          target:
            type: Utilization
            averageUtilization: 80

**Docker Swarm Scaling:**

.. code-block:: bash

    # Scale service replicas
    docker service scale buem-stack_buem-api=10
    
    # Auto-scaling based on CPU
    docker service update \
        --replicas-max-per-node 2 \
        --constraint 'node.role==worker' \
        buem-stack_buem-api

Vertical Scaling
----------------

**Resource Optimization:**

.. code-block:: yaml

    # Optimized container resources
    resources:
      requests:
        cpu: 500m
        memory: 1Gi
      limits:
        cpu: 2000m
        memory: 4Gi

**Memory-Intensive Workloads:**

.. code-block:: python

    # Process large building datasets efficiently
    def process_large_dataset(buildings, chunk_size=100):
        for chunk in chunked(buildings, chunk_size):
            # Process chunk and clear memory
            results = analyze_buildings(chunk)
            yield results
            
            # Force garbage collection
            import gc
            gc.collect()

Database Scaling
----------------

**Weather Data Partitioning:**

.. code-block:: python

    # Partition weather data by region/time
    class WeatherDataManager:
        def __init__(self):
            self.data_cache = {}
            self.cache_size_limit = 1000  # MB
        
        def get_weather_data(self, lat, lon, time_range):
            cache_key = f"{lat:.2f}_{lon:.2f}_{time_range}"
            
            if cache_key not in self.data_cache:
                if self.get_cache_size() > self.cache_size_limit:
                    self.evict_old_data()
                
                self.data_cache[cache_key] = self.load_weather_data(lat, lon, time_range)
            
            return self.data_cache[cache_key]

**Read Replicas for Weather Data:**

.. code-block:: yaml

    # Multiple weather data sources
    services:
      weather-db-primary:
        image: postgres:13
        environment:
          - POSTGRES_DB=weather_data
        volumes:
          - weather-primary:/var/lib/postgresql/data
      
      weather-db-replica-1:
        image: postgres:13
        environment:
          - POSTGRES_DB=weather_data
          - POSTGRES_MASTER_HOST=weather-db-primary
        volumes:
          - weather-replica-1:/var/lib/postgresql/data

Caching Strategies
------------------

**Multi-Level Caching:**

.. code-block:: python

    class BuEMCache:
        def __init__(self):
            # L1: In-memory cache (fastest)
            self.memory_cache = {}
            
            # L2: Redis cache (shared across instances)
            self.redis_client = redis.Redis(host='redis-cluster')
            
            # L3: File system cache (persistent)
            self.file_cache_dir = Path('/var/cache/buem')
        
        def get(self, key):
            # Try L1 cache first
            if key in self.memory_cache:
                return self.memory_cache[key]
            
            # Try L2 cache
            redis_value = self.redis_client.get(key)
            if redis_value:
                result = json.loads(redis_value)
                self.memory_cache[key] = result  # Populate L1
                return result
            
            # Try L3 cache
            file_path = self.file_cache_dir / f"{key}.json"
            if file_path.exists():
                with open(file_path) as f:
                    result = json.load(f)
                    self.memory_cache[key] = result  # Populate L1
                    self.redis_client.setex(key, 3600, json.dumps(result))  # Populate L2
                    return result
            
            return None

**Regional Caching:**

.. code-block:: python

    # Cache results by geographic regions
    def get_cache_key(building_attrs):
        coords = building_attrs['coordinates']
        lat, lon = coords['latitude'], coords['longitude']
        
        # Round to nearest 0.1 degree for regional caching
        region_lat = round(lat * 10) / 10
        region_lon = round(lon * 10) / 10
        
        # Include building type and key attributes
        building_hash = hash((
            building_attrs['building_type'],
            building_attrs['floor_area'],
            building_attrs['storeys']
        ))
        
        return f"region_{region_lat}_{region_lon}_{building_hash}"

Performance Monitoring
----------------------

**Metrics Collection:**

.. code-block:: python

    from prometheus_client import Counter, Histogram, Gauge
    
    # Request metrics
    REQUEST_COUNT = Counter('buem_requests_total', 'Total requests', ['method', 'endpoint'])
    REQUEST_DURATION = Histogram('buem_request_duration_seconds', 'Request duration')
    
    # System metrics
    ACTIVE_CONNECTIONS = Gauge('buem_active_connections', 'Active connections')
    CACHE_HIT_RATE = Gauge('buem_cache_hit_rate', 'Cache hit rate')
    MEMORY_USAGE = Gauge('buem_memory_usage_bytes', 'Memory usage')
    
    # Building processing metrics
    BUILDINGS_PROCESSED = Counter('buem_buildings_processed_total', 'Buildings processed')
    PROCESSING_TIME = Histogram('buem_building_processing_seconds', 'Building processing time')

**Alerting Rules:**

.. code-block:: yaml

    # Prometheus alerting rules
    groups:
    - name: buem-alerts
      rules:
      - alert: HighResponseTime
        expr: histogram_quantile(0.95, buem_request_duration_seconds) > 5
        for: 2m
        annotations:
          summary: "BuEM API response time is high"
      
      - alert: LowCacheHitRate
        expr: buem_cache_hit_rate < 0.7
        for: 5m
        annotations:
          summary: "BuEM cache hit rate is low"
      
      - alert: HighMemoryUsage
        expr: buem_memory_usage_bytes / (1024*1024*1024) > 3
        for: 2m
        annotations:
          summary: "BuEM memory usage is high"

For advanced scaling scenarios, see :doc:`cloud_providers` and :doc:`../technical/performance`.