import os
import time
import json
import re
import pickle
import http.client
import sklearn
import numpy as np

import libs.generator.deployment
import libs.nuclio_sdk


def generate(context, event):
    if event.path == '/configure':
        if type(event.body) is not dict:
            return context.Response(status_code=400)

        _configure(context, event.body)
    elif event.path == '/start':
        _start(context, event.body)
    elif event.path == '/stop':
        _stop(context)
    elif event.path == '/sites':
        return _sites(context)
    elif event.path == '/devices':
        return _devices(context)
    elif event.path == '/predict':
        return _predict(context)
    elif event.path in ['/generate', '/', '']:
        if context.user_data.state == 'generating':
            return _generate(context, **(event.body or {}))
    else:
        context.logger.warn_with('Got unsupported path', method=event.method, path=event.path)
        return context.Response(status_code=400)


def init_context(context):

    # initialize context structure
    for context_attr in ['state', 'configuration', 'manager']:
        setattr(context.user_data, context_attr, None)

    # start in idle state
    context.user_data.state = 'idle'

    # check to see if there's an environment variable with our initial configuration
    if 'GENERATOR_CONFIGURATION' in os.environ:
        _configure(context, json.loads(os.environ['GENERATOR_CONFIGURATION']))


def _configure(context, configuration: dict):
    context.logger.info_with('Configuring', configuration=configuration)

    # create a Full Network Deployment given configuration
    deployment = libs.generator.deployment.Deployment(configuration=configuration)

    # shove the configuration/manager in the context
    context.user_data.configuration = configuration
    context.user_data.deployment = deployment

    # TODO: Verify Load model to user context.user_data.model
    model_filepath = 'model/model'
    if 'MODEL_FILE' in os.environ:
        model_filepath = os.environ['MODEL_FILE']
    with open(model_filepath, 'rb+') as f:
        context.user_data.model = pickle.load(f)

    target_server = '10.90.1.131:9090'
    if 'tsdb_address' in os.environ:
        context.user_data.tsdb = os.environ['tsdb_address']
    else:
        context.user_data.tsdb = target_server

    try:
        context.user_data.state = configuration['state']
    except KeyError:
        pass


def _start(context, start_configuration):
    context.logger.info_with('Starting to generate',
                             prev_state=context.user_data.state)

    # if there's configuration, check if we need to generate historical data
    if type(start_configuration) is dict:
        now = int(time.time())

        # get the point in time in which to generate historical data
        start_timestamp = now - start_configuration['num_historical_seconds']
        interval = start_configuration.get('interval')

        # generate a few seconds into the future
        end_timestamp = now + 10

        # generate using the defaults from the configuration
        _generate(context, start_timestamp, end_timestamp, interval)

    # set state to generating so that periodically we'll generate
    context.user_data.state = 'generating'


def _stop(context):
    context.logger.info_with('Stopping to generate', prev_state=context.user_data.state)

    # go back to idle
    context.user_data.state = 'idle'


def _sites(context):
    deployment = context.user_data.deployment
    context.logger.info_with('Sending list of sites', deployment=deployment)

    sites = []
    for company in deployment.companies:
        company_name_label = _company_name_to_label(company.name)

        for i, site_locations in enumerate(company.locations.values()):
            sites.append({
                'key': f'{company_name_label}/{i}',
                'latitude': site_locations[0],
                'longtitude': site_locations[1],
                'name': f'{company.name}/{i}'
            })

    return sites


def _devices(context):
    deployment = context.user_data.deployment
    context.logger.info_with('Sending list of devices', deployment=deployment)

    devices = []
    for company in deployment.companies:
        for i, site_locations in company.components.items():
            for j, x in enumerate(site_locations['devices']):
                devices.append(f'{company.name}/{i}/{j}')

    return devices

def _predict(context):
    # Query Prometheus
    client = http.client.HTTPConnection(context.user_data.tsdb)
    metrics = sorted(list(context.user_data.deployment.configuration['metrics'].keys()))
    results = {}
    for metric in metrics:
        query = f'/api/v1/query?query=avg_over_time({metric}[1h])'
        client.request('GET', query)
        response = json.loads(client.getresponse().read().decode())
        # response = _get_prometheus_throughput_avg_1h()        # For testing purposes
        response = _extract_results_from_prometheus_response(response)
        for label in response:
            current_device_metric = _get_label_hash_from_response(label, metric)
            device_results = results.setdefault(list(current_device_metric.keys())[0], {})

            if device_results:
                device_results = device_results.setdefault('metrics', {})
                device_results.update(list(current_device_metric.values())[0]['metrics'])
            else:
                device_results.update(list(current_device_metric.values())[0])

    feature_vectors = {}
    for device, metrics in results.items():
        feature_vectors[device] = _create_feature_vector_from_metrics(metrics)

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
    response = _send_emitters_to_target(context, target, predictions)

    # if this is an event response, make sure it's OK
    if target == 'response':
        return response

def _predict_error(context, features: list):
    mode = 'test'
    if mode == 'test':
        return True
    return context.user_data.model.predict(features)[0]

def _extract_results_from_prometheus_response(response: dict):
    status = response.setdefault("status", "False")
    if status != "success":
        return []
    return response["data"]["result"]

def _get_label_hash_from_response(response: dict, metric: str):
    keys_to_keep = ['company_id', 'device_id', 'latitute', 'longitude', 'site_id']
    label_id = response['metric']['device_id']
    labels = { key: response['metric'][key] for key in keys_to_keep }
    values = {
        metric: response['value'][1]
    }

    return {
        label_id:{
            'label': labels,
            'metrics': values
        }
    }

def _create_feature_vector_from_metrics(metrics: dict):
    metrics['features'] = list(map(lambda metric: metric[1], sorted(metrics['metrics'].items())))
    return metrics

def _generate(context,
              start_timestamp=None,
              end_timestamp=None,
              interval=None,
              max_samples_per_metric=None,
              target=None):
    # get the target from the request to generate or the configuration
    target = target or context.user_data.configuration.get('target')

    # set some defaults
    max_samples_per_metric = max_samples_per_metric or context.user_data.configuration.get('max_samples_per_metric') or (
            (2 ** 64) - 1)
    interval = interval or context.user_data.configuration.get('interval') or 1
    start_timestamp = start_timestamp or int(time.time())
    end_timestamp = end_timestamp or (start_timestamp + interval)

    # calculate how many samples we need to submit
    num_samples_left = int((end_timestamp - start_timestamp) / interval)

    responses = []

    context.logger.info_with("Generating",
                             samples_left=num_samples_left)

    while num_samples_left > 0:
        num_samples = min(num_samples_left, max_samples_per_metric)

        # generate all metrics for all devices
        emitters = _generate_emitters(context, start_timestamp, num_samples, interval)

        # send the metrics towards the target
        response = _send_emitters_to_target(context, target, emitters)

        # if this is an event response, make sure it's OK
        if type(response) is context.Response and response.status_code != 200:
            return response
        elif response is not None:
            responses.append(response)

        num_samples_left -= num_samples
        start_timestamp += (num_samples * interval)

    if responses:
        return responses


def _create_metric_dict(context, dict_device: dict,
                        device: dict,
                        labels: dict,
                        metric: dict,
                        metric_name: str,
                        timestamp):
    dict_metric = dict_device.setdefault(metric_name, {
        'labels': {**labels['labels'],
                   **device,
                   **context.user_data.configuration['metrics'][metric_name].get(
                       'labels')},
    })

    # shove values
    dict_metric.setdefault('timestamps', []).append(timestamp)
    dict_metric.setdefault('values', []).append(
        metric['value'])
    dict_metric.setdefault('alerts', []).append(
        metric['alert'])
    dict_metric.setdefault('is_error', []).append(
        1 if metric['is_error'] else 0)

    return dict_metric


def _metrics_batch_dict_to_array(metrics_batch: dict):
    result = []
    for company, locations in metrics_batch.items():
        for location, devices in locations.items():
            for device, metrics in devices.items():
                result.append(metrics)

    return result


def _generate_emitters(context, start_timestamp, num_samples, interval):
    emitters = {}

    # generate metrics
    for sample_idx in range(num_samples):
        timestamp = int(start_timestamp + (interval * sample_idx))

        generated_metrics = next(context.user_data.deployment.generate())

        # iterate over companies
        for company_name, sites in generated_metrics.items():

            # label friendly representation ('Duffy, Miller and Kelley' -> 'duffy_miller_and_kelley')
            company_name = _company_name_to_label(company_name)

            # iterate over the company's sites
            for site_name, site_info in sites.items():

                # iterate over site devices
                for device_name, device_info in site_info['devices'].items():

                    # create an emitter id
                    emitter_id = f'{company_name}/{site_name}/{device_name}'

                    # if this is the first metric for the emitter, initialize an empty emitter
                    try:
                        emitter = emitters[emitter_id]
                    except KeyError:
                        emitter = _create_emitter(context, company_name, site_name, site_info, emitter_id)
                        emitters[emitter_id] = emitter

                        # iterate over metrics and add the samples
                    for metric_name, metric_info in device_info.items():
                        emitter['metrics'][metric_name]['timestamps'].append(timestamp)
                        emitter['metrics'][metric_name]['values'].append(metric_info['value'])
                        emitter['metrics'][metric_name]['alerts'].append(metric_info['alert'])
                        emitter['metrics'][metric_name]['is_error'].append(1 if metric_info['is_error'] else 0)

    return emitters


def _create_emitter(context, company_name, site_name, site_info, emitter_id):

    emitter = {
        'labels': {
            'longitude': site_info['location'][0],
            'latitute': site_info['location'][1],
            'company_id': company_name,
            'site_id': f'{company_name}/{site_name}',
            'device_id': emitter_id
        },
        'metrics': {}
    }

    # iterate over all metrics in the configuration and initialize metrics
    for metric_name, metric_info in context.user_data.configuration['metrics'].items():
        emitter['metrics'][metric_name] = {
            'labels': metric_info['labels'],
            'timestamps': [],
            'values': [],
            'alerts': [],
            'is_error': [],
        }

    return emitter


def _send_emitters_to_target(context, target, metrics_batch):
    context.logger.debug_with('Sending metrics to target', target=target)

    if target.startswith('function'):

        # function:netops-ingest -> netops-ingest
        target_function = target.split(':')[1]

        context.platform.call_function(target_function, libs.nuclio_sdk.Event(body=metrics_batch))
    elif target == 'response':
        return metrics_batch
    elif target == 'log':
        context.logger.info_with('Sending metrics batch', metrics_batch=metrics_batch)
    else:
        raise ValueError(f'Unknown target type {target}')


def _company_name_to_label(company_name):
    return re.sub(r'[^a-zA-Z -]', '', company_name).lower().replace(' ', '_').replace('-', '_')

def _get_prometheus_throughput_avg_1h():
    return {
        "status": "success",
        "data": {
            "resultType": "vector",
            "result": [
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/3/1",
                        "latitute": "-0.11766485686257479",
                        "longitude": "51.51241260576661",
                        "site_id": "cook_ramirez_and_howell/3",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "201.84682698565652"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/3/4",
                        "latitute": "-0.11766485686257479",
                        "longitude": "51.51241260576661",
                        "site_id": "cook_ramirez_and_howell/3",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "202.02232908643256"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/1/9",
                        "latitute": "-0.17937324059872775",
                        "longitude": "51.49981289880396",
                        "site_id": "cook_ramirez_and_howell/1",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "195.52091063340944"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/1/8",
                        "latitute": "-0.08845125744353492",
                        "longitude": "51.49395842747566",
                        "site_id": "jackson_gibson/1",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "196.80557368577473"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/3/8",
                        "latitute": "-0.14477605500681137",
                        "longitude": "51.50950646273536",
                        "site_id": "jackson_gibson/3",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "197.14578076146293"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/3/9",
                        "latitute": "-0.1684063123676963",
                        "longitude": "51.49890595002585",
                        "site_id": "martinez_inc/3",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "198.25121288933332"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/0/4",
                        "latitute": "-0.08743943934424686",
                        "longitude": "51.49462424727675",
                        "site_id": "cook_ramirez_and_howell/0",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "200.3116370269399"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/4/6",
                        "latitute": "-0.11922450970538258",
                        "longitude": "51.495592295069905",
                        "site_id": "cook_ramirez_and_howell/4",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "201.69564330124905"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/4/9",
                        "latitute": "-0.10358309561844188",
                        "longitude": "51.502997658785624",
                        "site_id": "martinez_inc/4",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "195.72478779138552"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/1/4",
                        "latitute": "-0.17937324059872775",
                        "longitude": "51.49981289880396",
                        "site_id": "cook_ramirez_and_howell/1",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "197.80413082951264"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/4/7",
                        "latitute": "-0.10358309561844188",
                        "longitude": "51.502997658785624",
                        "site_id": "martinez_inc/4",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "199.3129222253966"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/1/1",
                        "latitute": "-0.18856414865471136",
                        "longitude": "51.50398145727124",
                        "site_id": "martinez_inc/1",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "199.29127778426687"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/2/0",
                        "latitute": "-0.12588664262819296",
                        "longitude": "51.50221488435059",
                        "site_id": "cook_ramirez_and_howell/2",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "201.24457498024685"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/1/8",
                        "latitute": "-0.18856414865471136",
                        "longitude": "51.50398145727124",
                        "site_id": "martinez_inc/1",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "200.3373581533792"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/4/7",
                        "latitute": "-0.10790649546111267",
                        "longitude": "51.505154712405286",
                        "site_id": "jackson_gibson/4",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "199.9646135829882"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/3/7",
                        "latitute": "-0.1684063123676963",
                        "longitude": "51.49890595002585",
                        "site_id": "martinez_inc/3",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "202.4863893062895"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/4/2",
                        "latitute": "-0.11922450970538258",
                        "longitude": "51.495592295069905",
                        "site_id": "cook_ramirez_and_howell/4",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "200.05184702490186"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/2/0",
                        "latitute": "-0.11642291673866854",
                        "longitude": "51.51683458013747",
                        "site_id": "martinez_inc/2",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "195.79330791453125"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/3/0",
                        "latitute": "-0.1684063123676963",
                        "longitude": "51.49890595002585",
                        "site_id": "martinez_inc/3",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "199.96811468182636"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/2/3",
                        "latitute": "-0.11642291673866854",
                        "longitude": "51.51683458013747",
                        "site_id": "martinez_inc/2",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "202.77078565378753"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/0/4",
                        "latitute": "-0.14414594436220526",
                        "longitude": "51.51080694746054",
                        "site_id": "martinez_inc/0",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "204.43106231216132"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/2/4",
                        "latitute": "-0.12588664262819296",
                        "longitude": "51.50221488435059",
                        "site_id": "cook_ramirez_and_howell/2",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "198.3928395695168"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/1/6",
                        "latitute": "-0.08845125744353492",
                        "longitude": "51.49395842747566",
                        "site_id": "jackson_gibson/1",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "201.1124768354935"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/3/7",
                        "latitute": "-0.11766485686257479",
                        "longitude": "51.51241260576661",
                        "site_id": "cook_ramirez_and_howell/3",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "203.6165793877006"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/2/2",
                        "latitute": "-0.11642291673866854",
                        "longitude": "51.51683458013747",
                        "site_id": "martinez_inc/2",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "198.57428448308957"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/0/0",
                        "latitute": "-0.14414594436220526",
                        "longitude": "51.51080694746054",
                        "site_id": "martinez_inc/0",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "198.695688192008"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/1/1",
                        "latitute": "-0.08845125744353492",
                        "longitude": "51.49395842747566",
                        "site_id": "jackson_gibson/1",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "200.3342129942806"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/2/9",
                        "latitute": "-0.11642291673866854",
                        "longitude": "51.51683458013747",
                        "site_id": "martinez_inc/2",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "199.56559180485672"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/4/5",
                        "latitute": "-0.11922450970538258",
                        "longitude": "51.495592295069905",
                        "site_id": "cook_ramirez_and_howell/4",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "201.16954763272514"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/4/6",
                        "latitute": "-0.10790649546111267",
                        "longitude": "51.505154712405286",
                        "site_id": "jackson_gibson/4",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "196.71524325915243"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/2/6",
                        "latitute": "-0.12588664262819296",
                        "longitude": "51.50221488435059",
                        "site_id": "cook_ramirez_and_howell/2",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "199.28072743830444"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/3/9",
                        "latitute": "-0.11766485686257479",
                        "longitude": "51.51241260576661",
                        "site_id": "cook_ramirez_and_howell/3",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "200.49862413673156"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/4/1",
                        "latitute": "-0.10358309561844188",
                        "longitude": "51.502997658785624",
                        "site_id": "martinez_inc/4",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "200.80540298841441"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/3/9",
                        "latitute": "-0.14477605500681137",
                        "longitude": "51.50950646273536",
                        "site_id": "jackson_gibson/3",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "197.9708384853567"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/1/7",
                        "latitute": "-0.17937324059872775",
                        "longitude": "51.49981289880396",
                        "site_id": "cook_ramirez_and_howell/1",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "198.3352771171675"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/4/5",
                        "latitute": "-0.10358309561844188",
                        "longitude": "51.502997658785624",
                        "site_id": "martinez_inc/4",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "198.7710944467823"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/0/9",
                        "latitute": "-0.14414594436220526",
                        "longitude": "51.51080694746054",
                        "site_id": "martinez_inc/0",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "200.13094249930876"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/0/0",
                        "latitute": "-0.09275684203595459",
                        "longitude": "51.50604392091363",
                        "site_id": "jackson_gibson/0",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "203.74401774477604"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/3/1",
                        "latitute": "-0.1684063123676963",
                        "longitude": "51.49890595002585",
                        "site_id": "martinez_inc/3",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "195.06474004803403"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/4/1",
                        "latitute": "-0.11922450970538258",
                        "longitude": "51.495592295069905",
                        "site_id": "cook_ramirez_and_howell/4",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "197.24436504924168"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/0/7",
                        "latitute": "-0.14414594436220526",
                        "longitude": "51.51080694746054",
                        "site_id": "martinez_inc/0",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "201.08608593580766"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/2/3",
                        "latitute": "-0.12588664262819296",
                        "longitude": "51.50221488435059",
                        "site_id": "cook_ramirez_and_howell/2",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "198.7599557286866"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/3/6",
                        "latitute": "-0.1684063123676963",
                        "longitude": "51.49890595002585",
                        "site_id": "martinez_inc/3",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "204.308557481124"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/4/4",
                        "latitute": "-0.11922450970538258",
                        "longitude": "51.495592295069905",
                        "site_id": "cook_ramirez_and_howell/4",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "193.0099878859856"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/0/1",
                        "latitute": "-0.14414594436220526",
                        "longitude": "51.51080694746054",
                        "site_id": "martinez_inc/0",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "201.42345580633963"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/1/8",
                        "latitute": "-0.17937324059872775",
                        "longitude": "51.49981289880396",
                        "site_id": "cook_ramirez_and_howell/1",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "201.77209237275176"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/3/5",
                        "latitute": "-0.14477605500681137",
                        "longitude": "51.50950646273536",
                        "site_id": "jackson_gibson/3",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "196.69713104761172"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/0/7",
                        "latitute": "-0.09275684203595459",
                        "longitude": "51.50604392091363",
                        "site_id": "jackson_gibson/0",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "198.31397445378576"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/1/4",
                        "latitute": "-0.08845125744353492",
                        "longitude": "51.49395842747566",
                        "site_id": "jackson_gibson/1",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "201.82758047257465"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/1/0",
                        "latitute": "-0.08845125744353492",
                        "longitude": "51.49395842747566",
                        "site_id": "jackson_gibson/1",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "199.3491855729556"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/1/0",
                        "latitute": "-0.17937324059872775",
                        "longitude": "51.49981289880396",
                        "site_id": "cook_ramirez_and_howell/1",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "196.17085785311446"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/4/3",
                        "latitute": "-0.11922450970538258",
                        "longitude": "51.495592295069905",
                        "site_id": "cook_ramirez_and_howell/4",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "204.88745646047883"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/0/2",
                        "latitute": "-0.09275684203595459",
                        "longitude": "51.50604392091363",
                        "site_id": "jackson_gibson/0",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "196.3480228927308"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/0/2",
                        "latitute": "-0.14414594436220526",
                        "longitude": "51.51080694746054",
                        "site_id": "martinez_inc/0",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "202.8579103696573"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/0/5",
                        "latitute": "-0.14414594436220526",
                        "longitude": "51.51080694746054",
                        "site_id": "martinez_inc/0",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "197.37466218794935"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/4/2",
                        "latitute": "-0.10358309561844188",
                        "longitude": "51.502997658785624",
                        "site_id": "martinez_inc/4",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "202.51812945931016"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/4/9",
                        "latitute": "-0.10790649546111267",
                        "longitude": "51.505154712405286",
                        "site_id": "jackson_gibson/4",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "197.95775656198037"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/4/3",
                        "latitute": "-0.10358309561844188",
                        "longitude": "51.502997658785624",
                        "site_id": "martinez_inc/4",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "199.29505953777763"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/2/1",
                        "latitute": "-0.12588664262819296",
                        "longitude": "51.50221488435059",
                        "site_id": "cook_ramirez_and_howell/2",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "199.72902867003324"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/1/9",
                        "latitute": "-0.18856414865471136",
                        "longitude": "51.50398145727124",
                        "site_id": "martinez_inc/1",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "196.33084254742477"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/2/3",
                        "latitute": "-0.15706157829077952",
                        "longitude": "51.519939570267255",
                        "site_id": "jackson_gibson/2",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "198.44927576056375"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/0/9",
                        "latitute": "-0.08743943934424686",
                        "longitude": "51.49462424727675",
                        "site_id": "cook_ramirez_and_howell/0",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "196.92239718637927"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/4/0",
                        "latitute": "-0.10358309561844188",
                        "longitude": "51.502997658785624",
                        "site_id": "martinez_inc/4",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "202.71815476920034"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/3/5",
                        "latitute": "-0.11766485686257479",
                        "longitude": "51.51241260576661",
                        "site_id": "cook_ramirez_and_howell/3",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "201.89862443814354"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/2/5",
                        "latitute": "-0.15706157829077952",
                        "longitude": "51.519939570267255",
                        "site_id": "jackson_gibson/2",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "198.61435786412522"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/3/2",
                        "latitute": "-0.14477605500681137",
                        "longitude": "51.50950646273536",
                        "site_id": "jackson_gibson/3",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "200.13486464613476"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/1/9",
                        "latitute": "-0.08845125744353492",
                        "longitude": "51.49395842747566",
                        "site_id": "jackson_gibson/1",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "201.80828117073895"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/1/6",
                        "latitute": "-0.17937324059872775",
                        "longitude": "51.49981289880396",
                        "site_id": "cook_ramirez_and_howell/1",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "203.5009752841243"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/2/0",
                        "latitute": "-0.15706157829077952",
                        "longitude": "51.519939570267255",
                        "site_id": "jackson_gibson/2",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "201.03865831051542"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/3/8",
                        "latitute": "-0.11766485686257479",
                        "longitude": "51.51241260576661",
                        "site_id": "cook_ramirez_and_howell/3",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "202.40276494043889"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/4/0",
                        "latitute": "-0.10790649546111267",
                        "longitude": "51.505154712405286",
                        "site_id": "jackson_gibson/4",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "202.0984346718554"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/0/3",
                        "latitute": "-0.14414594436220526",
                        "longitude": "51.51080694746054",
                        "site_id": "martinez_inc/0",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "202.57778277641512"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/3/6",
                        "latitute": "-0.14477605500681137",
                        "longitude": "51.50950646273536",
                        "site_id": "jackson_gibson/3",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "197.86322701166387"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/3/4",
                        "latitute": "-0.14477605500681137",
                        "longitude": "51.50950646273536",
                        "site_id": "jackson_gibson/3",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "198.87411958933114"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/1/4",
                        "latitute": "-0.18856414865471136",
                        "longitude": "51.50398145727124",
                        "site_id": "martinez_inc/1",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "205.39193276923314"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/4/8",
                        "latitute": "-0.11922450970538258",
                        "longitude": "51.495592295069905",
                        "site_id": "cook_ramirez_and_howell/4",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "199.6762694607545"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/2/7",
                        "latitute": "-0.15706157829077952",
                        "longitude": "51.519939570267255",
                        "site_id": "jackson_gibson/2",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "197.30960573882373"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/0/3",
                        "latitute": "-0.09275684203595459",
                        "longitude": "51.50604392091363",
                        "site_id": "jackson_gibson/0",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "201.771092958179"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/0/5",
                        "latitute": "-0.08743943934424686",
                        "longitude": "51.49462424727675",
                        "site_id": "cook_ramirez_and_howell/0",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "199.4923922717868"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/2/4",
                        "latitute": "-0.11642291673866854",
                        "longitude": "51.51683458013747",
                        "site_id": "martinez_inc/2",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "202.5549280217423"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/0/1",
                        "latitute": "-0.08743943934424686",
                        "longitude": "51.49462424727675",
                        "site_id": "cook_ramirez_and_howell/0",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "202.9675457506287"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/1/3",
                        "latitute": "-0.17937324059872775",
                        "longitude": "51.49981289880396",
                        "site_id": "cook_ramirez_and_howell/1",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "198.5703293318505"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/1/5",
                        "latitute": "-0.08845125744353492",
                        "longitude": "51.49395842747566",
                        "site_id": "jackson_gibson/1",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "202.6195506442932"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/0/1",
                        "latitute": "-0.09275684203595459",
                        "longitude": "51.50604392091363",
                        "site_id": "jackson_gibson/0",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "200.59050851861292"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/0/8",
                        "latitute": "-0.14414594436220526",
                        "longitude": "51.51080694746054",
                        "site_id": "martinez_inc/0",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "203.5622379069917"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/4/5",
                        "latitute": "-0.10790649546111267",
                        "longitude": "51.505154712405286",
                        "site_id": "jackson_gibson/4",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "203.81845968239867"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/1/2",
                        "latitute": "-0.17937324059872775",
                        "longitude": "51.49981289880396",
                        "site_id": "cook_ramirez_and_howell/1",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "198.08604078610432"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/3/5",
                        "latitute": "-0.1684063123676963",
                        "longitude": "51.49890595002585",
                        "site_id": "martinez_inc/3",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "198.93246514279485"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/1/5",
                        "latitute": "-0.18856414865471136",
                        "longitude": "51.50398145727124",
                        "site_id": "martinez_inc/1",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "203.5700383167893"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/4/2",
                        "latitute": "-0.10790649546111267",
                        "longitude": "51.505154712405286",
                        "site_id": "jackson_gibson/4",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "199.49954891178135"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/2/2",
                        "latitute": "-0.15706157829077952",
                        "longitude": "51.519939570267255",
                        "site_id": "jackson_gibson/2",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "199.3125792525744"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/1/7",
                        "latitute": "-0.08845125744353492",
                        "longitude": "51.49395842747566",
                        "site_id": "jackson_gibson/1",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "199.63250114277076"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/4/3",
                        "latitute": "-0.10790649546111267",
                        "longitude": "51.505154712405286",
                        "site_id": "jackson_gibson/4",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "198.72943358456283"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/0/6",
                        "latitute": "-0.08743943934424686",
                        "longitude": "51.49462424727675",
                        "site_id": "cook_ramirez_and_howell/0",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "200.4231318636992"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/3/1",
                        "latitute": "-0.14477605500681137",
                        "longitude": "51.50950646273536",
                        "site_id": "jackson_gibson/3",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "199.31267730947303"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/3/2",
                        "latitute": "-0.1684063123676963",
                        "longitude": "51.49890595002585",
                        "site_id": "martinez_inc/3",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "199.54326952138825"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/2/1",
                        "latitute": "-0.15706157829077952",
                        "longitude": "51.519939570267255",
                        "site_id": "jackson_gibson/2",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "203.4478702901137"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/4/9",
                        "latitute": "-0.11922450970538258",
                        "longitude": "51.495592295069905",
                        "site_id": "cook_ramirez_and_howell/4",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "193.502798339676"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/1/3",
                        "latitute": "-0.08845125744353492",
                        "longitude": "51.49395842747566",
                        "site_id": "jackson_gibson/1",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "202.32434207174623"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/4/8",
                        "latitute": "-0.10358309561844188",
                        "longitude": "51.502997658785624",
                        "site_id": "martinez_inc/4",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "198.5594718612572"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/3/0",
                        "latitute": "-0.14477605500681137",
                        "longitude": "51.50950646273536",
                        "site_id": "jackson_gibson/3",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "205.06356467643758"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/0/0",
                        "latitute": "-0.08743943934424686",
                        "longitude": "51.49462424727675",
                        "site_id": "cook_ramirez_and_howell/0",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "204.31049087691707"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/0/5",
                        "latitute": "-0.09275684203595459",
                        "longitude": "51.50604392091363",
                        "site_id": "jackson_gibson/0",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "197.64496317318378"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/3/4",
                        "latitute": "-0.1684063123676963",
                        "longitude": "51.49890595002585",
                        "site_id": "martinez_inc/3",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "196.09901479328602"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/4/1",
                        "latitute": "-0.10790649546111267",
                        "longitude": "51.505154712405286",
                        "site_id": "jackson_gibson/4",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "197.90912683161795"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/2/1",
                        "latitute": "-0.11642291673866854",
                        "longitude": "51.51683458013747",
                        "site_id": "martinez_inc/2",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "195.20660684721142"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/0/8",
                        "latitute": "-0.09275684203595459",
                        "longitude": "51.50604392091363",
                        "site_id": "jackson_gibson/0",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "198.81177258795051"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/0/8",
                        "latitute": "-0.08743943934424686",
                        "longitude": "51.49462424727675",
                        "site_id": "cook_ramirez_and_howell/0",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "199.26558341667908"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/1/0",
                        "latitute": "-0.18856414865471136",
                        "longitude": "51.50398145727124",
                        "site_id": "martinez_inc/1",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "202.63322094012966"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/0/2",
                        "latitute": "-0.08743943934424686",
                        "longitude": "51.49462424727675",
                        "site_id": "cook_ramirez_and_howell/0",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "201.242829647885"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/1/1",
                        "latitute": "-0.17937324059872775",
                        "longitude": "51.49981289880396",
                        "site_id": "cook_ramirez_and_howell/1",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "203.47636863611046"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/2/8",
                        "latitute": "-0.12588664262819296",
                        "longitude": "51.50221488435059",
                        "site_id": "cook_ramirez_and_howell/2",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "196.6303931712822"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/4/8",
                        "latitute": "-0.10790649546111267",
                        "longitude": "51.505154712405286",
                        "site_id": "jackson_gibson/4",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "199.4025509158343"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/2/5",
                        "latitute": "-0.11642291673866854",
                        "longitude": "51.51683458013747",
                        "site_id": "martinez_inc/2",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "202.244381888705"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/2/9",
                        "latitute": "-0.15706157829077952",
                        "longitude": "51.519939570267255",
                        "site_id": "jackson_gibson/2",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "198.75932886475152"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/0/3",
                        "latitute": "-0.08743943934424686",
                        "longitude": "51.49462424727675",
                        "site_id": "cook_ramirez_and_howell/0",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "197.55541164406517"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/3/8",
                        "latitute": "-0.1684063123676963",
                        "longitude": "51.49890595002585",
                        "site_id": "martinez_inc/3",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "199.67193673177024"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/2/6",
                        "latitute": "-0.11642291673866854",
                        "longitude": "51.51683458013747",
                        "site_id": "martinez_inc/2",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "201.87301396849193"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/0/4",
                        "latitute": "-0.09275684203595459",
                        "longitude": "51.50604392091363",
                        "site_id": "jackson_gibson/0",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "208.8742227341114"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/4/6",
                        "latitute": "-0.10358309561844188",
                        "longitude": "51.502997658785624",
                        "site_id": "martinez_inc/4",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "197.7648261012689"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/0/6",
                        "latitute": "-0.14414594436220526",
                        "longitude": "51.51080694746054",
                        "site_id": "martinez_inc/0",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "199.9982144628044"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/0/9",
                        "latitute": "-0.09275684203595459",
                        "longitude": "51.50604392091363",
                        "site_id": "jackson_gibson/0",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "201.46652012853383"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/2/5",
                        "latitute": "-0.12588664262819296",
                        "longitude": "51.50221488435059",
                        "site_id": "cook_ramirez_and_howell/2",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "200.39455519286264"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/1/7",
                        "latitute": "-0.18856414865471136",
                        "longitude": "51.50398145727124",
                        "site_id": "martinez_inc/1",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "200.60777016813307"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/2/4",
                        "latitute": "-0.15706157829077952",
                        "longitude": "51.519939570267255",
                        "site_id": "jackson_gibson/2",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "195.1289531633795"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/1/2",
                        "latitute": "-0.08845125744353492",
                        "longitude": "51.49395842747566",
                        "site_id": "jackson_gibson/1",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "203.46170393549912"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/2/7",
                        "latitute": "-0.11642291673866854",
                        "longitude": "51.51683458013747",
                        "site_id": "martinez_inc/2",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "205.7759776027545"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/4/4",
                        "latitute": "-0.10358309561844188",
                        "longitude": "51.502997658785624",
                        "site_id": "martinez_inc/4",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "202.10716727798894"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/3/3",
                        "latitute": "-0.14477605500681137",
                        "longitude": "51.50950646273536",
                        "site_id": "jackson_gibson/3",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "199.58662763687067"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/2/8",
                        "latitute": "-0.11642291673866854",
                        "longitude": "51.51683458013747",
                        "site_id": "martinez_inc/2",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "199.73692392059917"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/3/6",
                        "latitute": "-0.11766485686257479",
                        "longitude": "51.51241260576661",
                        "site_id": "cook_ramirez_and_howell/3",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "197.8058363586146"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/2/6",
                        "latitute": "-0.15706157829077952",
                        "longitude": "51.519939570267255",
                        "site_id": "jackson_gibson/2",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "201.4959357936072"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/4/4",
                        "latitute": "-0.10790649546111267",
                        "longitude": "51.505154712405286",
                        "site_id": "jackson_gibson/4",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "201.15200992534773"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/1/3",
                        "latitute": "-0.18856414865471136",
                        "longitude": "51.50398145727124",
                        "site_id": "martinez_inc/1",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "198.47767020368474"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/3/0",
                        "latitute": "-0.11766485686257479",
                        "longitude": "51.51241260576661",
                        "site_id": "cook_ramirez_and_howell/3",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "196.8473143781654"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/1/2",
                        "latitute": "-0.18856414865471136",
                        "longitude": "51.50398145727124",
                        "site_id": "martinez_inc/1",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "203.16443165242134"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/2/2",
                        "latitute": "-0.12588664262819296",
                        "longitude": "51.50221488435059",
                        "site_id": "cook_ramirez_and_howell/2",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "204.06110122890823"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/4/7",
                        "latitute": "-0.11922450970538258",
                        "longitude": "51.495592295069905",
                        "site_id": "cook_ramirez_and_howell/4",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "198.0927403914103"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/0/7",
                        "latitute": "-0.08743943934424686",
                        "longitude": "51.49462424727675",
                        "site_id": "cook_ramirez_and_howell/0",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "199.8686825637131"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/3/3",
                        "latitute": "-0.1684063123676963",
                        "longitude": "51.49890595002585",
                        "site_id": "martinez_inc/3",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "200.35823350690367"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/3/7",
                        "latitute": "-0.14477605500681137",
                        "longitude": "51.50950646273536",
                        "site_id": "jackson_gibson/3",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "200.6086038246571"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/4/0",
                        "latitute": "-0.11922450970538258",
                        "longitude": "51.495592295069905",
                        "site_id": "cook_ramirez_and_howell/4",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "202.84687489498225"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/3/2",
                        "latitute": "-0.11766485686257479",
                        "longitude": "51.51241260576661",
                        "site_id": "cook_ramirez_and_howell/3",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "196.86890595546433"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/3/3",
                        "latitute": "-0.11766485686257479",
                        "longitude": "51.51241260576661",
                        "site_id": "cook_ramirez_and_howell/3",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "199.39106984840805"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/1/5",
                        "latitute": "-0.17937324059872775",
                        "longitude": "51.49981289880396",
                        "site_id": "cook_ramirez_and_howell/1",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "197.42025139765155"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/2/9",
                        "latitute": "-0.12588664262819296",
                        "longitude": "51.50221488435059",
                        "site_id": "cook_ramirez_and_howell/2",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "202.4647531090913"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/2/8",
                        "latitute": "-0.15706157829077952",
                        "longitude": "51.519939570267255",
                        "site_id": "jackson_gibson/2",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "199.47985538380314"
                    ]
                },
                {
                    "metric": {
                        "company_id": "martinez_inc",
                        "device_id": "martinez_inc/1/6",
                        "latitute": "-0.18856414865471136",
                        "longitude": "51.50398145727124",
                        "site_id": "martinez_inc/1",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "203.75229813981974"
                    ]
                },
                {
                    "metric": {
                        "company_id": "cook_ramirez_and_howell",
                        "device_id": "cook_ramirez_and_howell/2/7",
                        "latitute": "-0.12588664262819296",
                        "longitude": "51.50221488435059",
                        "site_id": "cook_ramirez_and_howell/2",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "201.04338505108396"
                    ]
                },
                {
                    "metric": {
                        "company_id": "jackson_gibson",
                        "device_id": "jackson_gibson/0/6",
                        "latitute": "-0.09275684203595459",
                        "longitude": "51.50604392091363",
                        "site_id": "jackson_gibson/0",
                        "target_type": "gauge",
                        "unit": "mbyte_sec",
                        "ver": "1"
                    },
                    "value": [
                        1540456986.897,
                        "197.69736363634297"
                    ]
                }
            ]
        }
    }
