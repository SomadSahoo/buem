Validation
==========

Validation methodology and benchmarking of BuEM thermal calculations.

Validation Framework
-------------------

**Multi-Level Validation Approach**

BuEM undergoes validation at several levels:

1. **Unit Testing**: Individual function validation
2. **Component Testing**: Building element calculations
3. **Integration Testing**: Complete building models
4. **Benchmark Validation**: Comparison with reference cases
5. **Measured Data Validation**: Real building performance

**Validation Standards**

BuEM validation follows established standards:

- **ASHRAE Standard 140**: Building energy simulation validation
- **EN 15265**: Energy performance calculation methods validation
- **IEA BESTEST**: Building energy simulation test procedures
- **ANSI/ASHRAE 140**: Standard method of test for building energy simulation

Unit Testing
-----------

**Heat Transfer Functions**

.. code-block:: python

    import pytest
    import math
    
    class TestHeatTransferCalculations:
        
        def test_transmission_heat_loss_basic(self):
            """Test basic transmission heat loss calculation"""
            building_params = {
                'wall_area': 100,  # m²
                'u_value_wall': 0.3,  # W/(m²·K)
                'roof_area': 50,
                'u_value_roof': 0.2,
                'floor_area': 50,
                'u_value_floor': 0.25,
                'window_area': 15,
                'u_value_window': 1.5
            }
            
            T_indoor = 20.0  # °C
            T_outdoor = 0.0  # °C
            
            result = calculate_transmission_heat_loss(building_params, T_indoor, T_outdoor)
            
            # Expected calculation:
            # Walls: 100 * 0.3 * 20 = 600 W
            # Roof: 50 * 0.2 * 20 = 200 W
            # Floor: 50 * 0.25 * 20 * 0.8 = 200 W (ground coupling)
            # Windows: 15 * 1.5 * 20 = 450 W
            # Total: 1450 W (plus thermal bridges)
            
            expected_total = 600 + 200 + 200 + 450  # 1450 W base
            assert abs(result['walls'] - 600) < 1.0
            assert abs(result['roof'] - 200) < 1.0
            assert abs(result['windows'] - 450) < 1.0
            assert result['total'] > expected_total  # Should include thermal bridges
        
        def test_ventilation_heat_loss(self):
            """Test ventilation heat loss calculation"""
            building_params = {
                'floor_area': 100,  # m²
                'ceiling_height': 2.5,  # m
                'mechanical_ventilation_rate': 0.5,  # ACH
                'infiltration_rate': 0.3,  # ACH
                'heat_recovery_efficiency': 0.0
            }
            
            result = calculate_ventilation_heat_loss(building_params, 20.0, 0.0)
            
            # Volume = 100 * 2.5 = 250 m³
            # Total ACH = 0.5 + 0.3 = 0.8
            # Volumetric flow = 0.8 * 250 / 3600 = 0.0556 m³/s
            # Mass flow = 0.0556 * 1.2 = 0.0667 kg/s
            # Heat loss = 0.0667 * 1005 * 20 = 1340 W
            
            expected_loss = 0.8 * 250 / 3600 * 1.2 * 1005 * 20
            assert abs(result['total'] - expected_loss) < 10.0
        
        def test_solar_gains_basic(self):
            """Test basic solar gain calculation"""
            building_params = {
                'window_area': 20,  # m²
                'solar_heat_gain_coefficient': 0.5,
                'latitude': 46.5,
                'longitude': 6.6
            }
            
            solar_data = {
                'global_horizontal': 500,  # W/m²
                'diffuse_horizontal': 150   # W/m²
            }
            
            result = calculate_window_solar_gains(building_params, solar_data, 2000)
            
            # Should be positive solar gain
            assert result['total'] > 0
            # Should be reasonable magnitude (less than max possible)
            assert result['total'] < 500 * 20 * 0.5  # Max theoretical

Component Testing
----------------

**Building Element Validation**

.. code-block:: python

    class TestBuildingElements:
        
        def test_window_heat_transfer_coefficient(self):
            """Validate window U-value calculations"""
            # Test different glazing types
            test_cases = [
                {'type': 'single_glazed', 'expected_u': 5.8, 'tolerance': 0.2},
                {'type': 'double_glazed', 'expected_u': 2.8, 'tolerance': 0.2},
                {'type': 'triple_glazed', 'expected_u': 1.8, 'tolerance': 0.2},
                {'type': 'low_e_double', 'expected_u': 1.6, 'tolerance': 0.2}
            ]
            
            for case in test_cases:
                calculated_u = calculate_window_u_value(case['type'])
                assert abs(calculated_u - case['expected_u']) < case['tolerance']
        
        def test_wall_thermal_mass(self):
            """Validate thermal mass calculations for different wall types"""
            wall_types = {
                'timber_frame': {'expected_capacity': 120000, 'tolerance': 20000},
                'masonry_cavity': {'expected_capacity': 250000, 'tolerance': 50000},
                'concrete': {'expected_capacity': 400000, 'tolerance': 80000}
            }
            
            for wall_type, expected in wall_types.items():
                params = {'wall_construction': wall_type, 'floor_area': 100}
                capacity = calculate_building_thermal_capacity(params)
                
                assert abs(capacity - expected['expected_capacity']) < expected['tolerance']

Benchmark Validation
-------------------

**BESTEST Case 600 (Basic Building)**

.. code-block:: python

    def test_bestest_case_600():
        """Validate against BESTEST Case 600 - Basic building with south windows"""
        
        bestest_600_params = {
            'floor_area': 48.0,  # 8m x 6m
            'building_height': 2.7,
            'wall_area': 75.6,   # Total exterior wall area minus windows
            'roof_area': 48.0,
            'window_area_south': 12.0,  # All windows on south face
            'u_value_wall': 0.514,      # W/(m²·K)
            'u_value_roof': 0.318,
            'u_value_floor': 0.039,
            'u_value_window': 3.0,
            'solar_heat_gain_coefficient': 0.789,
            'infiltration_rate': 0.5,   # ACH at 50Pa
            'thermal_mass': 'light',
            'latitude': 39.76,           # Denver, Colorado
            'longitude': -104.86
        }
        
        # Run simulation with BESTEST weather data
        results = run_annual_simulation(bestest_600_params, 'TMY2_denver.csv')
        
        # BESTEST 600 reference results (from multiple simulation tools)
        reference_results = {
            'annual_heating_load': {'min': 4613, 'max': 5944, 'mean': 5383},  # MWh
            'annual_cooling_load': {'min': 6137, 'max': 8448, 'mean': 6827},  # MWh
            'peak_heating_load': {'min': 3437, 'max': 4354, 'mean': 3940},    # W
            'peak_cooling_load': {'min': 5865, 'max': 6776, 'mean': 6253}     # W
        }
        
        # Convert BuEM results to same units
        annual_heating = sum(results['hourly_data'][h]['heating_demand'] 
                           for h in range(8760)) / 1000  # Convert to MWh
        annual_cooling = sum(results['hourly_data'][h]['cooling_demand'] 
                           for h in range(8760)) / 1000
        
        peak_heating = max(results['hourly_data'][h]['heating_demand'] 
                          for h in range(8760))
        peak_cooling = max(results['hourly_data'][h]['cooling_demand'] 
                          for h in range(8760))
        
        # Validate against reference range
        assert (reference_results['annual_heating_load']['min'] <= 
                annual_heating <= 
                reference_results['annual_heating_load']['max']), \
                f"Annual heating load {annual_heating} outside BESTEST range"
        
        assert (reference_results['annual_cooling_load']['min'] <= 
                annual_cooling <= 
                reference_results['annual_cooling_load']['max']), \
                f"Annual cooling load {annual_cooling} outside BESTEST range"

**ASHRAE 140 Validation Suite**

.. code-block:: python

    class TestASHRAE140:
        """Complete ASHRAE 140 validation test suite"""
        
        def test_case_series_600(self):
            """Test basic building thermal cases (600-650)"""
            cases = [
                '600',  # Basic case
                '610',  # South shading
                '620',  # East/west windows
                '630',  # East/west shading
                '640',  # Heating setback
                '650'   # Night ventilation
            ]
            
            for case in cases:
                params = load_ashrae_140_parameters(case)
                results = run_annual_simulation(params)
                reference = load_ashrae_140_reference(case)
                
                validate_against_reference(results, reference, case)
        
        def test_case_series_900(self):
            """Test high thermal mass cases (900-960)"""
            cases = ['900', '910', '920', '930', '940', '950', '960']
            
            for case in cases:
                params = load_ashrae_140_parameters(case)
                results = run_annual_simulation(params)
                reference = load_ashrae_140_reference(case)
                
                # High mass cases should show different behavior
                validate_thermal_mass_effects(results, reference, case)

Measured Data Validation
-----------------------

**Real Building Comparisons**

.. code-block:: python

    def validate_against_measured_data(building_id):
        """Validate simulation against measured building performance"""
        
        # Load building parameters and measured data
        building_params = load_building_parameters(building_id)
        measured_data = load_measured_energy_data(building_id)
        weather_data = load_local_weather_data(building_params['location'])
        
        # Run simulation
        simulated_results = run_annual_simulation(building_params, weather_data)
        
        # Compare monthly energy consumption
        monthly_comparison = compare_monthly_consumption(
            simulated_results, measured_data
        )
        
        # Calculate validation metrics
        validation_metrics = {
            'cv_rmse': calculate_cv_rmse(simulated_results, measured_data),
            'nmbe': calculate_nmbe(simulated_results, measured_data),
            'correlation': calculate_correlation(simulated_results, measured_data)
        }
        
        # ASHRAE Guideline 14 acceptance criteria
        assert validation_metrics['cv_rmse'] < 30.0, \
            f"CV(RMSE) {validation_metrics['cv_rmse']:.1f}% exceeds 30% limit"
        
        assert abs(validation_metrics['nmbe']) < 10.0, \
            f"NMBE {validation_metrics['nmbe']:.1f}% exceeds ±10% limit"
        
        return validation_metrics
    
    def calculate_cv_rmse(simulated, measured):
        """Calculate Coefficient of Variation of Root Mean Square Error"""
        import numpy as np
        
        sim_monthly = aggregate_monthly_consumption(simulated)
        meas_monthly = measured['monthly_consumption']
        
        rmse = np.sqrt(np.mean((sim_monthly - meas_monthly) ** 2))
        cv_rmse = (rmse / np.mean(meas_monthly)) * 100
        
        return cv_rmse
    
    def calculate_nmbe(simulated, measured):
        """Calculate Normalized Mean Bias Error"""
        import numpy as np
        
        sim_monthly = aggregate_monthly_consumption(simulated)
        meas_monthly = measured['monthly_consumption']
        
        mbe = np.mean(sim_monthly - meas_monthly)
        nmbe = (mbe / np.mean(meas_monthly)) * 100
        
        return nmbe

Statistical Analysis
-------------------

**Uncertainty Analysis**

.. code-block:: python

    def perform_uncertainty_analysis(building_params, num_runs=1000):
        """Perform Monte Carlo uncertainty analysis"""
        import numpy as np
        
        results = []
        
        for run in range(num_runs):
            # Apply parameter variations
            varied_params = apply_parameter_uncertainty(building_params)
            
            # Run simulation
            result = run_annual_simulation(varied_params)
            annual_heating = sum(result['hourly_data'][h]['heating_demand'] 
                               for h in range(8760))
            results.append(annual_heating)
        
        # Calculate statistics
        uncertainty_stats = {
            'mean': np.mean(results),
            'std': np.std(results),
            'cv': np.std(results) / np.mean(results) * 100,  # Coefficient of variation
            'p10': np.percentile(results, 10),
            'p90': np.percentile(results, 90),
            'min': np.min(results),
            'max': np.max(results)
        }
        
        return uncertainty_stats
    
    def apply_parameter_uncertainty(base_params):
        """Apply realistic parameter uncertainties"""
        import numpy as np
        
        varied_params = base_params.copy()
        
        # U-value uncertainties (±10%)
        for param in ['u_value_wall', 'u_value_roof', 'u_value_window']:
            if param in varied_params:
                uncertainty = 0.1  # 10%
                variation = np.random.normal(1.0, uncertainty)
                varied_params[param] *= variation
        
        # Infiltration rate uncertainty (±50%)
        if 'infiltration_rate' in varied_params:
            uncertainty = 0.5  # 50%
            variation = np.random.lognormal(0, uncertainty)
            varied_params['infiltration_rate'] *= variation
        
        # Thermal mass uncertainty (±30%)
        if 'thermal_capacity' in varied_params:
            uncertainty = 0.3  # 30%
            variation = np.random.normal(1.0, uncertainty)
            varied_params['thermal_capacity'] *= variation
        
        return varied_params

Validation Reporting
-------------------

**Automated Validation Reports**

.. code-block:: python

    def generate_validation_report():
        """Generate comprehensive validation report"""
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'buem_version': get_buem_version(),
            'test_results': {}
        }
        
        # Run all validation tests
        test_suites = [
            ('unit_tests', run_unit_tests),
            ('component_tests', run_component_tests),
            ('bestest_validation', run_bestest_validation),
            ('ashrae_140', run_ashrae_140_validation),
            ('measured_data', run_measured_data_validation)
        ]
        
        for suite_name, test_function in test_suites:
            try:
                results = test_function()
                report['test_results'][suite_name] = {
                    'status': 'passed',
                    'results': results
                }
            except AssertionError as e:
                report['test_results'][suite_name] = {
                    'status': 'failed',
                    'error': str(e)
                }
            except Exception as e:
                report['test_results'][suite_name] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        # Overall validation status
        all_passed = all(
            result['status'] == 'passed' 
            for result in report['test_results'].values()
        )
        
        report['overall_status'] = 'passed' if all_passed else 'failed'
        
        # Save report
        with open('validation_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        return report

For continuous integration validation, see :doc:`../deployment/production_deployment`.