"""
BUEM Integration Scripts - Internal implementation modules.

This package contains implementation modules for BUEM integration.
For user-facing API, import from buem.integration directly:

    from buem.integration import BuemSchemaValidator, validate_request_file

Available modules:
- Core (always available): schema_manager, schema_validator, geojson_validator  
- Infrastructure-dependent: geojson_processor, attribute_builder, debug_utils
- Utilities: send_geojson
"""