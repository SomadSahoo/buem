Implementation Details
======================

Detailed implementation information for BuEM components.

Building Attribute Validation
-----------------------------

The validation system uses a hierarchical approach with JSON-based configuration:

.. code-block:: python

    # cfg_attribute.py
    class AttributeValidator:
        def __init__(self, config_file):
            with open(config_file) as f:
                self.rules = json.load(f)
        
        def validate_building(self, building_data):
            errors = []
            attributes = building_data.get('properties', {}).get('buem', {})
            
            for attr_name, attr_rules in self.rules.items():
                if self._is_required(attr_rules) and attr_name not in attributes:
                    errors.append(f"Missing required attribute: {attr_name}")
                
                if attr_name in attributes:
                    value = attributes[attr_name]
                    attr_errors = self._validate_attribute(attr_name, value, attr_rules)
                    errors.extend(attr_errors)
            
            return errors

**Configuration Structure:**

.. code-block:: json

    {
        "coordinates": {
            "required": true,
            "type": "object",
            "properties": {
                "latitude": {
                    "type": "number",
                    "minimum": -90,
                    "maximum": 90
                },
                "longitude": {
                    "type": "number", 
                    "minimum": -180,
                    "maximum": 180
                }
            }
        },
        "building_type": {
            "required": true,
            "type": "string",
            "enum": ["residential", "commercial", "industrial"]
        }
    }

Weather Data Processing
-----------------------

**CSV Data Loading:**

.. code-block:: python

    # weather/from_csv.py
    class WeatherDataLoader:
        def __init__(self, data_dir):
            self.data_dir = Path(data_dir)
            self.cache = {}
        
        def load_weather_data(self, lat, lon, start_date, end_date):
            # Find closest weather station
            station_file = self._find_closest_station(lat, lon)
            
            # Load and interpolate data
            cache_key = f"{station_file}_{start_date}_{end_date}"
            if cache_key not in self.cache:
                df = pd.read_csv(self.data_dir / station_file)
                df['datetime'] = pd.to_datetime(df['datetime'])
                
                # Filter by date range
                mask = (df['datetime'] >= start_date) & (df['datetime'] <= end_date)
                filtered_data = df.loc[mask]
                
                self.cache[cache_key] = filtered_data
            
            return self.cache[cache_key]
        
        def _find_closest_station(self, lat, lon):
            # Implement geographic distance calculation
            min_distance = float('inf')
            closest_station = None
            
            for station_file in self.data_dir.glob('*.csv'):
                station_coords = self._extract_coordinates(station_file)
                distance = self._haversine_distance(lat, lon, *station_coords)
                
                if distance < min_distance:
                    min_distance = distance
                    closest_station = station_file.name
            
            return closest_station

Thermal Model Implementation
----------------------------

**Building Heat Transfer:**

.. code-block:: python

    # thermal/model_buem.py
    class ThermalModel:
        def __init__(self, building_attrs, weather_data):
            self.building = building_attrs
            self.weather = weather_data
            self.thermal_mass = self._calculate_thermal_mass()
        
        def calculate_heating_demand(self, time_series):
            heating_demand = []
            
            for timestamp in time_series:
                # Indoor-outdoor temperature difference
                T_out = self.weather.get_temperature(timestamp)
                T_in = 20.0  # Assumed indoor setpoint
                dT = T_in - T_out
                
                # Heat loss through building envelope
                if dT > 0:  # Heating required
                    # Transmission losses
                    Q_transmission = self._calculate_transmission_losses(dT)
                    
                    # Ventilation losses
                    Q_ventilation = self._calculate_ventilation_losses(dT)
                    
                    # Internal gains reduction
                    Q_internal = self._calculate_internal_gains(timestamp)
                    
                    # Net heating demand
                    Q_heating = max(0, Q_transmission + Q_ventilation - Q_internal)
                    heating_demand.append(Q_heating)
                else:
                    heating_demand.append(0.0)
            
            return heating_demand
        
        def _calculate_transmission_losses(self, dT):
            # U-value based calculation
            wall_area = self.building.get('wall_area', 100)
            roof_area = self.building.get('roof_area', 50)
            window_area = self.building.get('window_area', 20)
            
            U_wall = self.building.get('u_value_wall', 0.3)
            U_roof = self.building.get('u_value_roof', 0.2)
            U_window = self.building.get('u_value_window', 1.5)
            
            Q_transmission = (
                wall_area * U_wall * dT +
                roof_area * U_roof * dT +
                window_area * U_window * dT
            )
            
            return Q_transmission

Occupancy Pattern Generation
----------------------------

**Stochastic Occupancy Modeling:**

.. code-block:: python

    # occupancy/occupancy_profile.py
    class OccupancyProfile:
        def __init__(self, building_type, occupant_count):
            self.building_type = building_type
            self.occupant_count = occupant_count
            self.base_profiles = self._load_base_profiles()
        
        def generate_profile(self, start_date, end_date):
            date_range = pd.date_range(start=start_date, end=end_date, freq='H')
            occupancy_profile = []
            
            for timestamp in date_range:
                hour = timestamp.hour
                day_of_week = timestamp.dayofweek  # Monday = 0, Sunday = 6
                
                # Base occupancy probability
                if day_of_week < 5:  # Weekday
                    base_prob = self.base_profiles['weekday'][hour]
                else:  # Weekend
                    base_prob = self.base_profiles['weekend'][hour]
                
                # Add stochastic variation
                variation = np.random.normal(0, 0.1)  # 10% standard deviation
                final_prob = np.clip(base_prob + variation, 0, 1)
                
                # Calculate actual occupancy
                occupancy = int(self.occupant_count * final_prob)
                occupancy_profile.append(occupancy)
            
            return occupancy_profile
        
        def _load_base_profiles(self):
            # Residential profile example
            if self.building_type == 'residential':
                return {
                    'weekday': {
                        0: 0.95, 1: 0.95, 2: 0.95, 3: 0.95, 4: 0.95, 5: 0.95,
                        6: 0.8, 7: 0.6, 8: 0.3, 9: 0.2, 10: 0.2, 11: 0.2,
                        12: 0.3, 13: 0.2, 14: 0.2, 15: 0.2, 16: 0.3, 17: 0.5,
                        18: 0.7, 19: 0.8, 20: 0.9, 21: 0.9, 22: 0.95, 23: 0.95
                    },
                    'weekend': {
                        0: 0.95, 1: 0.95, 2: 0.95, 3: 0.95, 4: 0.95, 5: 0.95,
                        6: 0.95, 7: 0.9, 8: 0.8, 9: 0.7, 10: 0.6, 11: 0.5,
                        12: 0.6, 13: 0.6, 14: 0.6, 15: 0.6, 16: 0.6, 17: 0.7,
                        18: 0.8, 19: 0.85, 20: 0.9, 21: 0.9, 22: 0.95, 23: 0.95
                    }
                }

Technology Performance Modeling
-------------------------------

**Heat Pump Performance:**

.. code-block:: python

    # technology/new/heatpump.py
    class HeatPump:
        def __init__(self, nominal_capacity, nominal_cop):
            self.nominal_capacity = nominal_capacity  # kW
            self.nominal_cop = nominal_cop
        
        def calculate_performance(self, T_outside, heat_demand):
            # Temperature-dependent COP calculation
            # COP decreases with decreasing outdoor temperature
            cop_temp_factor = 1 - 0.02 * max(0, 7 - T_outside)  # 2% per degree below 7°C
            actual_cop = self.nominal_cop * cop_temp_factor
            
            # Part-load performance adjustment
            if heat_demand < self.nominal_capacity:
                load_ratio = heat_demand / self.nominal_capacity
                # Part-load efficiency curve (quadratic approximation)
                part_load_factor = 0.1 + 0.9 * load_ratio - 0.2 * (1 - load_ratio) ** 2
                actual_cop *= part_load_factor
            
            # Calculate electricity consumption
            if heat_demand > 0:
                electricity_consumption = heat_demand / actual_cop
            else:
                electricity_consumption = 0
            
            return {
                'heat_output': min(heat_demand, self.nominal_capacity),
                'electricity_input': electricity_consumption,
                'cop': actual_cop,
                'efficiency': actual_cop / self.nominal_cop
            }

Error Handling and Logging
--------------------------

**Structured Error Handling:**

.. code-block:: python

    # Error handling in API endpoints
    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        logger.warning(f"Validation error: {error.message}", extra={
            'error_type': 'validation',
            'field_errors': error.field_errors,
            'request_id': request.headers.get('X-Request-ID')
        })
        
        return {
            'error': {
                'type': 'validation_error',
                'message': error.message,
                'details': error.field_errors
            }
        }, 422
    
    @app.errorhandler(Exception)
    def handle_general_error(error):
        logger.error(f"Unexpected error: {str(error)}", extra={
            'error_type': 'internal',
            'traceback': traceback.format_exc(),
            'request_id': request.headers.get('X-Request-ID')
        })
        
        return {
            'error': {
                'type': 'internal_error',
                'message': 'An unexpected error occurred'
            }
        }, 500

For more technical details, see :doc:`performance` and :doc:`../api_integration/advanced_usage`.