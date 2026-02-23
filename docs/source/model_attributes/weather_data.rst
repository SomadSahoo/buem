Weather Data
============

Climate data requirements and weather file specifications for BuEM thermal modeling.

Required Weather Variables
-------------------------

**Temperature Data**

.. code-block:: json

    {
        "outdoor_temperature": {
            "variable": "dry_bulb_temperature",
            "unit": "celsius",
            "frequency": "hourly",
            "range": [-40, 50]
        }
    }

- **dry_bulb_temperature**: Primary temperature for heat transfer calculations
- **Unit**: Degrees Celsius
- **Frequency**: Hourly data required
- **Range**: Must be within realistic limits

**Solar Radiation**

.. code-block:: json

    {
        "solar_radiation": {
            "global_horizontal": "W/m²",
            "direct_normal": "W/m²",
            "diffuse_horizontal": "W/m²"
        }
    }

- **global_horizontal**: Total solar on horizontal surface
- **direct_normal**: Direct beam radiation
- **diffuse_horizontal**: Scattered solar radiation

**Humidity and Precipitation**

.. code-block:: json

    {
        "humidity": {
            "relative_humidity": "%",
            "specific_humidity": "kg/kg",
            "dew_point_temperature": "°C"
        },
        "precipitation": {
            "rainfall": "mm/h",
            "snowfall": "mm/h"
        }
    }

**Wind Conditions**

.. code-block:: json

    {
        "wind": {
            "wind_speed": "m/s",
            "wind_direction": "degrees",
            "wind_gusts": "m/s"
        }
    }

Weather File Formats
-------------------

**CSV Format (Primary)**

BuEM primarily uses CSV files with the following structure:

.. code-block:: csv

    datetime,temperature,humidity,solar_global,solar_direct,solar_diffuse,wind_speed,wind_direction
    2023-01-01 00:00:00,-2.5,85,0,0,0,3.2,245
    2023-01-01 01:00:00,-3.1,87,0,0,0,2.8,250
    2023-01-01 02:00:00,-3.8,89,0,0,0,2.5,255
    ...

**Required CSV Columns:**

- **datetime**: ISO format timestamp (YYYY-MM-DD HH:MM:SS)
- **temperature**: Dry bulb temperature (°C)
- **humidity**: Relative humidity (%)
- **solar_global**: Global horizontal irradiance (W/m²)
- **wind_speed**: Wind speed (m/s)

**Optional CSV Columns:**

- **solar_direct**: Direct normal irradiance (W/m²)
- **solar_diffuse**: Diffuse horizontal irradiance (W/m²)
- **wind_direction**: Wind direction (degrees)
- **pressure**: Atmospheric pressure (Pa)
- **precipitation**: Rainfall rate (mm/h)

**EPW Format Support**

BuEM can also read EnergyPlus Weather (EPW) files:

.. code-block:: python

    # EPW file conversion to CSV
    def convert_epw_to_csv(epw_file, csv_file):
        with open(epw_file, 'r') as f:
            lines = f.readlines()
        
        # Skip header lines (first 8 lines typically)
        weather_data = []
        for line in lines[8:]:
            fields = line.strip().split(',')
            # Extract required fields from EPW format
            datetime_str = f"{fields[0]}-{fields[1]:02d}-{fields[2]:02d} {fields[3]:02d}:00:00"
            temp = float(fields[6])  # Dry bulb temperature
            humidity = float(fields[8])  # Relative humidity
            # ... extract other variables

Geographic Considerations
------------------------

**Coordinate System**

Weather data must be associated with geographic coordinates:

.. code-block:: json

    {
        "weather_station": {
            "latitude": 46.5197,
            "longitude": 6.566,
            "elevation": 372,
            "time_zone": "Europe/Zurich"
        }
    }

- **elevation**: Meters above sea level (affects temperature and pressure)
- **time_zone**: For proper solar calculations

**Spatial Interpolation**

For buildings not co-located with weather stations:

.. code-block:: python

    def find_closest_weather_station(building_lat, building_lon, stations):
        """Find closest weather station to building location"""
        min_distance = float('inf')
        closest_station = None
        
        for station in stations:
            distance = haversine_distance(
                building_lat, building_lon,
                station['lat'], station['lon']
            )
            if distance < min_distance:
                min_distance = distance
                closest_station = station
        
        return closest_station, min_distance

**Elevation Adjustment**

Temperature corrections for elevation differences:

.. code-block:: python

    def adjust_temperature_for_elevation(temp_station, elev_station, elev_building):
        """Adjust temperature for elevation difference"""
        # Lapse rate: approximately 6.5°C per 1000m
        lapse_rate = -0.0065  # °C/m
        elevation_diff = elev_building - elev_station
        temp_adjusted = temp_station + (lapse_rate * elevation_diff)
        return temp_adjusted

Temporal Considerations
----------------------

**Time Zones and Solar Time**

.. code-block:: python

    def convert_to_solar_time(local_time, longitude, time_zone_offset):
        """Convert local time to solar time for solar calculations"""
        # Solar time correction
        equation_of_time = calculate_equation_of_time(local_time.dayofyear)
        longitude_correction = (longitude - time_zone_offset * 15) * 4  # minutes
        
        solar_time = local_time + timedelta(
            minutes=equation_of_time + longitude_correction
        )
        return solar_time

**Daylight Saving Time**

- Weather data should be in standard time (no DST)
- Building schedules may need DST adjustments
- Solar calculations require careful time handling

Data Quality and Validation
--------------------------

**Quality Checks**

.. code-block:: python

    def validate_weather_data(weather_df):
        """Validate weather data quality"""
        errors = []
        
        # Temperature range check
        if (weather_df['temperature'] < -50).any() or (weather_df['temperature'] > 60).any():
            errors.append("Temperature values outside realistic range")
        
        # Solar radiation physical limits
        if (weather_df['solar_global'] < 0).any() or (weather_df['solar_global'] > 1400).any():
            errors.append("Solar radiation values outside physical limits")
        
        # Humidity range check
        if (weather_df['humidity'] < 0).any() or (weather_df['humidity'] > 100).any():
            errors.append("Humidity values outside valid range")
        
        # Check for missing data
        if weather_df.isnull().any().any():
            errors.append("Missing data found in weather file")
        
        return errors

**Gap Filling**

For missing data points:

.. code-block:: python

    def fill_weather_gaps(weather_df):
        """Fill missing weather data using interpolation"""
        # Linear interpolation for short gaps (< 3 hours)
        weather_df.interpolate(method='linear', limit=2, inplace=True)
        
        # For longer gaps, use monthly averages
        weather_df['month'] = weather_df.index.month
        monthly_means = weather_df.groupby('month').mean()
        
        for column in ['temperature', 'humidity', 'solar_global']:
            mask = weather_df[column].isnull()
            weather_df.loc[mask, column] = weather_df.loc[mask, 'month'].map(
                monthly_means[column]
            )
        
        return weather_df

Example Weather File
-------------------

**Sample COSMO Weather Data**

BuEM includes sample weather data from COSMO meteorological model:

.. code-block:: text

    File: data/weather/COSMO_Year__ix_390_650.csv
    Location: Switzerland (latitude: 46.5197, longitude: 6.566)
    Period: Full meteorological year (8760 hours)
    Resolution: Hourly data
    Variables: Temperature, humidity, solar radiation, wind

**Data Source Information**

.. code-block:: json

    {
        "data_source": {
            "provider": "MeteoSwiss COSMO model",
            "spatial_resolution": "1.1 km",
            "temporal_resolution": "1 hour",
            "typical_meteorological_year": false,
            "measurement_height": {
                "temperature": "2 m",
                "wind_speed": "10 m"
            }
        }
    }

For weather data processing implementation, see :doc:`validation_rules`.