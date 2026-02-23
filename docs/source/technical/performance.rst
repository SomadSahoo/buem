Performance
===========

Performance characteristics, optimization strategies, and benchmarks for BuEM.

Performance Characteristics
---------------------------

**Typical Processing Times:**

- Single building analysis: 50-200ms
- Batch of 10 buildings: 300-800ms
- Batch of 100 buildings: 2-5 seconds
- Large dataset (1000 buildings): 30-60 seconds

**Resource Requirements:**

- Memory usage: 50-200MB base + 1-5MB per building
- CPU usage: 1-2 cores for typical workloads
- Disk space: 100MB for weather data + results cache
- Network: Minimal for API calls, varies with building data size

**Scalability Metrics:**

- Concurrent requests: Up to 50 simultaneous API calls
- Throughput: 100-500 buildings per minute (depends on complexity)
- Cache hit ratio: 60-80% for repeated building types

Bottleneck Analysis
-------------------

**Primary Performance Bottlenecks:**

1. **Weather Data Loading**:
   - File I/O for CSV reading
   - Geographic coordinate calculations
   - Time-series interpolation

2. **Thermal Calculations**:
   - Heat transfer computations
   - Time-series processing
   - Occupancy pattern generation

3. **Data Serialization**:
   - JSON parsing/generation
   - GeoJSON structure creation
   - Result formatting

**Performance Profiling Example:**

.. code-block:: python

    import cProfile
    import pstats
    
    def profile_building_analysis(building_data):
        profiler = cProfile.Profile()
        profiler.enable()
        
        # Run analysis
        result = analyze_building(building_data)
        
        profiler.disable()
        stats = pstats.Stats(profiler)
        
        # Print top time consumers
        print("Top 10 time consumers:")
        stats.sort_stats('cumulative').print_stats(10)
        
        return result

Optimization Strategies
-----------------------

**1. Weather Data Optimization:**

.. code-block:: python

    class OptimizedWeatherLoader:
        def __init__(self, data_dir):
            self.data_dir = Path(data_dir)
            # Pre-load station metadata
            self.station_metadata = self._load_station_metadata()
            # Memory-mapped weather files
            self.memory_mapped_data = {}
        
        def load_weather_data_optimized(self, lat, lon, date_range):
            # Fast station lookup using spatial indexing
            closest_station = self._fast_station_lookup(lat, lon)
            
            # Memory-mapped file access
            if closest_station not in self.memory_mapped_data:
                self.memory_mapped_data[closest_station] = self._mmap_weather_file(closest_station)
            
            # Vectorized data extraction
            return self._extract_vectorized(self.memory_mapped_data[closest_station], date_range)

**2. Thermal Calculation Vectorization:**

.. code-block:: python

    import numpy as np
    
    class VectorizedThermalModel:
        def calculate_heating_demand_vectorized(self, temperatures):
            # Vectorized operations using NumPy
            T_out = np.array(temperatures)
            T_in = 20.0
            dT = np.maximum(T_in - T_out, 0)  # Heating only
            
            # Vectorized heat transfer calculation
            Q_transmission = (
                self.wall_area * self.U_wall * dT +
                self.roof_area * self.U_roof * dT +
                self.window_area * self.U_window * dT
            )
            
            return Q_transmission.tolist()

**3. Multi-level Caching:**

.. code-block:: python

    from functools import lru_cache
    import hashlib
    
    class PerformanceOptimizedAnalyzer:
        def __init__(self):
            self.l1_cache = {}  # In-memory cache
            self.l2_cache_dir = Path('.cache')  # Disk cache
            
        @lru_cache(maxsize=1000)
        def get_weather_data(self, lat, lon, date_hash):
            # Cached weather data lookup
            return self._load_weather_data(lat, lon, date_hash)
        
        def analyze_building_cached(self, building_data):
            # Generate cache key from building attributes
            attrs = building_data['properties']['buem']['building_attributes']
            cache_key = self._generate_cache_key(attrs)
            
            # L1 cache check
            if cache_key in self.l1_cache:
                return self.l1_cache[cache_key]
            
            # L2 cache check
            cache_file = self.l2_cache_dir / f"{cache_key}.json"
            if cache_file.exists():
                with open(cache_file) as f:
                    result = json.load(f)
                    self.l1_cache[cache_key] = result
                    return result
            
            # Compute and cache
            result = self._analyze_building(building_data)
            self.l1_cache[cache_key] = result
            
            # Save to L2 cache
            with open(cache_file, 'w') as f:
                json.dump(result, f)
            
            return result

**4. Batch Processing Optimization:**

.. code-block:: python

    def optimized_batch_processing(buildings):
        # Group buildings by location for weather data efficiency
        location_groups = defaultdict(list)
        for building in buildings:
            coords = building['properties']['buem']['building_attributes']['coordinates']
            # Round coordinates for grouping
            lat_rounded = round(coords['latitude'], 2)
            lon_rounded = round(coords['longitude'], 2)
            location_key = (lat_rounded, lon_rounded)
            location_groups[location_key].append(building)
        
        results = []
        for location, buildings_group in location_groups.items():
            # Load weather data once per location group
            weather_data = weather_loader.load_weather_data(*location)
            
            # Process all buildings in the group with shared weather data
            for building in buildings_group:
                result = analyze_building_with_weather(building, weather_data)
                results.append(result)
        
        return results

Memory Management
-----------------

**Memory Usage Monitoring:**

.. code-block:: python

    import psutil
    import gc
    
    def monitor_memory_usage():
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            'rss': memory_info.rss / 1024 / 1024,  # MB
            'vms': memory_info.vms / 1024 / 1024,  # MB
            'percent': process.memory_percent()
        }
    
    def analyze_with_memory_management(buildings):
        results = []
        
        for i, building in enumerate(buildings):
            result = analyze_building(building)
            results.append(result)
            
            # Periodic memory cleanup
            if i % 100 == 0:
                gc.collect()
                memory = monitor_memory_usage()
                
                if memory['percent'] > 80:
                    # Clear caches if memory usage is high
                    clear_weather_cache()
                    gc.collect()

**Efficient Data Structures:**

.. code-block:: python

    # Use slots for memory efficiency
    class EfficientBuilding:
        __slots__ = ['id', 'coordinates', 'floor_area', 'attributes']
        
        def __init__(self, building_data):
            self.id = building_data['id']
            attrs = building_data['properties']['buem']['building_attributes']
            self.coordinates = (attrs['coordinates']['latitude'], 
                              attrs['coordinates']['longitude'])
            self.floor_area = attrs.get('floor_area', 100)
            self.attributes = attrs

Concurrency and Parallelization
-------------------------------

**Thread-Safe Processing:**

.. code-block:: python

    import threading
    from concurrent.futures import ThreadPoolExecutor
    
    class ThreadSafeAnalyzer:
        def __init__(self):
            self._local = threading.local()
        
        def get_analyzer(self):
            if not hasattr(self._local, 'analyzer'):
                self._local.analyzer = BuildingAnalyzer()
            return self._local.analyzer
        
        def parallel_analysis(self, buildings, max_workers=4):
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [
                    executor.submit(self._analyze_single, building)
                    for building in buildings
                ]
                
                results = []
                for future in futures:
                    try:
                        result = future.result(timeout=30)
                        results.append(result)
                    except Exception as e:
                        logger.error(f"Analysis failed: {e}")
                        results.append(None)
                
                return results
        
        def _analyze_single(self, building):
            analyzer = self.get_analyzer()
            return analyzer.analyze(building)

Performance Benchmarks
----------------------

**Benchmark Test Suite:**

.. code-block:: python

    import time
    
    class BuEMBenchmark:
        def __init__(self):
            self.results = {}
        
        def benchmark_single_building(self, iterations=100):
            building = self.generate_test_building()
            times = []
            
            for _ in range(iterations):
                start = time.time()
                result = analyze_building(building)
                end = time.time()
                times.append(end - start)
            
            self.results['single_building'] = {
                'mean': np.mean(times),
                'std': np.std(times),
                'min': np.min(times),
                'max': np.max(times),
                'p95': np.percentile(times, 95)
            }
        
        def benchmark_batch_processing(self, batch_sizes=[10, 50, 100, 500]):
            for size in batch_sizes:
                buildings = [self.generate_test_building() for _ in range(size)]
                
                start = time.time()
                results = analyze_buildings_batch(buildings)
                end = time.time()
                
                self.results[f'batch_{size}'] = {
                    'total_time': end - start,
                    'per_building': (end - start) / size,
                    'throughput': size / (end - start)
                }
        
        def generate_performance_report(self):
            report = ["BuEM Performance Benchmark Results"]
            report.append("=" * 40)
            
            for test_name, metrics in self.results.items():
                report.append(f"\n{test_name}:")
                for metric, value in metrics.items():
                    report.append(f"  {metric}: {value:.4f}")
            
            return "\n".join(report)

**Example Benchmark Results:**

.. code-block:: text

    BuEM Performance Benchmark Results
    ========================================
    
    single_building:
      mean: 0.0856
      std: 0.0124
      min: 0.0723
      max: 0.1234
      p95: 0.1045
    
    batch_10:
      total_time: 0.4521
      per_building: 0.0452
      throughput: 22.12
    
    batch_100:
      total_time: 3.2145
      per_building: 0.0321
      throughput: 31.11

For more optimization techniques, see :doc:`../deployment/scaling_strategies` and :doc:`../examples/performance_optimization`.