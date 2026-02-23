Architecture
============

BuEM (Building Energy Model) system architecture and component overview.

System Overview
---------------

BuEM is designed as a modular building energy modeling system with the following key components:

.. mermaid::
   :caption: BuEM System Architecture

   graph TB
       A["API Gateway<br/>(Flask/Gunicorn)"] --> B["GeoJSON Processor"]
       B --> C["Building Validator"]
       C --> D["Thermal Model"]
       D --> E["Occupancy Model"]
       E --> F["Technology Model"]
       F --> G["Results Generator"]
       
       H["Weather Data"] --> D
       I["Configuration"] --> C
       J["Building Database"] --> B
       G --> K["Results Storage"]

Core Components
---------------

**API Server (apis/api_server.py)**
  - RESTful API endpoint for building analysis
  - GeoJSON format input/output
  - Request validation and error handling
  - Authentication and rate limiting

**GeoJSON Processor (integration/geojson_processor.py)**
  - Parses GeoJSON building data
  - Extracts building attributes and geometry
  - Handles multiple building collections
  - Validates coordinate systems

**Configuration System (config/)**
  - Building attribute validation (cfg_attribute.py)
  - Component specifications (cfg_building.py)
  - Dynamic validation rules (validator.py)
  - JSON-based configuration (cfg_attribute.json)

**Thermal Model (thermal/model_buem.py)**
  - Building thermal calculations
  - Heat transfer computations
  - Energy demand estimation
  - Weather data integration

**Occupancy Model (occupancy/)**
  - Electricity consumption patterns (electricity_consumption.py)
  - Occupancy profiles (occupancy_profile.py)
  - Time-series generation
  - Load distribution modeling

**Technology Integration (technology/)**
  - Existing technologies (existing/fireplace.py)
  - New technologies (new/heatpump.py)
  - Performance modeling
  - Efficiency calculations

**Weather Data Management (weather/)**
  - CSV data import (from_csv.py)
  - Time-series weather data
  - Geographic interpolation
  - Caching mechanisms

Data Flow
---------

1. **Request Processing**:
   - Client sends GeoJSON data to API endpoint
   - Request validation and authentication
   - GeoJSON parsing and building extraction

2. **Building Analysis**:
   - Configuration validation using cfg_attribute rules
   - Geometric processing and attribute extraction
   - Weather data lookup for building location

3. **Energy Modeling**:
   - Thermal model initialization with building parameters
   - Occupancy pattern generation
   - Technology performance calculation
   - Energy demand computation

4. **Result Generation**:
   - Time-series energy data compilation
   - Result formatting in GeoJSON structure
   - Statistical analysis and aggregation
   - Response transmission to client

Storage Architecture
--------------------

**File-Based Storage**:
  - Weather data: CSV files in data/weather/
  - Configuration: JSON files in config/
  - Results cache: JSON files in results/
  - Logs: Structured logging in logs/

**Memory Management**:
  - Weather data caching for frequently accessed locations
  - Building attribute validation cache
  - Result caching for repeated building configurations
  - Session-based request tracking

API Design Patterns
-------------------

**Resource-Based Endpoints**:
  - ``/api/geojson`` - Main building analysis endpoint
  - ``/health`` - Service health monitoring
  - ``/metrics`` - Performance metrics (optional)
  - ``/docs`` - API documentation

**Request/Response Format**:
  - Standard GeoJSON FeatureCollection format
  - Embedded building attributes in feature properties
  - Consistent error response structure
  - Pagination support for large datasets

**Error Handling**:
  - HTTP status codes for different error types
  - Structured error messages with details
  - Request validation with specific field errors
  - Graceful degradation for partial failures

Scalability Considerations
--------------------------

**Horizontal Scaling**:
  - Stateless API design for load balancing
  - Containerized deployment (Docker)
  - Microservice architecture support
  - Database-agnostic design

**Performance Optimization**:
  - Weather data caching strategies
  - Batch processing capabilities
  - Asynchronous processing options
  - Memory-efficient data structures

**Extension Points**:
  - Plugin architecture for new technologies
  - Configurable validation rules
  - Modular component design
  - External data source integration

Security Architecture
---------------------

**API Security**:
  - Optional API key authentication
  - Request rate limiting
  - Input validation and sanitization
  - CORS configuration

**Data Protection**:
  - No persistent storage of building data
  - Configurable logging levels
  - Secure weather data access
  - Container-based isolation

For implementation details, see :doc:`implementation_details` and :doc:`../api_integration/overview`.