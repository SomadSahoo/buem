Documentation Structure
=======================

Welcome to the BuEM documentation source files.

Directory Contents
------------------

.. code-block::

   docs/
   ├── README.md              # Complete documentation overview
   ├── source/                # Sphinx source files
   │   ├── index.rst          # Main documentation entry point
   │   ├── conf.py            # Sphinx configuration
   │   ├── introduction/      # Project introduction
   │   ├── api_integration/   # API integration guide
   │   ├── model_attributes/  # Building attributes reference
   │   ├── technical/         # Technical documentation
   │   ├── installation/      # Installation instructions
   │   └── examples/          # Integration examples
   ├── build/                 # Generated documentation (after build)
   ├── requirements.txt       # Documentation dependencies
   ├── Makefile              # Build script (Linux/macOS)
   ├── make.bat              # Build script (Windows)
   └── build_docs.bat        # Conda-aware build helper

Quick Start
-----------

**View Documentation Overview:**
   Open `README.md <README.md>`_ for complete documentation guide.

**Build Documentation:**

   1. Activate conda environment: ``conda activate buem_env``
   2. Install dependencies: ``conda env update -f ../environment.yml``
   3. Build docs: ``./build_docs.bat`` (Windows) or ``make html``
   4. View: Open ``build/html/index.html``

**Main Entry Point:**
   After building, start at `build/html/index.html` or `source/index.rst`

For detailed information about content and structure, see the main `README.md <README.md>`_ file.