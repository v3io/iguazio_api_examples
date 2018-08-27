To deploy the functions, use the `nuctl` Nuclio CLI, which you  can download from https://github.com/nuclio/nuclio/releases.

For local installs, add `--platform local` to all of the following commands.

1.  Create a project:

    ```sh
    nuctl create project --display-name taxi_example --namespace Nuclio taxi_example
    ```

2.  Update **/xxx/nuclio_python/generate_data/function.yaml** `INGEST_URL` to point to the ingestion-function URL:

3.  Update **/xxx/nuclio_python/ingest/function.yaml** `WEBAPI_URL` to point to the Iguazio Continuous Data Platform web-gateway service (nginx) URL:

4.  **Update /xxx/nuclio_python/ingest/function.yaml** `DRIVERS_TABLE` and `CELLS_TABLE` to point to the desired location of the tables:

5.  Deploy functions:

    ```sh
    nuctl deploy --path /xxx/nuclio_python/ingest.py -f /xxx/taxi_nuclio/ingest.yaml
    nuctl deploy --path /xxx/nuclio_python/generate_data.py -f /xxx/taxi_nuclio/generate_data.yaml
    ```

