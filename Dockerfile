FROM continuumio/miniconda3

WORKDIR /app

# install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# copy env and create conda env
COPY environment.yml /app/
RUN conda env create -f environment.yml && conda clean -afy

# ensure conda env bin is first on PATH so gunicorn/python are available directly
ENV PATH=/opt/conda/envs/buem_env/bin:$PATH
ENV PYTHONPATH=/app/src

# copy project
COPY . /app

EXPOSE 5000

# run gunicorn directly (uses gunicorn from conda env installed via environment.yml)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "buem.apis.api_server:create_app()", "--workers", "2", "--threads", "2"]