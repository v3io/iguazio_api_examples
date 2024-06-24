import os
import json
import pickle
import http.client
import sklearn
import numpy as np

import libs.utils.utils
import libs.nuclio_sdk


def predict(context, event):
    if event.path == '/configure':
        if type(event.body) is not dict:
            return context.Response(status_code=400)

        _configure(context, event.body)
    elif event.path == '/start':
        _start(context)
    elif event.path == '/stop':
        _stop(context)
    elif event.path in ['/predict', '/', '']:
        if context.user_data.state == 'predicting':
            return _predict_error(context, **(event.body or {}))
    else:
        context.logger.warn_with('Got unsupported path', method=event.method, path=event.path)
        return context.Response(status_code=400)


def init_context(context):
    # Init states
    libs.utils.utils.init_context(context)

    # check to see if there's an environment variable with our initial configuration
    if 'PREDICTOR_CONFIGURATION' in os.environ:
        _configure(context, json.loads(os.environ['PREDICTOR_CONFIGURATION']))


def _configure(context, configuration: dict):
    # Load model from given path
    try:
        if 'MODEL_FILE' in os.environ:
            with open(os.environ.get('MODEL_FILE'), 'rb+') as f:
                context.user_data.model = pickle.load(f)
    except IOError:
        context.user_data.model = None


    # Configure TSDB server for queries
    context.user_data.tsdb = configuration.get("tsdb")

    # Configure Metrics
    context.user_data.metrics = configuration.get("metrics")

    # Save configuration
    context.user_data.configuration = configuration

    try:
        context.user_data.state = configuration['state']
    except KeyError:
        pass


def _start(context):
    context.logger.info_with('Starting to predict', prev_state=context.user_data.state)

    # Start predicting
    context.user_data.state = 'predicting'


def _stop(context):
    context.logger.info_with('Stopping to predict', prev_state=context.user_data.state)

    # go back to idle
    context.user_data.state = 'idle'


def _predict(context):
    # Connect to TSDB
    client = http.client.HTTPConnection(context.user_data.tsdb)

    # Get metrics list
    metrics = sorted(list(context.user_data.metrics))
    results = {}

    # Query per metric (Prometheus query method)
    for metric in metrics:
        # Build and send query
        query = f'/api/v1/query?query=avg_over_time({metric}[1h])'
        client.request('GET', query)
        response = json.loads(client.getresponse().read().decode())
        response = _extract_results_from_prometheus_response(response)

        # Prepare responses
        for label in response:
            current_device_metric = _get_label_hash_from_response(label, metric)
            device_results = results.setdefault(list(current_device_metric.keys())[0], {})

            if device_results:
                device_results = device_results.setdefault('metrics', {})
                device_results.update(list(current_device_metric.values())[0]['metrics'])
            else:
                device_results.update(list(current_device_metric.values())[0])

    # Create feature vector per label (device)
    feature_vectors = {}
    for device, metrics in results.items():
        feature_vectors[device] = _create_feature_vector_from_metrics(metrics)

    # Predict error per device
    predictions = {}
    for device, X in feature_vectors.items():
        predictions[device] = {
            'label': {
                **X['label']
            },
            'metric': {
                'prediction': _predict_error(context, X['features'])
            }
        }

    # get the target from the request to generate or the configuration
    target = context.user_data.configuration.get('target')

    # send the metrics towards the target
    response = libs.utils.utils.send_emitters_to_target(context, target, predictions)

    # if this is an event response, make sure it's OK
    if target == 'response':
        return response


def _predict_error(context, features: list):
    return context.user_data.model.predict(features)[0]


def _extract_results_from_prometheus_response(response: dict):
    status = response.setdefault("status", "False")
    if status != "success":
        return []
    return response["data"]["result"]


def _get_label_hash_from_response(response: dict, metric: str):
    keys_to_keep = ['company_id', 'device_id', 'latitute', 'longitude', 'site_id']
    label_id = response['metric']['device_id']
    labels = {key: response['metric'][key] for key in keys_to_keep}
    values = {
        metric: response['value'][1]
    }

    return {
        label_id: {
            'label': labels,
            'metrics': values
        }
    }


def _create_feature_vector_from_metrics(metrics: dict):
    metrics['features'] = list(map(lambda metric: metric[1], sorted(metrics['metrics'].items())))
    return metrics
