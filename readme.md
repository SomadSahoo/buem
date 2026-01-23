# BUEM: Building Thermal Model

BUEM is a Python module for simulating building thermal behavior using the ISO 52016-1:2017 5R1C model.  
It supports solar gains, detailed heat load calculations, and the possibility to solve inequalities 
related to temperature ranges and other bounded conditions.

## Features

- 5R1C thermal model (ISO 52016-1)
- Refurbishment and insulation options
- Solar and internal gains
- Heating and cooling load calculation
- Plotting of results

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/somadsahoo/buem.git
   cd buem
   ```

2. Create and activate the conda environment:
   ```bash
   conda env create -f environment.yml
   conda activate buem_env
   ```

3. Install the BUEM module in editable mode:
   ```bash
   pip install -e .
   ```

## pip install 

To install as Library site package

```bash
   pip install buem
```

## Conda install (for advanced users)

To build and install with conda:

```bash
   conda install conda-build
   conda build .
   conda install --use-local buem
```

## Docker Setup and Usage

You can also run BUEM using Docker Compose for a fully reproducible environment.

### 1. Build and run with Docker Compose

From the project root, run:
```bash
docker compose up --build
```
This will build the Docker image (if needed) and run the model.

### 2. (Optional) Force a clean build

If you want to ensure everything is rebuilt from scratch:
```bash
docker compose build --no-cache
docker compose up
```

### Notes

- Output files (e.g., plots) will be saved to the `output/` directory if configured.
- You can modify the configuration or mount additional volumes as needed.

## Usage

### 1. Run the model via the main entry point

If you have installed BUEM with `pip install -e .` or `pip install .` (from the project root), you can run:

```bash
python -m buem.main
```

Or, if you installed via pip and set up the CLI script, you can simply run:
```bash
buem
```

### 2. Run the model without installing (development mode)

If you have **not** installed the package, but want to run it directly from the source, use:

```bash
python -m src.buem.main
```
(from the project root)

### 3. Import and use in your own scripts

You can also import the main class and use it programmatically:

```python
from buem.thermal.model_buem import ModelBUEM
from buem.config.cfg_attribute import cfg

model = ModelBUEM(cfg)
model.sim_model(use_inequality_constraints=False)
# Access results, plot, etc.
```

## API Implementation

This project includes a small Flask-based HTTP API for running models and processing GeoJSON.

1) Start the Flask application

- From the project root (development, running from source):

```bash
python -m src.buem.apis.api_server
```

- If the package is installed in your environment (recommended for production-like use):

```bash
python -m buem.apis.api_server
```

The server is configured to bind to host `0.0.0.0` and port `5000` by default (see [src/buem/apis/api_server.py](src/buem/apis/api_server.py)). Logs are written to the path set by the `BUEM_LOG_FILE` environment variable (defaults to `C:\test\buem\src\buem\logs\buem_api.log`). Large result files are stored in the directory set by `BUEM_RESULTS_DIR` (defaults to `C:\test\buem\results`).

2) Endpoints (summary)

- `GET /api/health` — basic health check, returns `{"status":"ok"}`.
- `POST /api/run` — run the building model once using a JSON config payload. Query parameter `include_timeseries=true` will include full time series arrays in the result. The request payload may include `use_milp` (boolean) and `forward_url` (string) to forward results to another HTTP endpoint.
- `GET|POST /api/process` — single entry point that accepts either a plain JSON config (same as `/api/run`) or a GeoJSON `Feature`/`FeatureCollection` containing `properties.buem`. When GeoJSON is provided the server returns a processed GeoJSON FeatureCollection with results attached to each feature. Query parameter `include_timeseries=true` will include full arrays in the GeoJSON output.
- `GET /api/files/<path:filename>` — download a previously saved result file from the results directory.

Steps 3), 4), and 5) are provide different ways to make an API call or test the application. 

3) Quick curl examples

- Health check

```bash
curl -i http://localhost:5000/api/health
```

- Run model with a JSON payload file (development)

```bash
curl -X POST "http://localhost:5000/api/run?include_timeseries=true" \
   -H "Content-Type: application/json" \
   --data-binary @payload.json
```

- Process a GeoJSON file (use the sample in the repository)

```bash
curl -X POST "http://localhost:5000/api/process?include_timeseries=false" \
   -H "Content-Type: application/json" \
   --data-binary @src/buem/integration/sample_request_template.geojson
```

- Forwarding results: include a `forward_url` in your JSON payload (the server will attempt to POST the result to that URL and include forwarding details in the response):

```json
{
   "forward_url": "https://example.com/receiver",
   "include_timeseries": false,
   "use_milp": false,
   ... other configuration fields ...
}
```

- Download a saved result file (timeseries files are saved as gzipped JSON with pattern `buem_ts_<hex>.json.gz`):

```bash
curl -O http://localhost:5000/api/files/buem_ts_<hex>.json.gz
```

4) Postman / GUI alternative

- Create a new request in Postman.
- Set the request URL to `http://localhost:5000/api/run` (or `/api/process`).
- Select `POST`.
- In `Headers` add `Content-Type: application/json`.
- Body:
   - For a GeoJSON file: choose `binary` and upload the GeoJSON file present in `.src/buem/intrgration/sample_request_template.geojson` (recommended for Feature/FeatureCollection posts).
   - For a JSON config: choose `raw` → `JSON` and paste the JSON config.
- Optionally append `?include_timeseries=true` to the URL to receive full time series.
- Send the request and inspect the JSON response; large outputs may include a `timeseries_file` field with a `/api/files/...json.gz` URL you can download.

5) Testing with a helper:

- A small python helper is provided `.src/buem/integration/send_geojson.py`that posts a 
GeoJSON file to the API (acts like curl). 
- Example of usage: 

```bash
python -m src/buem/integration/send_geojson.py src/buem/integration/sample_request_template.geojson --include-timeseries
```


6) Example minimal payload for `/api/run`

The model expects a configuration that matches `CfgBuilding` input. For testing you can use a small valid configuration or adapt the examples in the repository. Example skeleton (values must be replaced with real config):

```json
{
   "use_milp": false,
   "include_timeseries": false,
   "building": {
      "name": "Test Building",
      "geometry": {...}
   },
   ...
}
```

7) Getting results

- The `/api/run` and `/api/process` endpoints return JSON. When `include_timeseries=false` you will receive summarized totals and peaks under `heating` and `cooling` plus a `meta` block containing `elapsed_s`. When `include_timeseries=true` the response contains `index` (ISO timestamps) and `values` arrays.
- If the server was provided a `forward_url` it will attempt to POST the results to that URL and include a `forward` sub-object with the HTTP status and response text.
- For large result files the server may write outputs into `BUEM_RESULTS_DIR` and you can fetch them via the `/api/files/<filename>` endpoint.

7) Troubleshooting

- If you do not see logs, set `BUEM_LOG_FILE` to a writable file path and restart the server. Default is `C:\test\buem\src\buem\logs\buem_api.log`.
- If downloads fail, ensure `BUEM_RESULTS_DIR` exists and the server process has read permissions.

---

## Requirements

- Python 3.11+

Other python-based modules
--------------------------
- matplotlib
- numpy
- pandas
- pvlib
- scipy
- sympy
- openpyxl
- cvxpy

## Notes

- If you use Docker or Conda, follow the respective instructions above.
- Output files (e.g., plots) will be saved to the `output/` directory if configured.
- For custom configuration, edit the files in `src/buem/config/`.

---

## License

MIT