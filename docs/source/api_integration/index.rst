API Integration Guide
====================

This section provides comprehensive guidance for developers integrating BuEM (Building Energy Model) with other systems via REST APIs through Docker containers.

.. toctree::
   :maxdepth: 2

   overview
   docker_setup
   api_endpoints
   request_format
   response_format
   error_handling
   authentication
   examples

Overview
--------

BuEM provides a REST API that allows external systems to:

- Submit building energy model requests via GeoJSON format
- Receive thermal load calculations (heating/cooling)
- Download detailed timeseries data
- Integrate with other building simulation tools

The API is designed for synchronous operation and robust error handling to ensure reliable integration between models developed by different organizations.