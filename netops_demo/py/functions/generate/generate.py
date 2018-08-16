import os
import time
import json

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
    elif event.path in ['/generate', '/', '']:
        print(context.user_data.state)
        print(context.user_data.configuration)
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
        for i, site_locations in enumerate(company.locations):
            sites.append({
                'key': f'{company.name}/{i}',
                'latitude': site_locations[0],
                'longtitude': site_locations[1],
                'name': f'{company.name}/{i}'
            })

    return sites


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
