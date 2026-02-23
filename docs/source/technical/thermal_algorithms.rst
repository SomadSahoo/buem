Thermal Algorithms
==================

Detailed thermal calculation algorithms implemented in BuEM.

Heat Transfer Fundamentals
-------------------------

**Steady-State Heat Transfer**

BuEM uses established heat transfer principles:

.. math::

   Q = U \cdot A \cdot \Delta T

Where:
- :math:`Q` = Heat transfer rate (W)
- :math:`U` = Overall heat transfer coefficient (W/m²·K)
- :math:`A` = Surface area (m²)
- :math:`\Delta T` = Temperature difference (K)

**Multi-Layer Heat Transfer**

For composite building elements:

.. math::

   \frac{1}{U} = \frac{1}{h_i} + \sum_{n=1}^{N} \frac{t_n}{\lambda_n} + \frac{1}{h_o}

Where:
- :math:`h_i, h_o` = Internal and external surface heat transfer coefficients
- :math:`t_n` = Thickness of layer n
- :math:`\lambda_n` = Thermal conductivity of layer n

Building Envelope Heat Loss
---------------------------

**Transmission Heat Loss**

.. code-block:: python

    def calculate_transmission_heat_loss(building_params, T_indoor, T_outdoor):
        """Calculate heat loss through building envelope"""
        
        dT = T_indoor - T_outdoor
        
        # Wall heat loss
        Q_walls = (
            building_params['wall_area'] * 
            building_params['u_value_wall'] * 
            dT
        )
        
        # Roof heat loss
        Q_roof = (
            building_params['roof_area'] * 
            building_params['u_value_roof'] * 
            dT
        )
        
        # Floor heat loss (ground coupling factor applied)
        Q_floor = (
            building_params['floor_area'] * 
            building_params['u_value_floor'] * 
            dT * 
            building_params.get('ground_coupling_factor', 0.8)
        )
        
        # Window heat loss
        Q_windows = (
            building_params['window_area'] * 
            building_params['u_value_window'] * 
            dT
        )
        
        # Thermal bridging adjustment
        thermal_bridge_factor = building_params.get('thermal_bridge_factor', 0.05)
        Q_thermal_bridges = (Q_walls + Q_roof) * thermal_bridge_factor
        
        total_transmission_loss = Q_walls + Q_roof + Q_floor + Q_windows + Q_thermal_bridges
        
        return {
            'total': total_transmission_loss,
            'walls': Q_walls,
            'roof': Q_roof,
            'floor': Q_floor,
            'windows': Q_windows,
            'thermal_bridges': Q_thermal_bridges
        }

**Ventilation Heat Loss**

.. code-block:: python

    def calculate_ventilation_heat_loss(building_params, T_indoor, T_outdoor):
        """Calculate heat loss from ventilation and infiltration"""
        
        # Air properties
        rho_air = 1.2  # kg/m³ at 20°C
        cp_air = 1005  # J/(kg·K)
        
        # Building volume
        volume = building_params['floor_area'] * building_params.get('ceiling_height', 2.7)
        
        # Mechanical ventilation
        ventilation_rate = building_params.get('mechanical_ventilation_rate', 0.3)  # ACH
        
        # Infiltration (additional to mechanical ventilation)
        infiltration_rate = building_params.get('infiltration_rate', 0.2)  # ACH
        
        # Total air change rate
        total_air_changes = ventilation_rate + infiltration_rate
        
        # Volumetric flow rate
        V_dot = total_air_changes * volume / 3600  # m³/s
        
        # Mass flow rate
        m_dot = V_dot * rho_air  # kg/s
        
        # Heat recovery efficiency (only applies to mechanical ventilation)
        heat_recovery_efficiency = building_params.get('heat_recovery_efficiency', 0.0)
        
        # Effective temperature difference (accounting for heat recovery)
        dT_mechanical = (T_indoor - T_outdoor) * (1 - heat_recovery_efficiency)
        dT_infiltration = T_indoor - T_outdoor
        
        # Heat loss calculation
        Q_ventilation_mechanical = (
            (ventilation_rate * volume / 3600) * rho_air * cp_air * dT_mechanical
        )
        
        Q_ventilation_infiltration = (
            (infiltration_rate * volume / 3600) * rho_air * cp_air * dT_infiltration
        )
        
        total_ventilation_loss = Q_ventilation_mechanical + Q_ventilation_infiltration
        
        return {
            'total': total_ventilation_loss,
            'mechanical': Q_ventilation_mechanical,
            'infiltration': Q_ventilation_infiltration,
            'heat_recovery_savings': (
                (ventilation_rate * volume / 3600) * rho_air * cp_air * 
                (T_indoor - T_outdoor) * heat_recovery_efficiency
            )
        }

Solar Heat Gains
---------------

**Window Solar Gains**

.. code-block:: python

    def calculate_window_solar_gains(building_params, solar_data, hour_of_year):
        """Calculate solar heat gains through windows"""
        
        gains_by_orientation = {}
        total_solar_gain = 0
        
        # Window areas by orientation (if specified)
        orientations = ['north', 'south', 'east', 'west']
        
        for orientation in orientations:
            window_area_key = f'window_area_{orientation}'
            if window_area_key in building_params:
                window_area = building_params[window_area_key]
                
                # Solar heat gain coefficient
                shgc = building_params.get('solar_heat_gain_coefficient', 0.5)
                
                # Window shading factor (seasonal/hourly variation)
                shading_factor = calculate_shading_factor(
                    orientation, hour_of_year, building_params
                )
                
                # Incident solar radiation on surface
                incident_solar = calculate_incident_solar(
                    solar_data, orientation, building_params['latitude'],
                    building_params['longitude'], hour_of_year
                )
                
                # Solar gain through windows
                orientation_gain = (
                    incident_solar * window_area * shgc * shading_factor
                )
                
                gains_by_orientation[orientation] = orientation_gain
                total_solar_gain += orientation_gain
        
        # If orientations not specified, use total window area
        if not gains_by_orientation and 'window_area' in building_params:
            avg_incident_solar = (
                solar_data['global_horizontal'] + 
                solar_data.get('diffuse_horizontal', solar_data['global_horizontal'] * 0.3)
            ) / 2  # Simplified average for vertical surfaces
            
            shgc = building_params.get('solar_heat_gain_coefficient', 0.5)
            shading_factor = building_params.get('average_shading_factor', 0.8)
            
            total_solar_gain = (
                avg_incident_solar * building_params['window_area'] * 
                shgc * shading_factor
            )
        
        return {
            'total': total_solar_gain,
            'by_orientation': gains_by_orientation
        }

**Incident Solar Radiation Calculation**

.. code-block:: python

    import math
    
    def calculate_incident_solar(solar_data, orientation, latitude, longitude, hour_of_year):
        """Calculate incident solar radiation on vertical surface"""
        
        # Solar angles
        declination = calculate_solar_declination(hour_of_year)
        hour_angle = calculate_hour_angle(hour_of_year, longitude)
        
        # Solar elevation and azimuth
        elevation = math.asin(
            math.sin(math.radians(latitude)) * math.sin(declination) +
            math.cos(math.radians(latitude)) * math.cos(declination) * math.cos(hour_angle)
        )
        
        azimuth = math.atan2(
            math.sin(hour_angle),
            math.cos(hour_angle) * math.sin(math.radians(latitude)) - 
            math.tan(declination) * math.cos(math.radians(latitude))
        )
        
        # Surface orientation angles
        orientation_angles = {
            'south': 180,
            'north': 0,
            'east': 90,
            'west': 270
        }
        
        surface_azimuth = math.radians(orientation_angles.get(orientation, 180))
        surface_tilt = math.radians(90)  # Vertical surface
        
        # Angle of incidence
        cos_incidence = (
            math.sin(elevation) * math.cos(surface_tilt) +
            math.cos(elevation) * math.sin(surface_tilt) * 
            math.cos(azimuth - surface_azimuth)
        )
        
        cos_incidence = max(0, cos_incidence)  # No negative values
        
        # Direct and diffuse components
        direct_normal = solar_data.get('direct_normal', 0)
        diffuse_horizontal = solar_data.get('diffuse_horizontal', 
                                          solar_data['global_horizontal'] * 0.3)
        
        # Direct radiation on surface
        direct_on_surface = direct_normal * cos_incidence
        
        # Diffuse radiation (simplified isotropic sky model)
        diffuse_on_surface = diffuse_horizontal * (1 + math.cos(surface_tilt)) / 2
        
        # Ground reflected radiation (assuming 20% reflectance)
        ground_reflectance = 0.2
        ground_reflected = (
            solar_data['global_horizontal'] * ground_reflectance * 
            (1 - math.cos(surface_tilt)) / 2
        )
        
        total_incident = direct_on_surface + diffuse_on_surface + ground_reflected
        
        return max(0, total_incident)

Internal Heat Gains
------------------

**Occupancy Heat Gains**

.. code-block:: python

    def calculate_occupancy_heat_gains(building_params, hour_of_year, occupancy_schedule):
        """Calculate internal heat gains from occupants"""
        
        # Get occupancy fraction for this hour
        hour_of_day = hour_of_year % 24
        day_of_week = (hour_of_year // 24) % 7
        
        if day_of_week < 5:  # Weekday
            occupancy_fraction = occupancy_schedule['weekday'][hour_of_day]
        else:  # Weekend
            occupancy_fraction = occupancy_schedule['weekend'][hour_of_day]
        
        # Number of occupants present
        occupants_present = building_params['occupant_count'] * occupancy_fraction
        
        # Heat gains per person (sensible + latent)
        sensible_gain_per_person = 75  # W (seated, light activity)
        latent_gain_per_person = 55   # W (moisture)
        
        # Activity level adjustment
        activity_factor = building_params.get('activity_factor', 1.0)
        
        total_sensible_gain = (
            occupants_present * sensible_gain_per_person * activity_factor
        )
        
        total_latent_gain = (
            occupants_present * latent_gain_per_person * activity_factor
        )
        
        return {
            'total_sensible': total_sensible_gain,
            'total_latent': total_latent_gain,
            'occupants_present': occupants_present
        }

**Equipment and Lighting Gains**

.. code-block:: python

    def calculate_equipment_lighting_gains(building_params, hour_of_year, usage_schedules):
        """Calculate internal gains from equipment and lighting"""
        
        hour_of_day = hour_of_year % 24
        day_of_week = (hour_of_year // 24) % 7
        
        gains = {}
        
        # Lighting gains
        lighting_power = building_params.get('lighting_installed_power', 0)
        if day_of_week < 5:
            lighting_fraction = usage_schedules['lighting']['weekday'][hour_of_day]
        else:
            lighting_fraction = usage_schedules['lighting']['weekend'][hour_of_day]
        
        gains['lighting'] = lighting_power * lighting_fraction
        
        # Equipment gains
        equipment_power = building_params.get('equipment_installed_power', 0)
        if day_of_week < 5:
            equipment_fraction = usage_schedules['equipment']['weekday'][hour_of_day]
        else:
            equipment_fraction = usage_schedules['equipment']['weekend'][hour_of_day]
        
        gains['equipment'] = equipment_power * equipment_fraction
        
        # Cooking gains (if applicable)
        if building_params.get('building_type') == 'residential':
            cooking_power = building_params.get('cooking_installed_power', 1000)
            if day_of_week < 5:
                cooking_fraction = usage_schedules['cooking']['weekday'][hour_of_day]
            else:
                cooking_fraction = usage_schedules['cooking']['weekend'][hour_of_day]
            
            gains['cooking'] = cooking_power * cooking_fraction
        
        gains['total'] = sum(gains.values())
        
        return gains

Thermal Mass Effects
-------------------

**Dynamic Heat Storage**

.. code-block:: python

    def calculate_thermal_mass_effects(building_params, T_indoor_prev, T_setpoint, 
                                     heat_gains, heat_losses, timestep_hours=1):
        """Calculate thermal mass effects on indoor temperature"""
        
        # Building thermal capacity
        thermal_capacity = building_params.get('thermal_capacity', 250000)  # J/K
        
        # Net heat input to building
        net_heat_input = heat_gains - heat_losses  # W
        
        # Temperature change due to thermal mass
        dT_dt = net_heat_input / thermal_capacity  # K/s
        
        # New indoor temperature (if free-running)
        T_indoor_new = T_indoor_prev + (dT_dt * timestep_hours * 3600)
        
        # If heating/cooling system present, calculate required capacity
        heating_cooling_power = 0
        
        if T_indoor_new < T_setpoint - 0.5:  # Heating required
            # Calculate heating power to reach setpoint
            heating_cooling_power = (
                (T_setpoint - T_indoor_new) * thermal_capacity / 
                (timestep_hours * 3600)
            )
            T_indoor_final = T_setpoint
        
        elif T_indoor_new > T_setpoint + 0.5:  # Cooling required (if available)
            if building_params.get('has_cooling', False):
                heating_cooling_power = -(
                    (T_indoor_new - T_setpoint) * thermal_capacity / 
                    (timestep_hours * 3600)
                )
                T_indoor_final = T_setpoint
            else:
                T_indoor_final = T_indoor_new  # No cooling available
        
        else:
            T_indoor_final = T_indoor_new
        
        return {
            'indoor_temperature': T_indoor_final,
            'heating_cooling_power': heating_cooling_power,
            'thermal_mass_effect': T_indoor_new - T_indoor_prev
        }

Algorithm Integration
--------------------

**Main Thermal Calculation Loop**

.. code-block:: python

    def calculate_building_thermal_performance(building_params, weather_data):
        """Main thermal calculation for building energy analysis"""
        
        results = {
            'hourly_data': [],
            'monthly_summaries': {},
            'annual_totals': {}
        }
        
        # Initialize indoor temperature
        T_indoor = 20.0  # °C
        
        for hour in range(8760):  # Full year
            weather_hour = weather_data[hour]
            T_outdoor = weather_hour['temperature']
            
            # Calculate heat losses
            transmission_losses = calculate_transmission_heat_loss(
                building_params, T_indoor, T_outdoor
            )
            
            ventilation_losses = calculate_ventilation_heat_loss(
                building_params, T_indoor, T_outdoor
            )
            
            total_losses = transmission_losses['total'] + ventilation_losses['total']
            
            # Calculate heat gains
            solar_gains = calculate_window_solar_gains(
                building_params, weather_hour, hour
            )
            
            occupancy_gains = calculate_occupancy_heat_gains(
                building_params, hour, occupancy_schedules
            )
            
            equipment_gains = calculate_equipment_lighting_gains(
                building_params, hour, usage_schedules
            )
            
            total_gains = (
                solar_gains['total'] + 
                occupancy_gains['total_sensible'] + 
                equipment_gains['total']
            )
            
            # Apply thermal mass effects
            thermal_result = calculate_thermal_mass_effects(
                building_params, T_indoor, 20.0, total_gains, total_losses
            )
            
            T_indoor = thermal_result['indoor_temperature']
            heating_power = max(0, thermal_result['heating_cooling_power'])
            cooling_power = max(0, -thermal_result['heating_cooling_power'])
            
            # Store hourly results
            hourly_result = {
                'hour': hour,
                'outdoor_temperature': T_outdoor,
                'indoor_temperature': T_indoor,
                'transmission_losses': transmission_losses['total'],
                'ventilation_losses': ventilation_losses['total'],
                'solar_gains': solar_gains['total'],
                'internal_gains': occupancy_gains['total_sensible'] + equipment_gains['total'],
                'heating_demand': heating_power,
                'cooling_demand': cooling_power
            }
            
            results['hourly_data'].append(hourly_result)
        
        # Calculate monthly and annual summaries
        results['annual_totals'] = {
            'heating_demand': sum(h['heating_demand'] for h in results['hourly_data']),
            'cooling_demand': sum(h['cooling_demand'] for h in results['hourly_data']),
            'total_losses': sum(h['transmission_losses'] + h['ventilation_losses'] 
                              for h in results['hourly_data']),
            'total_gains': sum(h['solar_gains'] + h['internal_gains'] 
                             for h in results['hourly_data'])
        }
        
        return results

For detailed implementation examples, see :doc:`implementation_details`.