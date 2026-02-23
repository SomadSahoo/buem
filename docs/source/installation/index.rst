Installation Guide
==================

This guide covers different installation methods for BuEM depending on your use case and environment.

.. toctree::
   :maxdepth: 2

   conda_setup
   docker_installation
   development_setup

Quick Start
-----------

**For API Integration (Recommended)**

Use the pre-built Docker container:

.. code-block:: bash

    docker pull buem:latest
    docker run -d -p 5000:5000 buem:latest

**For Development**

Set up the conda environment:

.. code-block:: bash

    git clone <buem-repository>
    cd buem
    conda env create -f environment.yml
    conda activate buem_env

Installation Options
--------------------

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Method
     - Use Case
     - Pros/Cons
   * - Docker Container
     - Production deployment, API integration
     - ✓ Easy deployment, ✓ Isolated environment, ⚠ Container overhead
   * - Conda Environment
     - Development, local analysis
     - ✓ Full control, ✓ Easy debugging, ⚠ Dependency management
   * - Cloud Deployment
     - Scalable production
     - ✓ Auto-scaling, ✓ High availability, ⚠ Cloud complexity

Prerequisites
-------------

**System Requirements**
- Operating System: Windows 10+, macOS 10.14+, or Linux
- Memory: 2GB minimum, 4GB recommended
- Disk Space: 1GB for installation, additional space for results
- Network: Internet access for downloading dependencies

**Software Prerequisites**
- Python 3.8+ (for conda installation)
- Docker 20.10+ (for container installation)
- Git (for source code access)

Next Steps
----------

Choose your installation method:
- :doc:`docker_installation` for production deployment
- :doc:`conda_setup` for development work
- :doc:`../deployment/production_deployment` for scalable deployment