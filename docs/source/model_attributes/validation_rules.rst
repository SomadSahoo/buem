Validation Rules
================

Comprehensive validation framework for building model attributes and data consistency.

Validation Framework
-------------------

**Multi-Level Validation**

BuEM implements validation at multiple levels:

1. **Schema Validation**: Data types and required fields
2. **Range Validation**: Physical and practical limits
3. **Consistency Validation**: Relationships between attributes
4. **Physics Validation**: Thermodynamic and energy balance checks

**Validation Configuration**

Validation rules are defined in JSON configuration files:

.. code-block:: json

    {
        "building_attributes": {
            "coordinates": {
                "required": true,
                "type": "object",
                "properties": {
                    "latitude": {
                        "type": "number",
                        "minimum": -90,
                        "maximum": 90,
                        "error_message": "Latitude must be between -90 and 90 degrees"
                    },
                    "longitude": {
                        "type": "number",
                        "minimum": -180,
                        "maximum": 180,
                        "error_message": "Longitude must be between -180 and 180 degrees"
                    }
                }
            }
        }
    }

Schema Validation
----------------

**Data Type Validation**

.. code-block:: python

    # Type checking implementation
    def validate_data_types(building_data, schema):
        errors = []
        
        for field_name, field_schema in schema.items():
            if field_name in building_data:
                value = building_data[field_name]
                expected_type = field_schema.get('type')
                
                if expected_type == 'number' and not isinstance(value, (int, float)):
                    errors.append(f"{field_name}: Expected number, got {type(value).__name__}")
                elif expected_type == 'string' and not isinstance(value, str):
                    errors.append(f"{field_name}: Expected string, got {type(value).__name__}")
                elif expected_type == 'boolean' and not isinstance(value, bool):
                    errors.append(f"{field_name}: Expected boolean, got {type(value).__name__}")
        
        return errors

**Required Field Validation**

.. code-block:: python

    def validate_required_fields(building_data, schema):
        errors = []
        
        for field_name, field_schema in schema.items():
            if field_schema.get('required', False) and field_name not in building_data:
                errors.append(f"Missing required field: {field_name}")
        
        return errors

Range Validation
---------------

**Numerical Range Checks**

.. code-block:: python

    def validate_ranges(building_data, schema):
        errors = []
        
        for field_name, value in building_data.items():
            if field_name in schema:
                field_schema = schema[field_name]
                
                # Minimum value check
                if 'minimum' in field_schema and value < field_schema['minimum']:
                    errors.append(
                        f"{field_name}: Value {value} below minimum {field_schema['minimum']}"
                    )
                
                # Maximum value check
                if 'maximum' in field_schema and value > field_schema['maximum']:
                    errors.append(
                        f"{field_name}: Value {value} above maximum {field_schema['maximum']}"
                    )
                
                # Enumeration check
                if 'enum' in field_schema and value not in field_schema['enum']:
                    allowed_values = ', '.join(field_schema['enum'])
                    errors.append(
                        f"{field_name}: Value '{value}' not in allowed values: {allowed_values}"
                    )
        
        return errors

**Physical Limits**

.. list-table:: Common Physical Validation Ranges
   :header-rows: 1

   * - Attribute
     - Minimum
     - Maximum
     - Unit
     - Rationale
   * - U-value wall
     - 0.05
     - 3.0
     - W/(m²·K)
     - Super-insulated to uninsulated
   * - Floor area
     - 10
     - 100,000
     - m²
     - Small room to large complex
   * - Window-to-wall ratio
     - 0.0
     - 0.9
     - fraction
     - No windows to mostly glass
   * - Air change rate
     - 0.1
     - 10.0
     - h⁻¹
     - Tight building to very leaky
   * - Occupancy density
     - 0.005
     - 1.0
     - people/m²
     - Warehouse to crowded office

Consistency Validation
---------------------

**Geometric Consistency**

.. code-block:: python

    def validate_geometric_consistency(building_attrs):
        errors = []
        
        # Window area cannot exceed wall area
        if 'window_area' in building_attrs and 'wall_area' in building_attrs:
            if building_attrs['window_area'] > building_attrs['wall_area']:
                errors.append("Window area exceeds total wall area")
        
        # Floor area per storey should be reasonable
        if 'floor_area' in building_attrs and 'storeys' in building_attrs:
            area_per_storey = building_attrs['floor_area'] / building_attrs['storeys']
            if area_per_storey < 5 or area_per_storey > 10000:
                errors.append(f"Floor area per storey ({area_per_storey:.1f} m²) seems unrealistic")
        
        # Building height vs. storeys consistency
        if 'building_height' in building_attrs and 'storeys' in building_attrs:
            height_per_storey = building_attrs['building_height'] / building_attrs['storeys']
            if height_per_storey < 2.0 or height_per_storey > 6.0:
                errors.append(f"Height per storey ({height_per_storey:.1f} m) outside typical range")
        
        return errors

**Window-to-Wall Ratio Validation**

.. code-block:: python

    def validate_window_to_wall_ratio(building_attrs):
        errors = []
        
        # Calculate actual vs. specified window-to-wall ratio
        if all(key in building_attrs for key in ['window_area', 'wall_area', 'window_to_wall_ratio']):
            calculated_ratio = building_attrs['window_area'] / building_attrs['wall_area']
            specified_ratio = building_attrs['window_to_wall_ratio']
            
            if abs(calculated_ratio - specified_ratio) > 0.1:
                errors.append(
                    f"Window-to-wall ratio mismatch: specified {specified_ratio:.2f}, "
                    f"calculated {calculated_ratio:.2f}"
                )
        
        return errors

Physics Validation
-----------------

**Heat Transfer Validation**

.. code-block:: python

    def validate_heat_transfer_physics(building_attrs):
        errors = []
        
        # U-value relationships (wall > roof > floor typically)
        u_values = {}
        for component in ['wall', 'roof', 'floor', 'window']:
            key = f'u_value_{component}'
            if key in building_attrs:
                u_values[component] = building_attrs[key]
        
        # Windows should have higher U-values than walls
        if 'wall' in u_values and 'window' in u_values:
            if u_values['window'] < u_values['wall']:
                errors.append(
                    "Warning: Window U-value lower than wall U-value (unusual)"
                )
        
        # Roof typically better insulated than walls
        if 'wall' in u_values and 'roof' in u_values:
            if u_values['roof'] > u_values['wall'] * 1.5:
                errors.append(
                    "Warning: Roof U-value significantly higher than wall (check insulation)"
                )
        
        return errors

**Energy Balance Validation**

.. code-block:: python

    def validate_energy_balance(building_attrs, weather_data):
        warnings = []
        
        # Estimate heating degree days
        if weather_data:
            heating_degree_days = sum(
                max(0, 18.3 - temp) for temp in weather_data['temperature']
            ) / 24  # Convert hours to days
            
            # Rough heating demand estimate (W/m²)
            if 'u_value_wall' in building_attrs:
                avg_u_value = building_attrs['u_value_wall']  # Simplified
                estimated_demand = avg_u_value * heating_degree_days * 24 / 1000  # kWh/m²
                
                # Sanity check against typical ranges
                if estimated_demand < 10:
                    warnings.append(
                        f"Very low heating demand estimated ({estimated_demand:.1f} kWh/m²/year) - "
                        "check insulation values"
                    )
                elif estimated_demand > 300:
                    warnings.append(
                        f"Very high heating demand estimated ({estimated_demand:.1f} kWh/m²/year) - "
                        "check building envelope"
                    )
        
        return warnings

Custom Validation Rules
----------------------

**Building Type-Specific Validation**

.. code-block:: python

    def validate_building_type_specific(building_attrs):
        errors = []
        building_type = building_attrs.get('building_type')
        
        if building_type == 'residential':
            # Residential-specific checks
            if building_attrs.get('occupant_density', 0) > 0.1:
                errors.append("Occupant density too high for residential building")
            
            if building_attrs.get('floor_area', 0) > 1000:
                errors.append("Warning: Very large floor area for single residential unit")
        
        elif building_type == 'office':
            # Office-specific checks
            if building_attrs.get('window_to_wall_ratio', 0) < 0.15:
                errors.append("Warning: Low window ratio for office building (daylighting concerns)")
            
            if building_attrs.get('occupant_density', 0) > 0.2:
                errors.append("Very high occupant density for office building")
        
        return errors

Error Handling and Reporting
---------------------------

**Validation Error Classes**

.. code-block:: python

    class ValidationError(Exception):
        """Base validation error"""
        def __init__(self, message, field=None, value=None):
            self.message = message
            self.field = field
            self.value = value
            super().__init__(message)
    
    class CriticalValidationError(ValidationError):
        """Critical validation error that prevents analysis"""
        pass
    
    class ValidationWarning(ValidationError):
        """Non-critical validation issue"""
        pass

**Comprehensive Validation Report**

.. code-block:: python

    def generate_validation_report(building_data):
        report = {
            'status': 'valid',
            'errors': [],
            'warnings': [],
            'details': {}
        }
        
        try:
            # Run all validation checks
            schema_errors = validate_schema(building_data)
            range_errors = validate_ranges(building_data)
            consistency_errors = validate_consistency(building_data)
            physics_warnings = validate_physics(building_data)
            
            report['errors'].extend(schema_errors + range_errors + consistency_errors)
            report['warnings'].extend(physics_warnings)
            
            if report['errors']:
                report['status'] = 'invalid'
            elif report['warnings']:
                report['status'] = 'valid_with_warnings'
            
            # Add summary statistics
            report['details'] = {
                'total_errors': len(report['errors']),
                'total_warnings': len(report['warnings']),
                'validation_time': time.time() - start_time
            }
            
        except Exception as e:
            report['status'] = 'validation_failed'
            report['errors'].append(f"Validation system error: {str(e)}")
        
        return report

Validation in API Integration
----------------------------

**Real-time Validation**

.. code-block:: python

    # API endpoint with validation
    @app.route('/api/geojson', methods=['POST'])
    def process_geojson():
        try:
            geojson_data = request.get_json()
            
            # Validate each building in the collection
            validation_results = []
            for feature in geojson_data.get('features', []):
                building_attrs = feature.get('properties', {}).get('buem', {})
                
                validation_report = generate_validation_report(building_attrs)
                validation_results.append(validation_report)
                
                if validation_report['status'] == 'invalid':
                    return {
                        'error': {
                            'type': 'validation_error',
                            'message': 'Building data validation failed',
                            'details': validation_report['errors']
                        }
                    }, 422
            
            # Proceed with analysis if validation passes
            results = analyze_buildings(geojson_data)
            return results
            
        except Exception as e:
            return {'error': {'type': 'processing_error', 'message': str(e)}}, 500

For implementation examples, see :doc:`../examples/error_handling_examples`.