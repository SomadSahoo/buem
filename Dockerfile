FROM continuumio/miniconda3

# create a working directory and copy into it
WORKDIR /app
COPY . /app

# Set PYTHONPATH so you can run as a module
ENV PYTHONPATH=/app/src


# install dependencies
RUN conda env create -f environment.yml

# command to use the conda environment by default
# SHELL ["conda", "run", "-n", "buem_env", "/bin/bash", "-c"]

# Default command: run as module
CMD ["conda", "run", "-n", "buem_env", "python", "-m", "buem.main"]