Troubleshooting
===============

Common issues, solutions, and debugging guidance for BuEM.

Common Issues
------------

**Installation Problems**

*Issue*: ``ModuleNotFoundError: No module named 'buem'``

*Solution*:

.. code-block:: bash

    # Ensure you're in the correct environment
    conda activate buem_env
    
    # Reinstall in development mode
    pip install -e .
    
    # Check Python path
    python -c "import sys; print(sys.path)"

*Issue*: ``ImportError: No module named 'some_dependency'``

*Solution*:

.. code-block:: bash

    # Update environment
    conda env update -f environment.yml
    
    # Or install missing package
    conda install package_name
    # or
    pip install package_name

**API Endpoint Issues**

*Issue*: ``ConnectionRefusedError`` when calling API

*Solution*:

.. code-block:: bash

    # Check if API server is running
    curl http://localhost:5000/health
    
    # Start API server if not running
    python -m buem.apis.api_server
    
    # Check port availability
    netstat -an | grep 5000

*Issue*: ``422 Validation Error`` from API

*Solution*:

.. code-block:: python

    # Check error details in response
    response = requests.post(url, json=data)
    if response.status_code == 422:
        error_details = response.json()['error']['details']
        for detail in error_details:
            print(f"Validation error: {detail}")

Validation Errors
----------------

**Building Attribute Errors**

*Issue*: ``Missing required attribute: coordinates``

*Solution*:

.. code-block:: json

    {
        "properties": {
            "buem": {
                "building_attributes": {
                    "coordinates": {
                        "latitude": 46.5197,
                        "longitude": 6.566
                    },
                    "floor_area": 120.0,
                    "building_type": "residential"
                }
            }
        }
    }

*Issue*: ``U-value outside realistic range``

*Solution*: Check if U-values are in correct units (W/m²K) and realistic:

.. list-table::
   :header-rows: 1

   * - Component
     - Typical Range (W/m²K)
     - Good Value
     - Poor Value
   * - Walls
     - 0.1 - 1.5
     - 0.15 - 0.3
     - > 1.0
   * - Roof
     - 0.1 - 1.2
     - 0.12 - 0.25
     - > 0.8
   * - Windows
     - 0.7 - 6.0
     - 0.8 - 1.5
     - > 3.0

*Issue*: ``Window area exceeds wall area``

*Solution*:

.. code-block:: python

    # Check calculations
    window_to_wall_ratio = window_area / wall_area
    print(f"Window-to-wall ratio: {window_to_wall_ratio:.3f}")
    
    # Should be < 0.9 for most buildings
    if window_to_wall_ratio > 0.9:
        # Reduce window area or increase wall area
        corrected_window_area = wall_area * 0.4  # 40% ratio

**Weather Data Issues**

*Issue*: ``Weather data file not found``

*Solution*:

.. code-block:: python

    import os
    
    # Check if weather directory exists
    weather_dir = "src/buem/data/weather"
    if os.path.exists(weather_dir):
        files = os.listdir(weather_dir)
        print(f"Available weather files: {files}")
    else:
        print(f"Weather directory not found: {weather_dir}")
        # Create directory and add weather files
        os.makedirs(weather_dir, exist_ok=True)

*Issue*: ``Temperature values outside realistic range``

*Solution*:

.. code-block:: python

    import pandas as pd
    
    # Validate weather data
    weather_df = pd.read_csv('weather_file.csv')
    
    # Check temperature range
    print(f"Temperature range: {weather_df['temperature'].min():.1f} to {weather_df['temperature'].max():.1f} °C")
    
    # Check for missing data
    print(f"Missing data points: {weather_df.isnull().sum().sum()}")
    
    # Basic quality checks
    if weather_df['temperature'].min() < -50:
        print("Warning: Very low temperatures found")
    if weather_df['temperature'].max() > 60:
        print("Warning: Very high temperatures found")

Performance Issues
-----------------

**Slow API Responses**

*Issue*: API calls taking > 30 seconds

*Diagnosis*:

.. code-block:: python

    import time
    import cProfile
    
    def profile_analysis(building_data):
        profiler = cProfile.Profile()
        profiler.enable()
        
        start_time = time.time()
        result = analyze_building(building_data)
        end_time = time.time()
        
        profiler.disable()
        profiler.dump_stats('analysis_profile.prof')
        
        print(f"Analysis time: {end_time - start_time:.2f} seconds")
        return result

*Solutions*:

1. **Reduce weather data resolution** (if using sub-hourly data)
2. **Cache weather data** for repeated locations
3. **Optimize building complexity** (reduce unnecessary detail)
4. **Use batch processing** for multiple buildings

**Memory Usage Issues**

*Issue*: High memory consumption during analysis

*Diagnosis*:

.. code-block:: python

    import psutil
    import tracemalloc
    
    def monitor_memory_usage():
        process = psutil.Process()
        memory_info = process.memory_info()
        
        print(f"Memory usage: {memory_info.rss / 1024 / 1024:.1f} MB")
        print(f"Memory percent: {process.memory_percent():.1f}%")
    
    # Trace memory allocations
    tracemalloc.start()
    result = analyze_building(building_data)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    print(f"Current memory usage: {current / 1024 / 1024:.1f} MB")
    print(f"Peak memory usage: {peak / 1024 / 1024:.1f} MB")

*Solutions*:

1. **Process buildings in smaller batches**
2. **Clear caches periodically**
3. **Use memory-efficient data structures**
4. **Force garbage collection** when needed

.. code-block:: python

    import gc
    
    # Force garbage collection
    gc.collect()
    
    # Clear weather cache if memory is tight
    if psutil.virtual_memory().percent > 80:
        clear_weather_cache()

Docker Issues
------------

**Container Build Failures**

*Issue*: ``Docker build fails with package installation errors``

*Solution*:

.. code-block:: bash

    # Clear Docker cache and rebuild
    docker system prune -f
    docker build --no-cache -t buem:latest .
    
    # Check Docker daemon
    docker version
    
    # Build with verbose output
    docker build --progress=plain -t buem:latest .

*Issue*: ``Container exits immediately after start``

*Diagnosis*:

.. code-block:: bash

    # Check container logs
    docker logs buem-container
    
    # Run container interactively
    docker run -it --entrypoint /bin/bash buem:latest
    
    # Check if gunicorn starts properly
    docker run buem:latest gunicorn --version

**Container Runtime Issues**

*Issue*: ``Weather data not found in container``

*Solution*:

.. code-block:: bash

    # Check if volume is mounted correctly
    docker run -v $(pwd)/src/buem/data:/app/data buem:latest ls /app/data
    
    # Verify weather data path in container
    docker exec buem-container ls -la /app/data/weather/

*Issue*: ``Permission denied errors in container``

*Solution*:

.. code-block:: dockerfile

    # In Dockerfile, ensure proper permissions
    RUN chown -R app:app /app/data
    RUN chmod -R 755 /app/data
    
    # Or run as root if necessary
    USER root

Debugging Tools
--------------

**Logging Configuration**

.. code-block:: python

    import logging
    
    # Configure detailed logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('buem_debug.log'),
            logging.StreamHandler()
        ]
    )
    
    # Add module-specific loggers
    thermal_logger = logging.getLogger('buem.thermal')
    weather_logger = logging.getLogger('buem.weather')
    api_logger = logging.getLogger('buem.api')

**Data Inspection Tools**

.. code-block:: python

    def inspect_building_data(building_data):
        """Comprehensive building data inspection"""
        print("=== Building Data Inspection ===")
        
        # Check GeoJSON structure
        if 'type' in building_data:
            print(f"GeoJSON type: {building_data['type']}")
        
        # Check properties
        if 'properties' in building_data:
            props = building_data['properties']
            print(f"Properties keys: {list(props.keys())}")
            
            if 'buem' in props:
                buem_props = props['buem']
                print(f"BuEM properties: {list(buem_props.keys())}")
                
                if 'building_attributes' in buem_props:
                    attrs = buem_props['building_attributes']
                    print(f"Building attributes: {list(attrs.keys())}")
                    
                    # Check critical attributes
                    critical_attrs = ['coordinates', 'floor_area', 'building_type']
                    for attr in critical_attrs:
                        if attr in attrs:
                            print(f"  {attr}: {attrs[attr]}")
                        else:
                            print(f"  {attr}: MISSING")
        
        # Check geometry
        if 'geometry' in building_data:
            geom = building_data['geometry']
            print(f"Geometry type: {geom.get('type', 'Unknown')}")
            if 'coordinates' in geom:
                coords = geom['coordinates']
                print(f"Coordinate structure: {type(coords)}, length: {len(coords) if isinstance(coords, list) else 'N/A'}")

**API Testing Tools**

.. code-block:: python

    def test_api_endpoint(base_url="http://localhost:5000"):
        """Test API endpoint functionality"""
        import requests
        
        # Test health endpoint
        try:
            response = requests.get(f"{base_url}/health")
            print(f"Health check: {response.status_code}")
            if response.status_code == 200:
                print(f"Health response: {response.json()}")
        except Exception as e:
            print(f"Health check failed: {e}")
        
        # Test main API with simple building
        test_building = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {
                    "buem": {
                        "building_attributes": {
                            "coordinates": {"latitude": 46.5, "longitude": 6.6},
                            "floor_area": 100,
                            "building_type": "residential"
                        }
                    }
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]
                }
            }]
        }
        
        try:
            response = requests.post(
                f"{base_url}/api/geojson",
                json=test_building,
                headers={'Content-Type': 'application/json'}
            )
            print(f"API test: {response.status_code}")
            if response.status_code != 200:
                print(f"Error response: {response.text}")
            else:
                result = response.json()
                print(f"Successful analysis, features returned: {len(result.get('features', []))}")
        except Exception as e:
            print(f"API test failed: {e}")

Getting Help
-----------

**Information to Provide**

When seeking help, please provide:

1. **BuEM version**: ``python -c "import buem; print(buem.__version__)"``
2. **Python version**: ``python --version``
3. **Operating system**: Windows/Linux/macOS version
4. **Environment**: Conda/pip, virtual environment details
5. **Full error message**: Complete traceback
6. **Minimal example**: Smallest code that reproduces the issue
7. **Expected vs actual behavior**

**Debug Information Script**

.. code-block:: python

    def collect_debug_info():
        """Collect system and BuEM debug information"""
        import sys
        import platform
        import buem
        
        info = {
            'buem_version': buem.__version__,
            'python_version': sys.version,
            'platform': platform.platform(),
            'python_path': sys.path,
            'environment_variables': {
                k: v for k, v in os.environ.items() 
                if 'BUEM' in k or 'PYTHON' in k
            }
        }
        
        print("=== BuEM Debug Information ===")
        for key, value in info.items():
            print(f"{key}: {value}")
        
        return info

**Common Solutions Summary**

1. **Always activate the correct environment** before running BuEM
2. **Check file paths** are correct and files exist
3. **Validate input data** before processing
4. **Monitor resource usage** for performance issues
5. **Use logging** to trace execution flow
6. **Test with simple examples** before complex cases
7. **Check Docker volumes and ports** for container issues

For additional help, see :doc:`../api_integration/error_handling` and :doc:`../examples/error_handling_examples`.