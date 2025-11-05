FROM python:3.11

WORKDIR /app

COPY res-immunology-automation /app/res-immunology-automation
COPY graphRAG /app/graphRAG
COPY redis /app/redis
COPY geneSearch /app/geneSearch
COPY requirements.txt .
COPY llmfactory-0.1.0-py3-none-any.whl .

#Download GWAS associations data
WORKDIR /app/res-immunology-automation/res_immunology_automation/src/gwas_data
# RUN wget -O associations.tsv https://www.ebi.ac.uk/gwas/api/search/downloads/alternative || \
#     (echo "Download failed, extracting existing tar file..." && tar -xvzf *.tar.gz)

# RUN wget -O associations.zip https://www.ebi.ac.uk/gwas/api/search/downloads/associations/v1.0.2?split=false || \
#     (echo "Download failed, extracting existing tar file..." && unzip associations.zip && mv gwas-catalog-download-associations-alt-full.tsv associations.tsv)

RUN set -e; \
    echo "Downloading GWAS associations..."; \
    if wget -O associations.zip "https://www.ebi.ac.uk/gwas/api/search/downloads/associations/v1.0.2?split=false"; then \
        echo "Download successful."; \
        unzip associations.zip && mv gwas-catalog-download-associations-alt-full.tsv associations.tsv; \
    else \
        echo "Download failed — using existing associations.zip if present..."; \
        unzip associations.zip && mv gwas-catalog-download-associations-alt-full.tsv associations.tsv; \
    fi

WORKDIR /app/res-immunology-automation/res_immunology_automation/src/phenotype_file
RUN wget -O MGI_PhenotypicAllele.rpt https://www.informatics.jax.org/downloads/reports/MGI_PhenotypicAllele.rpt

WORKDIR /app/geneSearch
RUN tar -xvzf duckdb.db.tar.gz

WORKDIR /app
# Update the package manager and install SQLite
RUN apt-get update && apt-get install -y sqlite3 supervisor

RUN pip install -r requirements.txt
RUN pip install llmfactory-0.1.0-py3-none-any.whl

# copy supervisord.conf to startup both fastapi server and build dossier on start of container
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Run Supervisor as the container's main process
WORKDIR /app/res-immunology-automation/res_immunology_automation/src/scripts

# CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "20"]
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
