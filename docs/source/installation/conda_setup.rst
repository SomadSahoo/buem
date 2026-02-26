Conda Setup
===========

Installing and configuring BuEM using Conda package manager.

Prerequisites
-------------

* `Anaconda <https://docs.anaconda.com/anaconda/install/>`_ or `Miniconda <https://docs.conda.io/en/latest/miniconda.html>`_
* Python 3.8+ support (recommended: Python 3.11)

Quick Installation
------------------

Create the BuEM environment directly from the repository:

.. code-block:: bash

    # Clone the repository
    git clone https://github.com/your-org/buem.git
    cd buem
    
    # Create conda environment
    conda env create -f environment.yml
    
    # Activate environment
    conda activate buem_env
    
    # Ready to use! Run with:
    python -m src.buem.main

Building from Source (Advanced)
-------------------------------

To build and install with conda:

.. code-block:: bash

    conda install conda-build
    conda build .
    conda install --use-local buem

.. note::
   **Development Usage:** When using the conda environment with the source code, 
   always prefix commands with ``src.`` (e.g., ``python -m src.buem.main``) to 
   avoid import conflicts.

Manual Environment Setup
------------------------

For custom environment configuration:

.. code-block:: bash

    # Create new environment
    conda create -n buem_env python=3.11
    conda activate buem_env
    
    # Install core dependencies
    conda install -c conda-forge numpy pandas scipy matplotlib
    conda install -c conda-forge requests flask gunicorn
    
    # For PyPI installation (alternative)
    pip install buem

Optional Dependencies
---------------------

For development and documentation:

.. code-block:: bash

    # Documentation tools
    conda install -c conda-forge sphinx sphinx_rtd_theme
    
    # Development tools
    conda install -c conda-forge pytest pytest-cov black flake8
    
    # Jupyter for interactive analysis
    conda install -c conda-forge jupyter notebook

Verifying Installation
----------------------

.. code-block:: bash

    # Test import
    python -c "import buem; print(buem.__version__)"
    
    # Check API server
    python -m buem.apis.api_server
    
    # Run tests
    pytest tests/

Troubleshooting
---------------

**Environment conflicts:**

.. code-block:: bash

    # Remove and recreate environment
    conda env remove -n buem_env
    conda env create -f environment.yml

**Module not found errors:**

.. code-block:: bash

    # Ensure proper installation
    pip install -e . --force-reinstall

For additional help, see :doc:`troubleshooting`.