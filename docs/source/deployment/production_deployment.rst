Production Deployment
====================

Guide for deploying BuEM in production environments.

Deployment Overview
------------------

BuEM can be deployed in several production configurations:

- **Standalone Docker Container**: Single-node deployment
- **Docker Swarm**: Multi-node orchestration
- **Kubernetes**: Container orchestration platform
- **Cloud Services**: AWS ECS, Azure Container Instances, GCP Cloud Run

Docker Swarm Deployment
-----------------------

**Initialize Swarm:**

.. code-block:: bash

    # Initialize swarm on manager node
    docker swarm init
    
    # Join worker nodes
    docker swarm join --token <worker-token> <manager-ip>:2377

**Deploy Stack:**

Create ``docker-compose.prod.yml``:

.. code-block:: yaml

    version: '3.8'
    services:
      buem-api:
        image: buem:production
        ports:
          - "5000:5000"
        environment:
          - BUEM_LOG_LEVEL=INFO
          - GUNICORN_WORKERS=4
        volumes:
          - weather-data:/app/data/weather:ro
        deploy:
          replicas: 3
          restart_policy:
            condition: on-failure
            delay: 5s
            max_attempts: 3
          resources:
            limits:
              cpus: '0.5'
              memory: 512M
      
      nginx:
        image: nginx:alpine
        ports:
          - "80:80"
          - "443:443"
        configs:
          - source: nginx_config
            target: /etc/nginx/nginx.conf
        depends_on:
          - buem-api
    
    volumes:
      weather-data:
        external: true
    
    configs:
      nginx_config:
        file: ./nginx.conf

**Deploy:**

.. code-block:: bash

    docker stack deploy -c docker-compose.prod.yml buem-stack

Kubernetes Deployment
--------------------

**Deployment Configuration:**

.. code-block:: yaml

    # buem-deployment.yaml
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: buem-api
      labels:
        app: buem-api
    spec:
      replicas: 3
      selector:
        matchLabels:
          app: buem-api
      template:
        metadata:
          labels:
            app: buem-api
        spec:
          containers:
          - name: buem-api
            image: buem:production
            ports:
            - containerPort: 5000
            env:
            - name: BUEM_LOG_LEVEL
              value: "INFO"
            volumeMounts:
            - name: weather-data
              mountPath: /app/data/weather
              readOnly: true
            resources:
              limits:
                cpu: 500m
                memory: 512Mi
              requests:
                cpu: 250m
                memory: 256Mi
          volumes:
          - name: weather-data
            persistentVolumeClaim:
              claimName: weather-data-pvc

**Service Configuration:**

.. code-block:: yaml

    # buem-service.yaml
    apiVersion: v1
    kind: Service
    metadata:
      name: buem-api-service
    spec:
      selector:
        app: buem-api
      ports:
      - protocol: TCP
        port: 80
        targetPort: 5000
      type: LoadBalancer

**Deploy to Kubernetes:**

.. code-block:: bash

    kubectl apply -f buem-deployment.yaml
    kubectl apply -f buem-service.yaml
    
    # Check status
    kubectl get pods
    kubectl get services

Load Balancer Configuration
---------------------------

**Nginx Configuration:**

.. code-block:: nginx

    upstream buem_backend {
        least_conn;
        server buem-api-1:5000;
        server buem-api-2:5000;
        server buem-api-3:5000;
    }
    
    server {
        listen 80;
        server_name your-domain.com;
        
        location / {
            proxy_pass http://buem_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Timeout settings
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }
        
        location /health {
            access_log off;
            proxy_pass http://buem_backend/health;
        }
    }

Monitoring and Logging
----------------------

**Health Check Endpoint:**

.. code-block:: python

    # Add to api_server.py
    @app.route('/health')
    def health_check():
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": buem.__version__
        }

**Prometheus Metrics:**

.. code-block:: python

    from prometheus_client import Counter, Histogram, generate_latest
    
    REQUEST_COUNT = Counter('buem_requests_total', 'Total requests')
    REQUEST_LATENCY = Histogram('buem_request_duration_seconds', 'Request latency')
    
    @app.before_request
    def before_request():
        request.start_time = time.time()
    
    @app.after_request
    def after_request(response):
        REQUEST_COUNT.inc()
        REQUEST_LATENCY.observe(time.time() - request.start_time)
        return response
    
    @app.route('/metrics')
    def metrics():
        return generate_latest()

Security Considerations
-----------------------

**API Key Authentication:**

.. code-block:: python

    @app.before_request
    def require_api_key():
        if request.endpoint in ['metrics', 'health']:
            return
        
        api_key = request.headers.get('X-API-Key')
        if not api_key or not validate_api_key(api_key):
            return {'error': 'Invalid API key'}, 401

**Rate Limiting:**

.. code-block:: python

    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    
    limiter = Limiter(
        app,
        key_func=get_remote_address,
        default_limits=["100 per hour"]
    )
    
    @app.route('/api/geojson')
    @limiter.limit("10 per minute")
    def process_geojson():
        # API implementation

For more deployment options, see :doc:`cloud_providers` and :doc:`scaling_strategies`.