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