Cloud Provider Deployment
=========================

Deploying BuEM on major cloud platforms.

AWS Deployment
--------------

**AWS ECS with Fargate:**

.. code-block:: json

    {
      "family": "buem-api",
      "networkMode": "awsvpc", 
      "requiresCompatibilities": ["FARGATE"],
      "cpu": "512",
      "memory": "1024",
      "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
      "containerDefinitions": [
        {
          "name": "buem-api",
          "image": "your-account.dkr.ecr.region.amazonaws.com/buem:latest",
          "portMappings": [
            {
              "containerPort": 5000,
              "protocol": "tcp"
            }
          ],
          "environment": [
            {
              "name": "BUEM_LOG_LEVEL",
              "value": "INFO"
            }
          ],
          "logConfiguration": {
            "logDriver": "awslogs",
            "options": {
              "awslogs-group": "/ecs/buem-api",
              "awslogs-region": "us-west-2",
              "awslogs-stream-prefix": "ecs"
            }
          }
        }
      ]
    }

**Deploy with AWS CLI:**

.. code-block:: bash

    # Register task definition
    aws ecs register-task-definition --cli-input-json file://task-definition.json
    
    # Create ECS service
    aws ecs create-service \
        --cluster buem-cluster \
        --service-name buem-api-service \
        --task-definition buem-api \
        --desired-count 3 \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx,subnet-yyy],securityGroups=[sg-xxx]}"

**AWS Lambda for Event-Driven Processing:**

.. code-block:: python

    # lambda_function.py
    import json
    import boto3
    from buem.thermal.model_buem import process_building
    
    def lambda_handler(event, context):
        # Process building from S3 trigger or API Gateway
        building_data = json.loads(event['body']) if 'body' in event else event
        
        try:
            result = process_building(building_data)
            
            # Store result in S3
            s3 = boto3.client('s3')
            s3.put_object(
                Bucket='buem-results',
                Key=f"results/{building_data['id']}.json",
                Body=json.dumps(result)
            )
            
            return {
                'statusCode': 200,
                'body': json.dumps(result)
            }
        except Exception as e:
            return {
                'statusCode': 500,
                'body': json.dumps({'error': str(e)})
            }

Azure Deployment
----------------

**Azure Container Instances:**

.. code-block:: yaml

    # buem-aci.yaml
    apiVersion: 2021-03-01
    location: eastus
    name: buem-api-group
    properties:
      containers:
      - name: buem-api
        properties:
          image: your-registry.azurecr.io/buem:latest
          resources:
            requests:
              cpu: 1
              memoryInGb: 2
          ports:
          - port: 5000
            protocol: TCP
          environmentVariables:
          - name: BUEM_LOG_LEVEL
            value: INFO
      osType: Linux
      restartPolicy: Always
      ipAddress:
        type: Public
        ports:
        - protocol: tcp
          port: 5000

**Deploy with Azure CLI:**

.. code-block:: bash

    # Create resource group
    az group create --name buem-rg --location eastus
    
    # Deploy container group
    az container create \
        --resource-group buem-rg \
        --file buem-aci.yaml

**Azure Functions:**

.. code-block:: python

    # function_app.py
    import azure.functions as func
    import json
    from buem.thermal.model_buem import process_building
    
    def main(req: func.HttpRequest) -> func.HttpResponse:
        try:
            building_data = req.get_json()
            result = process_building(building_data)
            
            return func.HttpResponse(
                json.dumps(result),
                status_code=200,
                headers={'Content-Type': 'application/json'}
            )
        except Exception as e:
            return func.HttpResponse(
                json.dumps({'error': str(e)}),
                status_code=500
            )

Google Cloud Deployment
-----------------------

**Cloud Run Service:**

.. code-block:: yaml

    # service.yaml
    apiVersion: serving.knative.dev/v1
    kind: Service
    metadata:
      name: buem-api
      annotations:
        run.googleapis.com/ingress: all
    spec:
      template:
        metadata:
          annotations:
            autoscaling.knative.dev/maxScale: "10"
            run.googleapis.com/memory: "2Gi"
            run.googleapis.com/cpu: "2"
        spec:
          containers:
          - image: gcr.io/your-project/buem:latest
            ports:
            - containerPort: 5000
            env:
            - name: BUEM_LOG_LEVEL
              value: INFO
            resources:
              limits:
                memory: 2Gi
                cpu: 2000m

**Deploy with gcloud:**

.. code-block:: bash

    # Build and push to Container Registry
    docker build -t gcr.io/your-project/buem:latest .
    docker push gcr.io/your-project/buem:latest
    
    # Deploy to Cloud Run
    gcloud run deploy buem-api \
        --image gcr.io/your-project/buem:latest \
        --platform managed \
        --region us-central1 \
        --allow-unauthenticated

**Cloud Functions:**

.. code-block:: python

    # main.py
    import functions_framework
    import json
    from buem.thermal.model_buem import process_building
    
    @functions_framework.http
    def buem_process(request):
        try:
            building_data = request.get_json()
            result = process_building(building_data)
            
            return json.dumps(result), 200, {'Content-Type': 'application/json'}
        except Exception as e:
            return json.dumps({'error': str(e)}), 500

Cost Optimization
-----------------

**AWS Spot Instances:**

.. code-block:: bash

    # Launch spot instances for batch processing
    aws ec2 request-spot-instances \
        --spot-price "0.05" \
        --instance-count 3 \
        --type "one-time" \
        --launch-specification file://spot-specification.json

**Azure Spot VMs:**

.. code-block:: bash

    # Create spot VM scale set
    az vmss create \
        --resource-group buem-rg \
        --name buem-vmss \
        --image UbuntuLTS \
        --priority Spot \
        --max-price 0.05 \
        --instance-count 3

**Google Cloud Preemptible Instances:**

.. code-block:: bash

    # Create preemptible instance group
    gcloud compute instance-groups managed create buem-group \
        --base-instance-name buem-instance \
        --size 3 \
        --template buem-template

Monitoring and Logging
----------------------

**AWS CloudWatch:**

.. code-block:: python

    import boto3
    
    def publish_custom_metric(metric_name, value, unit='Count'):
        cloudwatch = boto3.client('cloudwatch')
        cloudwatch.put_metric_data(
            Namespace='BuEM/API',
            MetricData=[
                {
                    'MetricName': metric_name,
                    'Value': value,
                    'Unit': unit
                }
            ]
        )

**Azure Application Insights:**

.. code-block:: python

    from applicationinsights import TelemetryClient
    
    tc = TelemetryClient('your-instrumentation-key')
    tc.track_metric('BuildingsProcessed', buildings_count)
    tc.track_request('POST /api/geojson', response_time, success=True)

**Google Cloud Monitoring:**

.. code-block:: python

    from google.cloud import monitoring_v3
    
    client = monitoring_v3.MetricServiceClient()
    project_name = f"projects/{project_id}"
    
    # Create custom metric
    series = monitoring_v3.TimeSeries()
    series.metric.type = 'custom.googleapis.com/buem/buildings_processed'
    series.resource.type = 'global'

For more cloud-specific configurations, see provider documentation and :doc:`scaling_strategies`.