from datetime import timedelta

import pendulum
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG

PROJECT_DIR = "/opt/airflow/project"
DBT_DIR = f"{PROJECT_DIR}/sunglasshut_dbt"
SCRAPER = "/opt/venvs/scraper/bin/python -m scraper"
DBT_FLAGS = "--profiles-dir . --target-path /tmp/dbt/target --log-path /tmp/dbt/logs"

with DAG(
    dag_id="sunglasshut_daily",
    schedule="0 9 * * *",
    start_date=pendulum.datetime(2026, 9, 1, tz="Asia/Bangkok"),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
    tags=["sunglasshut"],
) as dag:
    extract = BashOperator(
        task_id="extract",
        bash_command=f"{SCRAPER} extract",
        cwd=PROJECT_DIR,
    )

    load = BashOperator(
        task_id="load",
        bash_command=SCRAPER + " load --run {{ ti.xcom_pull(task_ids='extract') }}",
        cwd=PROJECT_DIR,
        do_xcom_push=False,
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"/opt/venvs/dbt/bin/dbt run {DBT_FLAGS}",
        cwd=DBT_DIR,
        do_xcom_push=False,
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"/opt/venvs/dbt/bin/dbt test {DBT_FLAGS}",
        cwd=DBT_DIR,
        do_xcom_push=False,
    )

    extract >> load >> dbt_run >> dbt_test
