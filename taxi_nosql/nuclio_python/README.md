To deploy the functions use nuctl (download from https://github.com/nuclio/nuclio/releases)

For local installs, add "--platform local" to all commands below

1. Create a project

nuctl create project --display-name taxi_example --namespace nuclio taxi_example

2. Update /xxx/taxi_nuclio/generate_data/function.yaml INGEST_URL to point the ingestion function URL

3. Update /xxx/taxi_nuclio/ingest/function.yaml WEBAPI_URL to point the iguazio webapi nginx URL

4. Update /xxx/taxi_nuclio/ingest/function.yaml DRIVERS_TABLE and CELLS_TABLE to point to the desired location of the tables

5. Deploy functions

nuctl deploy --path /xxx/taxi_nuclio/ingest 

nuctl deploy --path /xxx/taxi_nuclio/generate_data



