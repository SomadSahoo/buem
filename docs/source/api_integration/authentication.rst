Authentication
==============

Currently, BuEM API does not implement authentication by default. This section outlines authentication strategies for production deployments.

Current Status
--------------

The BuEM API is designed to run in trusted environments without built-in authentication. This simplifies development and testing but requires additional security measures for production use.

Production Authentication Options
---------------------------------

**API Key Authentication**

Implement API key validation at the reverse proxy level:

.. code-block:: nginx

    location /api/ {
        # Validate API key header
        if ($http_x_api_key != "your-secret-api-key") {
            return 401 "Unauthorized";
        }
        proxy_pass http://buem-backend;
    }

**OAuth 2.0 Integration**

For enterprise integration, implement OAuth 2.0 with your identity provider:

.. code-block:: python

    import requests
    from authlib.integrations.requests_client import OAuth2Session

    # Get access token
    client = OAuth2Session(
        client_id='your-client-id',
        client_secret='your-client-secret'
    )
    token = client.fetch_token(
        'https://your-oauth-provider/token',
        grant_type='client_credentials'
    )

    # Use token for API requests
    headers = {'Authorization': f'Bearer {token["access_token"]}'}
    response = requests.post(
        'http://buem-api/geojson',
        headers=headers,
        json=building_data
    )

**Mutual TLS (mTLS)**

For high-security environments, use client certificates:

.. code-block:: bash

    # Generate client certificate
    openssl genrsa -out client.key 2048
    openssl req -new -key client.key -out client.csr
    openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -out client.crt

.. code-block:: python

    # Use client certificate for requests
    import requests
    
    response = requests.post(
        'https://buem-api/geojson',
        cert=('client.crt', 'client.key'),
        verify='ca.crt',
        json=building_data
    )

Network Security
----------------

**VPN/Private Networks**

Deploy BuEM in private networks accessible only through VPN:

.. code-block:: yaml

    # docker-compose.yml
    version: '3.8'
    services:
      buem:
        image: buem:latest
        networks:
          - private-network
    
    networks:
      private-network:
        driver: bridge
        internal: true

**IP Whitelisting**

Restrict access to known IP addresses:

.. code-block:: nginx

    location /api/ {
        allow 192.168.1.0/24;
        allow 10.0.0.0/8;
        deny all;
        proxy_pass http://buem-backend;
    }

Implementation Examples
-----------------------

**Simple API Key Middleware**

.. code-block:: python

    from flask import Flask, request, jsonify
    import os

    app = Flask(__name__)
    REQUIRED_API_KEY = os.environ.get('BUEM_API_KEY')

    @app.before_request
    def validate_api_key():
        if not REQUIRED_API_KEY:
            return  # Skip validation if no key configured
        
        api_key = request.headers.get('X-API-Key')
        if api_key != REQUIRED_API_KEY:
            return jsonify({
                'error': {
                    'code': 'UNAUTHORIZED',
                    'message': 'Invalid or missing API key'
                }
            }), 401

**Client Implementation with API Key**

.. code-block:: python

    import requests
    import os

    class BuEMClient:
        def __init__(self, base_url, api_key=None):
            self.base_url = base_url.rstrip('/')
            self.api_key = api_key or os.environ.get('BUEM_API_KEY')
        
        def _get_headers(self):
            headers = {'Content-Type': 'application/json'}
            if self.api_key:
                headers['X-API-Key'] = self.api_key
            return headers
        
        def analyze_building(self, building_data, include_timeseries=False):
            url = f'{self.base_url}/api/geojson'
            params = {'include_timeseries': include_timeseries}
            
            response = requests.post(
                url, 
                headers=self._get_headers(),
                params=params,
                json=building_data
            )
            
            if response.status_code == 401:
                raise AuthenticationError('Invalid API key')
            elif response.status_code != 200:
                raise APIError(f'Request failed: {response.status_code}')
            
            return response.json()

    # Usage
    client = BuEMClient('http://localhost:5000', api_key='your-api-key')
    results = client.analyze_building(building_data)

Best Practices
--------------

**Development vs Production**

- Development: No authentication for easier testing
- Staging: API key authentication for integration testing  
- Production: OAuth 2.0 or mTLS for enterprise security

**Key Management**

- Store API keys in environment variables, never in code
- Rotate keys regularly
- Use different keys for different environments
- Monitor key usage and implement rate limiting

**Security Headers**

.. code-block:: nginx

    # Add security headers
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

Next Steps
----------

Continue to :doc:`examples` for complete integration examples including authentication.