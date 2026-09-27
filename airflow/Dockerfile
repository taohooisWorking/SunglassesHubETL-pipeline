FROM apache/airflow:3.3.2-python3.12

USER root
RUN mkdir -p /opt/venvs && chown airflow:root /opt/venvs
USER airflow

COPY requirements.txt requirements-dbt.txt /tmp/

RUN /usr/local/bin/python3 -m venv /opt/venvs/scraper \
    && /opt/venvs/scraper/bin/pip install --no-cache-dir -r /tmp/requirements.txt

RUN /usr/local/bin/python3 -m venv /opt/venvs/dbt \
    && /opt/venvs/dbt/bin/pip install --no-cache-dir -r /tmp/requirements-dbt.txt
