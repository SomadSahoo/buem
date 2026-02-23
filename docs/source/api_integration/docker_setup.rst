Docker Setup and Deployment
============================

BuEM is designed to run in Docker containers for easy deployment and integration with other containerized systems.

Prerequisites
-------------

- Docker Engine 20.10 or later
- Docker Compose 2.0 or later (optional, for multi-service setup)
- Minimum 2GB available memory
- Network access for downloading dependencies

Building the Container
----------------------

**Option 1: Using provided Dockerfile**

.. code-block:: bash

    # Clone the repository
    git clone <buem-repository-url>
    cd buem
    
    # Build the container
    docker build -t buem:latest .

**Option 2: Using Docker Compose**

.. code-block:: bash

    # Use the provided docker-compose.yml
    docker-compose build buem

Container Configuration
-----------------------

**Environment Variables**

The BuEM container supports the following environment variables:

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Variable
     - Default
     - Description
   * - ``BUEM_WEATHER_DIR``
     - ``/app/data``
     - Directory containing weather data files
   * - ``BUEM_RESULTS_DIR``
     - ``/app/results``
     - Directory for saving timeseries output files
   * - ``FLASK_PORT``
     - ``5000``
     - Port for the API server
   * - ``FLASK_HOST``
     - ``0.0.0.0``
     - Host binding for the API server

**Volume Mounts**

Essential directories to mount:

.. code-block:: bash

    docker run -d \\
      -p 5000:5000 \\
      -v /host/path/to/weather:/app/data/weather \\
      -v /host/path/to/results:/app/results \\
      -e BUEM_WEATHER_DIR=/app/data/weather \\
      buem:latest

Running the Container
---------------------

**Single Container**

.. code-block:: bash

    docker run -d \\
      --name buem-api \\
      -p 5000:5000 \\
      -v $(pwd)/data/weather:/app/data/weather \\
      -v $(pwd)/results:/app/results \\
      buem:latest

**With Docker Compose**

Create a ``docker-compose.yml``:

.. code-block:: yaml

    version: '3.8'
    services:
      buem:
        build: .
        ports:
          - "5000:5000"
        volumes:
          - ./data/weather:/app/data/weather
          - ./results:/app/results
        environment:
          - BUEM_WEATHER_DIR=/app/data/weather
          - BUEM_RESULTS_DIR=/app/results
        restart: unless-stopped

    networks:
      default:
        driver: bridge

Then run:

.. code-block:: bash

    docker-compose up -d

Health Checks
-------------

**API Health Endpoint**

Check if the container is running properly:

.. code-block:: bash

    curl http://localhost:5000/api/health

Expected response:

.. code-block:: json

    {
      "status": "healthy",
      "version": "1.0.0",
      "timestamp": "2026-02-23T10:30:00Z"
    }

**Container Logs**

Monitor container logs:

.. code-block:: bash

    # For docker run
    docker logs buem-api
    
    # For docker-compose
    docker-compose logs buem

Security Considerations
-----------------------

**Network Security**
- Run containers on internal networks when possible
- Use reverse proxy (nginx/traefik) for external access
- Implement API authentication if required

**Data Security**
- Weather data directory should be read-only mounted
- Results directory needs write permissions
- Consider using Docker secrets for sensitive configuration

**Resource Limits**

Set appropriate resource limits:

.. code-block:: bash

    docker run -d \\
      --memory=2g \\
      --cpus=1.0 \\
      --name buem-api \\
      buem:latest

Integration with Other Services
-------------------------------

**With Database Services**

.. code-block:: yaml

    services:
      buem:
        # ... buem configuration
        depends_on:
          - database
      
      database:
        image: postgres:13
        environment:
          POSTGRES_DB: buildings
          POSTGRES_USER: buem
          POSTGRES_PASSWORD: secure_password

**With Load Balancer**

For production deployments, consider using multiple instances:

.. code-block:: yaml

    services:
      buem:
        # ... buem configuration
        deploy:
          replicas: 3
      
      nginx:
        image: nginx:alpine
        ports:
          - "80:80"
        volumes:
          - ./nginx.conf:/etc/nginx/nginx.conf

Troubleshooting
---------------

**Common Issues**

1. **Weather data not found**: Ensure proper volume mounting and file permissions
2. **Port conflicts**: Check that port 5000 is available
3. **Memory issues**: Increase container memory limits for large building datasets

**Debug Mode**

Run container in debug mode:

.. code-block:: bash

    docker run -it --rm \\
      -p 5000:5000 \\
      -e FLASK_ENV=development \\
      buem:latest

Next Steps
----------

Once your container is running, proceed to :doc:`api_endpoints` to learn about the available API endpoints.