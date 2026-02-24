"""
Comprehensive JSON schema validation for BUEM GeoJSON payloads.

This module provides robust validation and debugging capabilities for incoming
GeoJSON requests, supporting both legacy and new component structures.
Uses marshmallow for schema validation with detailed error reporting.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime
from enum import Enum
import json
import jsonschema
from marshmallow import Schema, fields, ValidationError, validates, validates_schema, post_load
from marshmallow_dataclass import dataclass as marsh_dataclass
import logging

logger = logging.getLogger(__name__)


class ComponentType(str, Enum):
    """Component types for building elements."""
    WALL = "wall"
    ROOF = "roof"
    FLOOR = "floor"
    WINDOW = "window"
    DOOR = "door"
    VENTILATION = "ventilation"


class ValidationLevel(str, Enum):
    """Validation severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """Single validation issue with context."""
    level: ValidationLevel
    message: str
    path: str
    value: Any = None
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Complete validation result with detailed reporting."""
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    validated_data: Optional[Dict[str, Any]] = None
    
    def add_issue(self, level: ValidationLevel, message: str, path: str, 
                  value: Any = None, suggestion: Optional[str] = None):
        """Add a validation issue."""
        self.issues.append(ValidationIssue(level, message, path, value, suggestion))
        if level == ValidationLevel.ERROR:
            self.is_valid = False
    
    def get_errors(self) -> List[ValidationIssue]:
        """Get only error-level issues."""
        return [issue for issue in self.issues if issue.level == ValidationLevel.ERROR]
    
    def get_warnings(self) -> List[ValidationIssue]:
        """Get warning-level issues."""
        return [issue for issue in self.issues if issue.level == ValidationLevel.WARNING]
    
    def summary(self) -> str:
        """Get a summary of validation results."""
        errors = len(self.get_errors())
        warnings = len(self.get_warnings())
        if errors > 0:
            return f"Validation failed: {errors} errors, {warnings} warnings"
        elif warnings > 0:
            return f"Validation passed with {warnings} warnings"
        else:
            return "Validation passed successfully"


class ComponentElementSchema(Schema):
    """Schema for individual building component elements."""
    id = fields.Str(required=True, validate=lambda x: len(x.strip()) > 0)
    area = fields.Float(required=True, validate=lambda x: x > 0)
    azimuth = fields.Float(required=True, validate=lambda x: 0 <= x <= 360)
    tilt = fields.Float(required=True, validate=lambda x: 0 <= x <= 90)
    # Optional fields for windows/doors
    surface = fields.Str(required=False, allow_none=True)
    U = fields.Float(validate=lambda x: x > 0, required=False, allow_none=True)  # Allow per-element U-values
    
    @validates('id')
    def validate_id_format(self, value):
        """Validate element ID format."""
        if not value or not value.strip():
            raise ValidationError("Element ID cannot be empty")
        # Add any specific ID format requirements here
    
    @validates('azimuth')
    def validate_azimuth_range(self, value):
        """Validate azimuth is in valid range."""
        if not 0 <= value <= 360:
            raise ValidationError("Azimuth must be between 0 and 360 degrees")


class ComponentSchema(Schema):
    """Schema for building component (Walls, Roof, etc.)."""
    U = fields.Float(validate=lambda x: x > 0, required=False, allow_none=True)  # Component-level U-value
    g_gl = fields.Float(validate=lambda x: 0 < x < 1, required=False, allow_none=True)  # For windows
    b_transmission = fields.Float(validate=lambda x: x > 0, load_default=1.0)
    elements = fields.List(fields.Nested(ComponentElementSchema), required=True, validate=lambda x: len(x) > 0)
    
    @validates_schema
    def validate_u_value_requirement(self, data, **kwargs):
        """Ensure either component-level or element-level U-values are provided."""
        component_u = data.get('U')
        elements = data.get('elements', [])
        
        if component_u is None:
            # Check if all elements have U-values
            for i, element in enumerate(elements):
                if element.get('U') is None:
                    raise ValidationError(
                        f"Element {i} missing U-value when no component-level U is provided",
                        field_name=f'elements.{i}.U'
                    )


class ChildComponentSchema(Schema):
    """Schema for child components (external format)."""
    component_id = fields.Str(required=True)
    component_type = fields.Str(required=True, validate=lambda x: x.lower() in [e.value for e in ComponentType])
    area_m2 = fields.Float(required=True, validate=lambda x: x > 0)
    orientation_deg = fields.Float(required=True, validate=lambda x: 0 <= x <= 360)
    tilt_deg = fields.Float(required=True, validate=lambda x: 0 <= x <= 90)
    u_value = fields.Float(validate=lambda x: x > 0, required=False, allow_none=True)
    surface_reference = fields.Str(required=False, allow_none=True)  # For windows/doors


class BuildingAttributesSchema(Schema):
    """Schema for building attributes."""
    # Location
    latitude = fields.Float(required=True, validate=lambda x: -90 <= x <= 90)
    longitude = fields.Float(required=True, validate=lambda x: -180 <= x <= 180)
    
    # Basic building properties
    A_ref = fields.Float(validate=lambda x: x > 0, load_default=100.0)
    h_room = fields.Float(validate=lambda x: x > 0, load_default=2.5)
    
    # Optional external format fields
    country = fields.Str(required=False, allow_none=True)
    building_type = fields.Str(required=False, allow_none=True)
    construction_period = fields.Str(required=False, allow_none=True)
    heated_area_m2 = fields.Float(validate=lambda x: x > 0, required=False, allow_none=True)
    volume_m3 = fields.Float(validate=lambda x: x > 0, required=False, allow_none=True)
    height_m = fields.Float(validate=lambda x: x > 0, required=False, allow_none=True)
    
    # Components (nested structure - preferred)
    components = fields.Dict(keys=fields.Str(), values=fields.Nested(ComponentSchema), required=False, allow_none=True)
    
    @validates('latitude')
    def validate_latitude(self, value):
        """Validate latitude range."""
        if not -90 <= value <= 90:
            raise ValidationError("Latitude must be between -90 and 90")
    
    @validates('longitude')  
    def validate_longitude(self, value):
        """Validate longitude range."""
        if not -180 <= value <= 180:
            raise ValidationError("Longitude must be between -180 and 180")


class BuemSchema(Schema):
    """Schema for BUEM section."""
    building_attributes = fields.Nested(BuildingAttributesSchema, required=True)
    child_components = fields.List(fields.Nested(ChildComponentSchema), required=False, allow_none=True)
    use_milp = fields.Bool(load_default=False)


class PropertiesSchema(Schema):
    """Schema for feature properties."""
    start_time = fields.DateTime(required=True)
    end_time = fields.DateTime(required=True)
    resolution = fields.Str(load_default="60")
    resolution_unit = fields.Str(load_default="minutes")
    buem = fields.Nested(BuemSchema, required=True)


class GeometrySchema(Schema):
    """Schema for GeoJSON geometry."""
    type = fields.Str(required=True, validate=lambda x: x == "Point")
    coordinates = fields.List(fields.Float(), required=True, validate=lambda x: len(x) == 2)


class FeatureSchema(Schema):
    """Schema for GeoJSON feature."""
    type = fields.Str(required=True, validate=lambda x: x == "Feature")
    id = fields.Str(required=True)
    geometry = fields.Nested(GeometrySchema, required=True)
    properties = fields.Nested(PropertiesSchema, required=True)


class GeoJsonRequestSchema(Schema):
    """Main schema for GeoJSON request."""
    type = fields.Str(required=True, validate=lambda x: x in ["FeatureCollection", "Feature"])
    features = fields.List(fields.Nested(FeatureSchema), required=True, validate=lambda x: len(x) > 0)
    timeStamp = fields.DateTime(required=False, allow_none=True)
    numberMatched = fields.Int(required=False, allow_none=True)
    numberReturned = fields.Int(required=False, allow_none=True)
    
    @post_load
    def normalize_single_feature(self, data, **kwargs):
        """Convert single Feature to FeatureCollection if needed."""
        if data.get('type') == 'Feature':
            # Convert single feature to collection
            feature = {k: v for k, v in data.items() if k != 'type'}
            data = {
                'type': 'FeatureCollection',
                'features': [feature]
            }
        return data


class GeoJsonValidator:
    """
    Comprehensive GeoJSON validator with hybrid component support.
    
    Supports both:
    1. Nested components structure (preferred): components.Walls.elements[]
    2. Flat child_components structure (external): child_components[]
    
    Provides detailed validation with debugging information.
    """
    
    def __init__(self, strict_mode: bool = False):
        """
        Initialize validator.
        
        Parameters
        ----------
        strict_mode : bool
            If True, warnings are treated as errors.
        """
        self.strict_mode = strict_mode
        self.schema = GeoJsonRequestSchema()
    
    def validate(self, payload: Dict[str, Any]) -> ValidationResult:
        """
        Validate GeoJSON payload with comprehensive error reporting.
        
        Parameters
        ----------
        payload : Dict[str, Any]
            Raw GeoJSON payload to validate.
            
        Returns
        -------
        ValidationResult
            Detailed validation results with errors, warnings, and suggestions.
        """
        result = ValidationResult(is_valid=True)
        
        try:
            # Basic schema validation
            validated_data = self.schema.load(payload)
            result.validated_data = validated_data
            
            # Additional custom validations
            self._validate_features(validated_data['features'], result)
            self._validate_time_consistency(validated_data['features'], result)
            self._convert_components_format(validated_data, result)
            
        except ValidationError as e:
            result.is_valid = False
            self._process_marshmallow_errors(e.messages, result)
        except Exception as e:
            result.add_issue(
                ValidationLevel.ERROR,
                f"Unexpected validation error: {str(e)}",
                "root",
                suggestion="Check payload format and structure"
            )
        
        return result
    
    def _validate_features(self, features: List[Dict], result: ValidationResult):
        """Validate individual features."""
        for i, feature in enumerate(features):
            self._validate_single_feature(feature, f"features[{i}]", result)
    
    def _validate_single_feature(self, feature: Dict, path: str, result: ValidationResult):
        """Validate a single feature."""
        buem_data = feature.get('properties', {}).get('buem', {})
        building_attrs = buem_data.get('building_attributes', {})
        child_components = buem_data.get('child_components', [])
        
        # Check for component data
        has_nested = 'components' in building_attrs and building_attrs['components']
        has_child = child_components and len(child_components) > 0
        
        if not has_nested and not has_child:
            result.add_issue(
                ValidationLevel.ERROR,
                "No building components found",
                f"{path}.properties.buem",
                suggestion="Provide either 'components' in building_attributes or 'child_components'"
            )
        elif has_nested and has_child:
            result.add_issue(
                ValidationLevel.WARNING,
                "Both component formats provided, nested 'components' will take precedence",
                f"{path}.properties.buem",
                suggestion="Use only one component format for clarity"
            )
    
    def _validate_time_consistency(self, features: List[Dict], result: ValidationResult):
        """Validate time range consistency."""
        for i, feature in enumerate(features):
            props = feature.get('properties', {})
            start_time = props.get('start_time')
            end_time = props.get('end_time')
            
            if start_time and end_time:
                if isinstance(start_time, str):
                    start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                if isinstance(end_time, str):
                    end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                
                if start_time >= end_time:
                    result.add_issue(
                        ValidationLevel.ERROR,
                        "end_time must be after start_time",
                        f"features[{i}].properties",
                        suggestion="Check time range validity"
                    )
    
    def _convert_components_format(self, data: Dict, result: ValidationResult):
        """Convert child_components to nested components format if needed."""
        for i, feature in enumerate(data.get('features', [])):
            buem_data = feature.get('properties', {}).get('buem', {})
            building_attrs = buem_data.get('building_attributes', {})
            child_components = buem_data.get('child_components', [])
            
            # If no nested components but have child_components, convert
            if (not building_attrs.get('components') and child_components):
                try:
                    converted = self._child_to_nested_components(child_components)
                    building_attrs['components'] = converted
                    result.add_issue(
                        ValidationLevel.INFO,
                        "Converted child_components to nested components format",
                        f"features[{i}].properties.buem.building_attributes"
                    )
                except Exception as e:
                    result.add_issue(
                        ValidationLevel.ERROR,
                        f"Failed to convert child_components: {str(e)}",
                        f"features[{i}].properties.buem.child_components"
                    )
    
    def _child_to_nested_components(self, child_components: List[Dict]) -> Dict[str, Any]:
        """Convert child_components array to nested components structure."""
        components = {}
        
        # Group by component type
        for child in child_components:
            comp_type = child['component_type'].lower()
            
            # Map component types
            if comp_type == 'wall':
                comp_key = 'Walls'
            elif comp_type == 'roof':
                comp_key = 'Roof'
            elif comp_type == 'floor':
                comp_key = 'Floor'
            elif comp_type == 'window':
                comp_key = 'Windows'
            elif comp_type == 'door':
                comp_key = 'Doors'
            else:
                comp_key = comp_type.title()
            
            if comp_key not in components:
                components[comp_key] = {'elements': []}
            
            # Convert to element format
            element = {
                'id': child['component_id'],
                'area': child['area_m2'],
                'azimuth': child['orientation_deg'],
                'tilt': child['tilt_deg']
            }
            
            if child.get('u_value'):
                element['U'] = child['u_value']
            if child.get('surface_reference'):
                element['surface'] = child['surface_reference']
            
            components[comp_key]['elements'].append(element)
        
        # Set default U-values if not provided per-element
        default_u_values = {
            'Walls': 1.6,
            'Roof': 1.5,
            'Floor': 1.7,
            'Windows': 2.5,
            'Doors': 3.5
        }
        
        for comp_key, comp_data in components.items():
            elements = comp_data['elements']
            has_element_u = any(elem.get('U') for elem in elements)
            
            if not has_element_u and comp_key in default_u_values:
                comp_data['U'] = default_u_values[comp_key]
            
            # Add special properties for windows
            if comp_key == 'Windows':
                comp_data['g_gl'] = 0.5  # Default solar gain
        
        return components
    
    def _process_marshmallow_errors(self, errors: Dict, result: ValidationResult):
        """Process marshmallow validation errors."""
        self._flatten_errors(errors, result, "")
    
    def _flatten_errors(self, errors: Union[Dict, List, str], result: ValidationResult, path: str):
        """Recursively flatten nested error messages."""
        if isinstance(errors, dict):
            for key, value in errors.items():
                new_path = f"{path}.{key}" if path else key
                self._flatten_errors(value, result, new_path)
        elif isinstance(errors, list):
            for error in errors:
                result.add_issue(
                    ValidationLevel.ERROR,
                    str(error),
                    path,
                    suggestion="Check value format and constraints"
                )
        else:
            result.add_issue(
                ValidationLevel.ERROR,
                str(errors),
                path,
                suggestion="Check value format and constraints"
            )


def validate_geojson_request(payload: Dict[str, Any], strict_mode: bool = False) -> ValidationResult:
    """
    Convenience function to validate GeoJSON request.
    
    Parameters
    ----------
    payload : Dict[str, Any]
        GeoJSON payload to validate.
    strict_mode : bool
        Treat warnings as errors.
        
    Returns
    -------
    ValidationResult
        Validation results with detailed error reporting.
    """
    validator = GeoJsonValidator(strict_mode=strict_mode)
    return validator.validate(payload)


def create_validation_report(result: ValidationResult) -> str:
    """
    Create a detailed validation report.
    
    Parameters
    ----------
    result : ValidationResult
        Validation result to report.
        
    Returns
    -------
    str
        Formatted validation report.
    """
    report = [f"=== VALIDATION REPORT ==="]
    report.append(f"Status: {result.summary()}")
    report.append("")
    
    if result.get_errors():
        report.append("ERRORS:")
        for issue in result.get_errors():
            report.append(f"  ❌ {issue.path}: {issue.message}")
            if issue.suggestion:
                report.append(f"     💡 Suggestion: {issue.suggestion}")
        report.append("")
    
    if result.get_warnings():
        report.append("WARNINGS:")
        for issue in result.get_warnings():
            report.append(f"  ⚠️  {issue.path}: {issue.message}")
            if issue.suggestion:
                report.append(f"     💡 Suggestion: {issue.suggestion}")
        report.append("")
    
    info_issues = [i for i in result.issues if i.level == ValidationLevel.INFO]
    if info_issues:
        report.append("INFO:")
        for issue in info_issues:
            report.append(f"  ℹ️  {issue.path}: {issue.message}")
        report.append("")
    
    return "\n".join(report)