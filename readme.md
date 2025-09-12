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

Run the example (with dummy data) from the command line:
```bash
python -m src.buem.thermal.modelbuem
```

Or import the `ModelBUEM` class in your own scripts:
```python
from buem.thermal.model_buem import ModelBUEM
```

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

## License

MIT