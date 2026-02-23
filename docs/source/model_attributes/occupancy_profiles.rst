Occupancy Profiles
==================

Occupancy patterns and internal heat gains from building use.

Occupancy Characteristics
------------------------

**Basic Occupancy Parameters**

.. code-block:: json

    {
        "occupant_count": 4,
        "occupancy_schedule": "residential_standard",
        "occupant_density": 0.033
    }

- **occupant_count**: Number of typical occupants
- **occupancy_schedule**: Predefined schedule type
- **occupant_density**: People per m² floor area

**Schedule Types**

.. list-table::
   :header-rows: 1

   * - Schedule Type
     - Description
     - Typical Use
   * - residential_standard
     - Standard home occupancy
     - Single family homes
   * - residential_multifamily
     - Apartment building pattern
     - Multi-family residential
   * - office_standard
     - 9-5 business hours
     - Office buildings
   * - retail
     - Shopping hours pattern
     - Commercial retail
   * - school
     - Educational schedule
     - Schools and universities
   * - hospital
     - 24/7 continuous use
     - Healthcare facilities

Internal Heat Gains
------------------

**Heat Gain Categories**

.. code-block:: json

    {
        "internal_gains": {
            "people": 75,
            "lighting": 5,
            "equipment": 8,
            "cooking": 12
        }
    }

**People Heat Gains**

- **Sensible heat**: 75 W per person (seated, light activity)
- **Latent heat**: 55 W per person (moisture)
- **Activity factors**: Adjust for different activity levels

.. list-table::
   :header-rows: 1

   * - Activity Level
     - Sensible (W/person)
     - Latent (W/person)
     - Total (W/person)
   * - Sleeping
     - 40
     - 25
     - 65
   * - Seated, quiet
     - 75
     - 55
     - 130
   * - Light work
     - 75
     - 75
     - 150
   * - Moderate activity
     - 75
     - 85
     - 160
   * - Heavy work
     - 115
     - 155
     - 270

**Lighting Heat Gains**

.. code-block:: json

    {
        "lighting": {
            "installed_power": 200,
            "lighting_schedule": "standard",
            "efficiency_type": "led"
        }
    }

- **installed_power**: Total lighting power (W)
- **lighting_schedule**: Usage pattern
- **efficiency_type**: "incandescent", "fluorescent", "led"

**Equipment Heat Gains**

.. code-block:: json

    {
        "equipment": {
            "office_equipment": 150,
            "kitchen_appliances": 800,
            "entertainment": 200,
            "other_plug_loads": 100
        }
    }

Daily Schedules
--------------

**Residential Standard Schedule**

.. code-block:: python

    # Hourly occupancy fractions (24 hours)
    residential_weekday = [
        1.0, 1.0, 1.0, 1.0, 1.0, 1.0,  # 00-05: Full occupancy (sleeping)
        0.8, 0.6, 0.3, 0.2, 0.2, 0.2,  # 06-11: Morning departure, low during day
        0.3, 0.2, 0.2, 0.2, 0.3, 0.5,  # 12-17: Lunch return, afternoon return starts
        0.7, 0.8, 0.9, 0.9, 1.0, 1.0   # 18-23: Evening return, full evening
    ]
    
    residential_weekend = [
        1.0, 1.0, 1.0, 1.0, 1.0, 1.0,  # 00-05: Full occupancy
        1.0, 0.9, 0.8, 0.7, 0.6, 0.5,  # 06-11: Gradual morning activity
        0.6, 0.6, 0.6, 0.6, 0.6, 0.7,  # 12-17: Variable afternoon
        0.8, 0.85, 0.9, 0.9, 1.0, 1.0  # 18-23: Evening gathering
    ]

**Commercial Office Schedule**

.. code-block:: python

    office_weekday = [
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0,  # 00-05: Empty
        0.1, 0.3, 0.8, 0.9, 0.95, 0.9, # 06-11: Arrival and morning work
        0.8, 0.95, 0.95, 0.9, 0.8, 0.5, # 12-17: Lunch dip, afternoon work
        0.3, 0.1, 0.05, 0.0, 0.0, 0.0  # 18-23: Departure
    ]
    
    office_weekend = [0.0] * 24  # Typically empty on weekends

Seasonal Variations
------------------

**Seasonal Occupancy Adjustments**

.. code-block:: json

    {
        "seasonal_adjustments": {
            "winter": 1.1,
            "spring": 1.0,
            "summer": 0.9,
            "autumn": 1.0
        }
    }

- **winter**: Higher occupancy during cold months
- **summer**: Reduced occupancy due to vacations
- **spring/autumn**: Baseline occupancy levels

**Holiday Adjustments**

.. code-block:: json

    {
        "holiday_schedule": {
            "christmas_week": 0.3,
            "summer_holidays": 0.7,
            "public_holidays": 0.5
        }
    }

Domestic Hot Water
-----------------

**DHW Consumption Patterns**

.. code-block:: json

    {
        "domestic_hot_water": {
            "daily_consumption": 150,
            "supply_temperature": 60,
            "mains_temperature": 10,
            "profile_type": "residential"
        }
    }

- **daily_consumption**: Liters per day
- **supply_temperature**: °C
- **mains_temperature**: °C (varies by season/location)
- **profile_type**: Usage pattern

**DHW Usage Schedule**

.. code-block:: python

    # Residential DHW hourly fractions
    dhw_residential = [
        0.01, 0.01, 0.01, 0.01, 0.01, 0.02,  # 00-05: Minimal use
        0.08, 0.15, 0.12, 0.05, 0.03, 0.04,  # 06-11: Morning peak
        0.06, 0.04, 0.03, 0.03, 0.04, 0.06,  # 12-17: Mid-day, afternoon
        0.08, 0.12, 0.15, 0.08, 0.04, 0.02   # 18-23: Evening peak
    ]

Stochastic Variations
--------------------

**Random Occupancy Modeling**

For detailed simulations, BuEM can apply stochastic variations:

.. code-block:: python

    # Add randomness to base schedules
    import numpy as np
    
    def apply_stochastic_variation(base_schedule, variation=0.2):
        """Apply random variation to occupancy schedule"""
        random_factors = np.random.normal(1.0, variation, len(base_schedule))
        varied_schedule = np.clip(base_schedule * random_factors, 0, 1)
        return varied_schedule

**Monte Carlo Occupancy**

- Multiple occupancy realizations for uncertainty analysis
- Accounts for real-world variability in building use
- Statistical distribution of energy consumption results

Validation Rules
---------------

**Occupancy Constraints**

- Occupant density must be realistic (0.005 - 1.0 people/m²)
- Heat gains must be physically reasonable
- Schedules must sum to reasonable daily totals

**Consistency Checks**

- Equipment loads appropriate for building type
- DHW consumption reasonable for occupancy
- Lighting power density within standards

For weather data specifications, see :doc:`weather_data`.