Integration Examples
====================

Complete examples demonstrating BuEM API integration in various scenarios.

Server Startup Examples
-----------------------

Starting the BuEM API Server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**With Conda Environment:**

.. code-block:: bash

    conda activate buem_env
    python -m src.buem.apis.api_server

**With PyPI Installation:**

.. code-block:: bash

    python -m buem.apis.api_server

**With Docker:**

.. code-block:: bash

    docker compose up

Example 1: Basic API Calls
--------------------------

**Health Check**

.. code-block:: bash

    curl http://localhost:5000/api/health

**Process GeoJSON File**

.. code-block:: bash

    curl -X POST "http://localhost:5000/api/process" \\
       -H "Content-Type: application/json" \\
       -d @src/buem/integration/json_schema/versions/v2/example_request.json

**Run Building Model**

.. code-block:: bash

    curl -X POST "http://localhost:5000/api/run?include_timeseries=true" \\
       -H "Content-Type: application/json" \\
       --data-binary @payload.json

Example 2: Postman Integration
-----------------------------

**Setup Steps:**

1. Create a new request in Postman
2. Set URL to ``http://localhost:5000/api/process``
3. Method: ``POST``
4. Headers: ``Content-Type: application/json``
5. Body:

   - For GeoJSON: Choose ``binary`` and upload GeoJSON file
   - For JSON config: Choose ``raw`` → ``JSON`` and paste the configuration
6. Optional: Add ``?include_timeseries=true`` for full time series
7. Send request and inspect JSON response

Example 3: Python Helper Tool
-----------------------------

BUEM includes a Python helper for testing:

.. code-block:: bash

    python -m src.buem.integration.send_geojson.py \\
        src/buem/integration/sample_request_template.geojson \\
        --include-timeseries

Example 4: Result Forwarding
----------------------------

Include a ``forward_url`` in your JSON payload to automatically send results to another service:

.. code-block:: json

    {
       "forward_url": "https://example.com/receiver",
       "include_timeseries": false,
       "use_milp": false,
       "building_attributes": {
           "latitude": 52.0,
           "longitude": 5.0,
           ...
       }
    }

Example 5: File Downloads
-------------------------

Download saved result files (large time series data):

.. code-block:: bash

    # Files are saved with pattern: buem_ts_<hex>.json.gz
    curl -O http://localhost:5000/api/files/buem_ts_abc123def.json.gz

Environment Configuration
------------------------

**Environment Variables:**

- ``BUEM_LOG_FILE`` - Log file path (default: ``logs/buem_api.log``)
- ``BUEM_RESULTS_DIR`` - Results directory (default: ``results/``)

**Troubleshooting:**

- If logs aren't visible, set ``BUEM_LOG_FILE`` to a writable path
- Ensure ``BUEM_RESULTS_DIR`` exists for file downloads
- Server binds to ``0.0.0.0:5000`` by default

Example 6: Basic Building Analysis
----------------------------------

**Python Client Example**

.. code-block:: python

    import requests
    import json
    
    def analyze_single_building():
        """Analyze a single building and print results."""
        
        # Define building data
        building_request = {
            "type": "FeatureCollection", 
            "features": [{
                "type": "Feature",
                "id": "B001",
                "geometry": {"type": "Point", "coordinates": [5.0, 52.0]},
                "properties": {
                    "buem": {
                        "building_attributes": {
                            "latitude": 52.0,
                            "longitude": 5.0,
                            "A_ref": 150.0,
                            "h_room": 2.7,
                            "components": {
                                "Walls": {
                                    "U": 1.2,
                                    "elements": [
                                        {"id": "Wall_N", "area": 40.0, "azimuth": 0.0, "tilt": 90.0},
                                        {"id": "Wall_S", "area": 40.0, "azimuth": 180.0, "tilt": 90.0},
                                        {"id": "Wall_E", "area": 30.0, "azimuth": 90.0, "tilt": 90.0},
                                        {"id": "Wall_W", "area": 30.0, "azimuth": 270.0, "tilt": 90.0}
                                    ]
                                },
                                "Roof": {
                                    "U": 0.8,
                                    "elements": [
                                        {"id": "Roof_1", "area": 150.0, "azimuth": 180.0, "tilt": 30.0}
                                    ]
                                },
                                "Floor": {
                                    "U": 1.5,
                                    "elements": [
                                        {"id": "Floor_1", "area": 150.0, "azimuth": 180.0, "tilt": 90.0}
                                    ]
                                },
                                "Windows": {
                                    "U": 2.8,
                                    "g_gl": 0.6,
                                    "elements": [
                                        {"id": "Win_S", "area": 12.0, "surface": "Wall_S", "azimuth": 180.0, "tilt": 90.0},
                                        {"id": "Win_N", "area": 6.0, "surface": "Wall_N", "azimuth": 0.0, "tilt": 90.0}
                                    ]
                                },
                                "Ventilation": {
                                    "elements": [
                                        {"id": "Vent_1", "air_changes": 0.4}
                                    ]
                                }
                            }
                        }
                    }
                }
            }]
        }
        
        # Submit request
        try:
            response = requests.post(
                'http://localhost:5000/api/geojson',
                json=building_request,
                timeout=30
            )
            response.raise_for_status()
            
            # Parse results
            results = response.json()
            feature = results['features'][0]
            thermal_profile = feature['properties']['buem']['thermal_load_profile']
            
            # Display results
            print(f"Building Analysis Results for {feature['id']}:")
            print(f"  Heating Demand: {thermal_profile['heating_total_kWh']:.0f} kWh/year")
            print(f"  Cooling Demand: {thermal_profile['cooling_total_kWh']:.0f} kWh/year")
            print(f"  Peak Heating: {thermal_profile['heating_peak_kW']:.1f} kW")
            print(f"  Peak Cooling: {thermal_profile['cooling_peak_kW']:.1f} kW")
            print(f"  Electricity: {thermal_profile['electricity_total_kWh']:.0f} kWh/year")
            print(f"  Processing Time: {thermal_profile['elapsed_s']:.2f} seconds")
            
            return thermal_profile
            
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return None
        except KeyError as e:
            print(f"Unexpected response format: {e}")
            return None
    
    if __name__ == '__main__':
        analyze_single_building()

Example 2: Batch Processing Multiple Buildings
----------------------------------------------

.. code-block:: python

    import requests
    import json
    import time
    from typing import List, Dict
    
    def create_building_variants() -> List[Dict]:
        """Create multiple building variants for analysis."""
        
        base_building = {
            "geometry": {"type": "Point", "coordinates": [5.0, 52.0]},
            "properties": {
                "buem": {
                    "building_attributes": {
                        "latitude": 52.0,
                        "longitude": 5.0,
                        "A_ref": 100.0,
                        "components": {
                            "Walls": {"U": 1.5, "elements": [{"id": "Wall_1", "area": 80.0, "azimuth": 180.0, "tilt": 90.0}]},
                            "Roof": {"U": 1.0, "elements": [{"id": "Roof_1", "area": 100.0, "azimuth": 180.0, "tilt": 30.0}]},
                            "Ventilation": {"elements": [{"id": "Vent_1", "air_changes": 0.5}]}
                        }
                    }
                }
            }
        }
        
        # Create variants with different U-values
        buildings = []
        u_values = [0.5, 1.0, 1.5, 2.0, 2.5]  # Different insulation levels
        
        for i, u_val in enumerate(u_values):
            building = json.loads(json.dumps(base_building))  # Deep copy
            building['type'] = 'Feature'
            building['id'] = f'Building_{i+1:02d}_U{u_val}'
            building['properties']['buem']['building_attributes']['components']['Walls']['U'] = u_val
            building['properties']['buem']['building_attributes']['components']['Roof']['U'] = u_val * 0.7  # Roof typically better insulated
            buildings.append(building)
        
        return buildings
    
    def batch_analyze_buildings():
        """Analyze multiple buildings in a single request."""
        
        buildings = create_building_variants()
        
        batch_request = {
            "type": "FeatureCollection",
            "features": buildings
        }
        
        print(f"Analyzing {len(buildings)} building variants...")
        start_time = time.time()
        
        try:
            response = requests.post(
                'http://localhost:5000/api/geojson',
                json=batch_request,
                timeout=120  # Longer timeout for batch processing
            )
            response.raise_for_status()
            
            results = response.json()
            elapsed_time = time.time() - start_time
            
            print(f"\nBatch processing completed in {elapsed_time:.1f} seconds")
            print(f"Average time per building: {elapsed_time/len(buildings):.2f} seconds\n")
            
            # Analyze results
            print("Results Summary:")
            print(f"{'Building ID':<15} {'Wall U':<8} {'Heating':<10} {'Cooling':<10} {'Total':<10}")
            print("-" * 60)
            
            for feature in results['features']:
                building_id = feature['id']
                if 'error' in feature['properties']['buem']:
                    print(f"{building_id:<15} ERROR: {feature['properties']['buem']['error']}")
                    continue
                
                thermal = feature['properties']['buem']['thermal_load_profile']
                wall_u = feature['properties']['buem']['building_attributes']['components']['Walls']['U']
                
                heating = thermal['heating_total_kWh']
                cooling = thermal['cooling_total_kWh'] 
                total = heating + cooling
                
                print(f"{building_id:<15} {wall_u:<8.1f} {heating:<10.0f} {cooling:<10.0f} {total:<10.0f}")
            
            return results
            
        except requests.exceptions.RequestException as e:
            print(f"Batch request failed: {e}")
            return None
    
    if __name__ == '__main__':
        batch_analyze_buildings()

Example 3: Timeseries Data Processing
-------------------------------------

.. code-block:: python

    import requests
    import json
    import gzip
    import pandas as pd
    import matplotlib.pyplot as plt
    
    def analyze_with_timeseries():
        """Request and process detailed timeseries data."""
        
        building_request = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "id": "TimeSeries_Example",
                "geometry": {"type": "Point", "coordinates": [5.0, 52.0]},
                "properties": {
                    "buem": {
                        "building_attributes": {
                            "latitude": 52.0,
                            "longitude": 5.0,
                            "A_ref": 200.0,
                            "components": {
                                "Walls": {"U": 1.0, "elements": [{"id": "Wall_1", "area": 120.0, "azimuth": 180.0, "tilt": 90.0}]},
                                "Roof": {"U": 0.6, "elements": [{"id": "Roof_1", "area": 200.0, "azimuth": 180.0, "tilt": 30.0}]},
                                "Windows": {"U": 2.5, "g_gl": 0.6, "elements": [{"id": "Win_1", "area": 25.0, "surface": "Wall_1", "azimuth": 180.0, "tilt": 90.0}]},
                                "Ventilation": {"elements": [{"id": "Vent_1", "air_changes": 0.3}]}
                            }
                        }
                    }
                }
            }]
        }
        
        # Request with timeseries data
        print("Requesting analysis with timeseries data...")
        response = requests.post(
            'http://localhost:5000/api/geojson',
            params={'include_timeseries': 'true'},
            json=building_request,
            timeout=60
        )
        
        if response.status_code != 200:
            print(f"Request failed: {response.status_code} - {response.text}")
            return
        
        results = response.json()
        thermal = results['features'][0]['properties']['buem']['thermal_load_profile']
        
        # Download timeseries file
        if 'timeseries_file' in thermal:
            timeseries_url = f"http://localhost:5000{thermal['timeseries_file']}"
            print(f"Downloading timeseries data from {timeseries_url}")
            
            ts_response = requests.get(timeseries_url)
            if ts_response.status_code == 200:
                # Decompress and parse JSON
                timeseries_data = json.loads(gzip.decompress(ts_response.content).decode('utf-8'))
                
                # Convert to pandas DataFrame
                df = pd.DataFrame({
                    'datetime': pd.to_datetime(timeseries_data['index']),
                    'heating': timeseries_data['heat'],
                    'cooling': [-x for x in timeseries_data['cool']],  # Convert to positive values
                    'electricity': timeseries_data['electricity']
                })
                df.set_index('datetime', inplace=True)
                
                # Analyze timeseries
                print(f"\nTimeseries Analysis ({len(df)} hourly points):")
                print(f"  Date range: {df.index.min()} to {df.index.max()}")
                print(f"  Peak heating: {df['heating'].max():.1f} kW")
                print(f"  Peak cooling: {df['cooling'].max():.1f} kW")
                print(f"  Average heating: {df['heating'].mean():.2f} kW")
                print(f"  Average cooling: {df['cooling'].mean():.2f} kW")
                
                # Monthly aggregation
                monthly = df.resample('M').agg({
                    'heating': 'sum',
                    'cooling': 'sum', 
                    'electricity': 'sum'
                })
                
                print("\nMonthly Energy Consumption (kWh):")
                print(monthly.round(0))
                
                # Optional: Create plots
                create_energy_plots(df, monthly, thermal)
                
                return df, thermal
            else:
                print(f"Failed to download timeseries: {ts_response.status_code}")
        else:
            print("No timeseries data available")
    
    def create_energy_plots(df, monthly, thermal):
        """Create visualization plots for energy data."""
        try:
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle('BuEM Energy Analysis Results', fontsize=16)
            
            # Daily average profiles
            daily_avg = df.groupby(df.index.hour).mean()
            axes[0, 0].plot(daily_avg.index, daily_avg['heating'], label='Heating', color='red')
            axes[0, 0].plot(daily_avg.index, daily_avg['cooling'], label='Cooling', color='blue')
            axes[0, 0].plot(daily_avg.index, daily_avg['electricity'], label='Electricity', color='green')
            axes[0, 0].set_xlabel('Hour of Day')
            axes[0, 0].set_ylabel('Power (kW)')
            axes[0, 0].set_title('Average Daily Load Profiles')
            axes[0, 0].legend()
            axes[0, 0].grid(True)
            
            # Monthly consumption
            x_pos = range(len(monthly))
            width = 0.25
            axes[0, 1].bar([x - width for x in x_pos], monthly['heating'], width, label='Heating', color='red', alpha=0.7)
            axes[0, 1].bar(x_pos, monthly['cooling'], width, label='Cooling', color='blue', alpha=0.7)
            axes[0, 1].bar([x + width for x in x_pos], monthly['electricity'], width, label='Electricity', color='green', alpha=0.7)
            axes[0, 1].set_xlabel('Month')
            axes[0, 1].set_ylabel('Energy (kWh)')
            axes[0, 1].set_title('Monthly Energy Consumption')
            axes[0, 1].set_xticks(x_pos)
            axes[0, 1].set_xticklabels([d.strftime('%b') for d in monthly.index])
            axes[0, 1].legend()
            axes[0, 1].grid(True, alpha=0.3)
            
            # Weekly pattern (sample week)
            sample_week = df.iloc[0:168]  # First week
            axes[1, 0].plot(sample_week.index, sample_week['heating'], label='Heating', alpha=0.8)
            axes[1, 0].plot(sample_week.index, sample_week['cooling'], label='Cooling', alpha=0.8)
            axes[1, 0].set_xlabel('Date/Time')
            axes[1, 0].set_ylabel('Power (kW)')
            axes[1, 0].set_title('Sample Week Load Pattern')
            axes[1, 0].legend()
            axes[1, 0].grid(True)
            axes[1, 0].xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            
            # Summary statistics
            summary_text = f"""
            Annual Summary:
            
            Heating: {thermal['heating_total_kWh']:.0f} kWh
            Cooling: {thermal['cooling_total_kWh']:.0f} kWh
            Electricity: {thermal['electricity_total_kWh']:.0f} kWh
            
            Peak Heating: {thermal['heating_peak_kW']:.1f} kW
            Peak Cooling: {thermal['cooling_peak_kW']:.1f} kW
            
            Processing: {thermal['elapsed_s']:.2f} sec
            """
            axes[1, 1].text(0.1, 0.9, summary_text, transform=axes[1, 1].transAxes, 
                           verticalalignment='top', fontfamily='monospace')
            axes[1, 1].set_xlim(0, 1)
            axes[1, 1].set_ylim(0, 1)
            axes[1, 1].set_title('Analysis Summary')
            axes[1, 1].axis('off')
            
            plt.tight_layout()
            plt.savefig('buem_analysis_results.png', dpi=300, bbox_inches='tight')
            plt.show()
            
            print("\nPlots saved as 'buem_analysis_results.png'")
            
        except ImportError:
            print("Matplotlib not available - skipping plots")
        except Exception as e:
            print(f"Error creating plots: {e}")
    
    if __name__ == '__main__':
        analyze_with_timeseries()

Example 4: Error Handling and Robustness
----------------------------------------

.. code-block:: python

    import requests
    import json
    import time
    from typing import Optional, Dict, List
    import logging
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    class BuEMAPIError(Exception):
        """Custom exception for BuEM API errors"""
        def __init__(self, message, status_code=None, response_data=None):
            super().__init__(message)
            self.status_code = status_code
            self.response_data = response_data
    
    class RobustBuEMClient:
        """Production-ready BuEM client with comprehensive error handling"""
        
        def __init__(self, base_url: str, timeout: int = 30, max_retries: int = 3):
            self.base_url = base_url.rstrip('/')
            self.timeout = timeout
            self.max_retries = max_retries
            self.session = requests.Session()
            
        def analyze_buildings(self, features: List[Dict], include_timeseries: bool = False) -> Dict:
            """Analyze buildings with robust error handling and retries"""
            
            # Validate input
            self._validate_features(features)
            
            request_data = {
                "type": "FeatureCollection",
                "features": features
            }
            
            # Attempt with retries
            for attempt in range(self.max_retries + 1):
                try:
                    response = self._make_request(request_data, include_timeseries, attempt)
                    return self._process_response(response)
                    
                except requests.exceptions.Timeout:
                    if attempt < self.max_retries:
                        wait_time = 2 ** attempt
                        logger.warning(f"Request timeout, retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries + 1})")
                        time.sleep(wait_time)
                    else:
                        raise BuEMAPIError("Request timed out after all retry attempts")
                        
                except requests.exceptions.ConnectionError: 
                    if attempt < self.max_retries:
                        wait_time = 2 ** attempt
                        logger.warning(f"Connection error, retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries + 1})")
                        time.sleep(wait_time)
                    else:
                        raise BuEMAPIError("Could not connect to BuEM API after all retry attempts")
                        
                except BuEMAPIError:
                    # Don't retry on API-specific errors (400-level errors)
                    raise
                    
                except Exception as e:
                    if attempt < self.max_retries:
                        wait_time = 2 ** attempt
                        logger.warning(f"Unexpected error: {e}, retrying in {wait_time}s")
                        time.sleep(wait_time)
                    else:
                        raise BuEMAPIError(f"Unexpected error: {e}")
            
        def _validate_features(self, features: List[Dict]):
            """Validate feature structure before sending"""
            if not features:
                raise BuEMAPIError("No features provided")
                
            for i, feature in enumerate(features):
                try:
                    # Check basic structure
                    if 'type' not in feature or feature['type'] != 'Feature':
                        raise BuEMAPIError(f"Feature {i}: Invalid type, must be 'Feature'")
                    
                    if 'id' not in feature:
                        raise BuEMAPIError(f"Feature {i}: Missing required 'id' field")
                    
                    # Check building attributes
                    props = feature.get('properties', {})
                    buem = props.get('buem', {})
                    attrs = buem.get('building_attributes', {})
                    
                    if not attrs:
                        raise BuEMAPIError(f"Feature {feature['id']}: Missing building_attributes")
                    
                    # Check required attributes
                    required = ['latitude', 'longitude', 'components']
                    for req in required:
                        if req not in attrs:
                            raise BuEMAPIError(f"Feature {feature['id']}: Missing required attribute '{req}'")
                    
                    # Validate coordinates
                    lat, lon = attrs['latitude'], attrs['longitude']
                    if not (-90 <= lat <= 90):
                        raise BuEMAPIError(f"Feature {feature['id']}: Invalid latitude {lat}")
                    if not (-180 <= lon <= 180):
                        raise BuEMAPIError(f"Feature {feature['id']}: Invalid longitude {lon}")
                        
                except KeyError as e:
                    raise BuEMAPIError(f"Feature {i}: Missing required field {e}")
                    
        def _make_request(self, request_data: Dict, include_timeseries: bool, attempt: int) -> requests.Response:
            """Make the actual HTTP request"""
            url = f'{self.base_url}/api/geojson'
            params = {'include_timeseries': include_timeseries} if include_timeseries else {}
            
            # Longer timeout for larger requests
            timeout = self.timeout + len(request_data['features']) * 2
            
            logger.info(f"Sending request to {url} (attempt {attempt + 1}, {len(request_data['features'])} buildings, timeout={timeout}s)")
            
            response = self.session.post(
                url,
                json=request_data,
                params=params,
                timeout=timeout
            )
            
            return response
            
        def _process_response(self, response: requests.Response) -> Dict:
            """Process and validate API response"""
            
            # Handle HTTP errors
            if response.status_code == 400:
                error_data = response.json().get('error', {}) if response.content else {}
                raise BuEMAPIError(
                    f"Bad request: {error_data.get('message', 'Invalid request format')}",
                    status_code=400,
                    response_data=error_data
                )
            elif response.status_code == 422:
                error_data = response.json().get('error', {}) if response.content else {}
                details = error_data.get('details', [])
                error_msg = f"Validation failed: {error_data.get('message', 'Unknown validation error')}"
                if details:
                    error_msg += f"\nDetails: {'; '.join(details)}"
                raise BuEMAPIError(error_msg, status_code=422, response_data=error_data)
            elif response.status_code == 500:
                raise BuEMAPIError("Internal server error - check server logs", status_code=500)
            elif response.status_code != 200:
                raise BuEMAPIError(f"Unexpected status code: {response.status_code}", status_code=response.status_code)
            
            # Parse JSON response
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                raise BuEMAPIError(f"Invalid JSON response: {e}")
            
            # Validate response structure
            if 'type' not in data or data['type'] != 'FeatureCollection':
                raise BuEMAPIError("Invalid response format: expected FeatureCollection")
            
            if 'features' not in data:
                raise BuEMAPIError("Invalid response format: missing features")
            
            # Check for feature-level errors
            error_features = []
            for feature in data['features']:
                buem_data = feature.get('properties', {}).get('buem', {})
                if 'error' in buem_data:
                    error_features.append({
                        'id': feature.get('id', 'unknown'),
                        'error': buem_data['error']
                    })
            
            if error_features:
                logger.warning(f"Some features failed processing: {error_features}")
                # Could choose to raise exception or just log warnings
                # raise BuEMAPIError(f"Features failed processing: {error_features}")
            
            logger.info(f"Successfully processed {len(data['features'])} features")
            return data
            
        def download_timeseries(self, timeseries_url: str) -> Optional[Dict]:
            """Download and process timeseries data with error handling"""
            try:
                response = self.session.get(f'{self.base_url}{timeseries_url}', timeout=self.timeout)
                
                if response.status_code == 404:
                    logger.error(f"Timeseries file not found: {timeseries_url}")
                    return None
                elif response.status_code != 200:
                    logger.error(f"Failed to download timeseries: {response.status_code}")
                    return None
                
                # Decompress and parse
                import gzip
                import json
                
                timeseries_data = json.loads(gzip.decompress(response.content).decode('utf-8'))
                
                # Validate structure
                required_keys = ['index', 'heat', 'cool', 'electricity']
                for key in required_keys:
                    if key not in timeseries_data:
                        raise BuEMAPIError(f"Invalid timeseries format: missing '{key}'")
                
                logger.info(f"Downloaded timeseries with {len(timeseries_data['index'])} data points")
                return timeseries_data
                
            except Exception as e:
                logger.error(f"Error downloading timeseries: {e}")
                return None
    
    def robust_analysis_example():
        """Example using the robust client"""
        
        client = RobustBuEMClient('http://localhost:5000', timeout=60, max_retries=2)
        
        # Create test buildings with some invalid data for testing error handling
        buildings = [
            {
                "type": "Feature",
                "id": "ValidBuilding",
                "properties": {
                    "buem": {
                        "building_attributes": {
                            "latitude": 52.0,
                            "longitude": 5.0,
                            "A_ref": 100.0,
                            "components": {
                                "Walls": {"U": 1.5, "elements": [{"id": "Wall_1", "area": 80.0, "azimuth": 180.0, "tilt": 90.0}]},
                                "Ventilation": {"elements": [{"id": "Vent_1", "air_changes": 0.5}]}
                            }
                        }
                    }
                }
            },
            # Intentionally invalid building to test error handling
            {
                "type": "Feature", 
                "id": "InvalidBuilding",
                "properties": {
                    "buem": {
                        "building_attributes": {
                            "latitude": 95.0,  # Invalid latitude
                            "longitude": 5.0,
                            "components": {}
                        }
                    }
                }
            }
        ]
        
        try:
            logger.info("Starting robust analysis...")
            results = client.analyze_buildings(buildings, include_timeseries=True)
            
            for feature in results['features']:
                building_id = feature['id']
                buem_data = feature['properties']['buem']
                
                if 'error' in buem_data:
                    logger.error(f"Building {building_id} failed: {buem_data['error']}")
                else:
                    thermal = buem_data['thermal_load_profile']
                    logger.info(f"Building {building_id}: {thermal['heating_total_kWh']:.0f} kWh heating, {thermal['cooling_total_kWh']:.0f} kWh cooling")
                    
                    # Download timeseries if available
                    if 'timeseries_file' in thermal:
                        timeseries = client.download_timeseries(thermal['timeseries_file'])
                        if timeseries:
                            logger.info(f"Downloaded timeseries with {len(timeseries['index'])} points")
            
        except BuEMAPIError as e:
            logger.error(f"BuEM API Error: {e}")
            if e.response_data:
                logger.error(f"Error details: {e.response_data}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
    
    if __name__ == '__main__':
        robust_analysis_example()

Next Steps
----------

The examples above demonstrate:

- Basic single building analysis
- Batch processing multiple buildings  
- Timeseries data handling and visualization
- Production-ready error handling and robustness

For more specific integration patterns, see :doc:`../technical/index` for architectural guidance.