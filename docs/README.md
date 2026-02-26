# 📚 BuEM Documentation

**Complete documentation for the Building Energy Model (BuEM) - specifically designed for developers integrating with other energy modeling systems via APIs.**

![BuEM Documentation](https://img.shields.io/badge/docs-ReadTheDocs-blue)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## 🎯 **Documentation Focus**

This documentation is **developer-oriented** for teams integrating BuEM with:
- District energy systems
- Building management platforms  
- Urban planning tools
- Energy optimization frameworks

### **Target Audience**: Software developers building energy analysis pipelines

## 🚀 **Quick Start**

**Installation Methods:**
- **Conda Environment** (recommended): `conda env create -f environment.yml`
- **PyPI**: `pip install buem`  
- **Docker**: `docker compose up`

**Important**: When using conda environment, run commands with `python -m src.buem.main` to avoid import conflicts.

---

## 📖 **Documentation Structure**

### 📁 **Main Sections**

| Section | Description | Key Content |
|---------|-------------|-------------|
| **[Introduction](source/introduction/index.rst)** | Overview and capabilities | Project scope, use cases, target users |
| **[API Integration](source/api_integration/index.rst)** | Complete integration guide | Docker setup, REST API, GeoJSON processing |
| **[Model Attributes](source/model_attributes/index.rst)** | Building specification reference | Component definitions, validation rules |
| **[Technical Reference](source/technical/index.rst)** | Implementation details | Algorithms, architecture, performance |
| **[Installation](source/installation/index.rst)** | Setup instructions | Conda, Docker, production deployment |
| **[Examples](source/examples/index.rst)** | Practical integration examples | Complete code samples, error handling |

---

## 🔧 **Configuration Files**

| File | Purpose | Usage |
|------|---------|-------|
| **[.readthedocs.yaml](../.readthedocs.yaml)** | ReadTheDocs hosting config | Automatic docs deployment |
| **[source/conf.py](source/conf.py)** | Sphinx configuration | Documentation generation |
| **[requirements.txt](requirements.txt)** | Documentation dependencies | ReadTheDocs builds |
| **[Makefile](Makefile)** / **[make.bat](make.bat)** | Build scripts | Local documentation generation |

---

## 🚀 **Quick Start**

### **View Online Documentation**
- **Production**: `https://buem.readthedocs.io/` *(when deployed)*
- **Latest Build**: Automatically updated on repository push

### **Build Documentation Locally**

**Prerequisites:**
```bash
# Activate BuEM conda environment
conda activate buem_env

# Install documentation dependencies (if not already done)
conda env update -f ../environment.yml
```

**Build Commands:**
```bash
# Navigate to docs directory
cd docs

# Build HTML documentation
make html          # Linux/macOS
# or
make.bat html      # Windows

# View results
open build/html/index.html  # macOS
start build/html/index.html # Windows
xdg-open build/html/index.html # Linux
```

**Alternative build (using sphinx directly):**
```bash
sphinx-build -b html source build
```

---

## 📖 **API Integration Documentation**

### **Complete Developer Guide Includes:**

#### 🐳 **[Docker Integration](source/api_integration/docker_setup.rst)**
- Container deployment strategies
- Environment variable configuration  
- Volume mounting for weather data
- Production deployment patterns

#### 🔌 **[REST API Reference](source/api_integration/api_endpoints.rst)**
- **`POST /api/geojson`** - Building analysis endpoint
- **`GET /api/files/{filename}`** - Timeseries data download
- **`GET /api/health`** - Service health check
- Complete request/response examples

#### 📊 **[Data Exchange Formats](source/api_integration/request_format.rst)**
- **Input**: GeoJSON FeatureCollection with building attributes
- **Output**: GeoJSON with thermal load results + compressed timeseries
- **Validation**: Comprehensive error handling and validation rules

#### 📈 **[Timeseries Processing](source/api_integration/response_format.rst)**
- Hourly heating/cooling load data (8760 points)
- Compressed `.json.gz` file format
- Download and processing workflows

---

## 🏗️ **Model Attributes Documentation**

### **Building Specification Reference:**

#### 📐 **[Component System](source/model_attributes/component_definitions.rst)**
```json
{
  "components": {
    "Walls": {"U": 1.5, "elements": [...]},
    "Roof": {"U": 1.0, "elements": [...]}, 
    "Windows": {"U": 2.8, "g_gl": 0.6, "elements": [...]},
    "Ventilation": {"elements": [...]}
  }
}
```

#### ⚙️ **[Attribute Categories](source/model_attributes/attribute_categories.rst)**
- **WEATHER**: Climate data and geographic location
- **FIXED**: Building geometry and thermal properties
- **BOOLEAN**: Control flags and simulation options
- **OTHER**: Complex structured data (components, profiles)

#### ✅ **[Validation Rules](source/model_attributes/validation_rules.rst)**
- Physical consistency checks
- Geometric constraint validation
- Value range enforcement
- Cross-reference verification

---

## 💻 **Integration Examples**

### **Complete Code Examples:**

#### 🔹 **[Basic Building Analysis](source/examples/basic_api_usage.rst)**
```python
# Simple single building request
response = requests.post('/api/geojson', json=building_data)
thermal_loads = response.json()['features'][0]['properties']['buem']
```

#### 🔹 **[Batch Processing](source/examples/batch_processing.rst)**
```python
# Multiple buildings in single request
feature_collection = {"type": "FeatureCollection", "features": buildings}
results = requests.post('/api/geojson', json=feature_collection)
```

#### 🔹 **[Error Handling](source/examples/error_handling_examples.rst)**
```python
# Robust integration with retry logic
try:
    response = buem_client.analyze_buildings(buildings)
except BuEMAPIError as e:
    handle_validation_error(e.response_data)
```

#### 🔹 **[Timeseries Processing](source/examples/basic_api_usage.rst)**
```python
# Download and analyze hourly data
timeseries_url = thermal['timeseries_file']
hourly_data = download_and_decompress(timeseries_url)
```

---

## 📚 **Documentation Maintenance**

### **Dependency Management**

**For Local Development:**
- Dependencies defined in **[../environment.yml](../environment.yml)**
- Includes Sphinx, theme, and extensions
- Use: `conda env update -f ../environment.yml`

**For ReadTheDocs:**
- Dependencies in **[requirements.txt](requirements.txt)**
- ReadTheDocs uses pip internally
- Automatically installed during builds

**For Development Tools:**
```bash
# Install with documentation extras
pip install -e ".[docs]"

# Or using conda environment (recommended)
conda activate buem_env
```

### **Version Management**
- Documentation version automatically synced with **[../pyproject.toml](../pyproject.toml)**
- Version: `0.1.2` (automatically updated)
- Release info in **[source/conf.py](source/conf.py)**

### **Content Updates**

**When to Update Documentation:**
- ✅ New API endpoints added
- ✅ Building attribute specifications change  
- ✅ Integration patterns evolve
- ✅ Error handling improvements
- ✅ New deployment options

**Update Process:**
1. Edit `.rst` files in **[source/](source/)**
2. Build locally: `make html`
3. Test changes: open `build/html/index.html`
4. Commit and push (triggers automatic ReadTheDocs build)

---

## 🌐 **Deployment and Hosting**

### **ReadTheDocs Integration**
- **Configuration**: **[../.readthedocs.yaml](../.readthedocs.yaml)**
- **Hosting URL**: `https://buem.readthedocs.io/`
- **Auto-deployment**: Triggered on repository push
- **Build logs**: Available in ReadTheDocs dashboard

### **Local Development Server**
```bash
# Serve documentation locally with auto-reload
sphinx-autobuild source build/html
# Access at: http://localhost:8000
```

---

## 🤝 **Contributing**

**Documentation Contributions Welcome!**

- **Guidelines**: See **[../CONTRIBUTE.md](../CONTRIBUTE.md)**
- **Style Guide**: RestructuredText with RTD theme
- **Review Process**: Technical accuracy + integration focus
- **Target**: Developer-friendly, integration-oriented content

### **Contribution Areas**
- 🔧 API integration patterns
- 📊 Real-world use cases  
- 🐛 Error handling scenarios
- 📈 Performance optimization
- 🔗 External system integration

---

## 📞 **Support**

**Documentation Questions:**
- Create issue in repository
- Tag: `documentation`
- Include: section reference + suggested improvement

**Integration Support:**
- Focus on API usage questions
- Include: code examples + error messages
- Response time: 1-2 business days

---

## 📊 **Documentation Metrics**

| Metric | Status |
|--------|--------|
| **Total Sections** | 6 main sections |
| **API Endpoints** | 3 documented endpoints |
| **Code Examples** | 15+ complete examples |
| **Building Attributes** | 40+ documented attributes |
| **Integration Patterns** | 5+ proven patterns |
| **Error Scenarios** | 10+ handled cases |

---

**🎯 Ready for Integration? Start with [API Integration Guide](source/api_integration/index.rst)**