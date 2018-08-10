import os
import time
import json

import libs.generator.manager
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
    elif event.path in ['/generate', '/', '']:
        print(context.user_data.state)
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
    try:
        _configure(context, json.loads(os.environ['GENERATOR_CONFIGURATION']))
    except KeyError:
        pass


def _configure(context, configuration):
    context.logger.info_with('Configuring', configuration=configuration)

    # create a Manager with the given configuration
    manager = libs.generator.manager.Manager(metrics=configuration['metrics'],
                                             error_scenarios=configuration['error_scenarios'],
                                             error_rate=configuration['error_rate'])

    # shove the configuration/manager in the context
    context.user_data.configuration = configuration
    context.user_data.manager = manager

    try:
        context.user_data.state = configuration['state']
    except KeyError:
        pass


def _start(context, start_configuration):
    context.logger.info_with('Starting to generate',
                             start_configuration=start_configuration,
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


def _generate(context, start_timestamp=None, end_timestamp=None, interval=None, max_samples_per_batch=None, target=None):

    # get the target from the request to generate or the configuration
    target = target or context.user_data.configuration.get('target')

    # set some defaults
    max_samples_per_batch = max_samples_per_batch or context.user_data.configuration.get('max_samples_per_batch') or ((2 ** 64) - 1)
    interval = interval or context.user_data.configuration.get('interval') or 1
    start_timestamp = start_timestamp or int(time.time())
    end_timestamp = end_timestamp or (start_timestamp + interval)

    # calculate how many samples we need to submit
    num_samples_left = int((end_timestamp - start_timestamp) / interval)

    responses = []

    while num_samples_left > 0:
        num_samples = min(num_samples_left, max_samples_per_batch)

        # generate the batch
        metrics_batch = _generate_batch(context, start_timestamp, num_samples, interval)

        # send to target
        response = _send_metrics_batch_to_target(context, target, metrics_batch)

        # if this is an event response, make sure it's OK
        if type(response) is context.Response and response.status_code != 200:
            return response
        elif response is not None:
            responses.append(response)

        num_samples_left -= num_samples
        start_timestamp += (num_samples * interval)

    if responses:
        return responses


def _generate_batch(context, start_timestamp, num_samples, interval):
    metrics_batch = {}

    # generate metrics
    for sample_idx in range(num_samples):
        timestamp = int(start_timestamp + (interval * sample_idx))

        for generated_metric_name, generated_metric in next(context.user_data.manager.generate()).items():

            # get metric, or create one with the proper labels
            metric_in_batch = metrics_batch.setdefault(generated_metric_name, {
                'labels': context.user_data.configuration['metrics'][generated_metric_name].get('labels'),
            })
            
            # shove values
            metric_in_batch.setdefault('timestamps', []).append(timestamp)
            metric_in_batch.setdefault('values', []).append(generated_metric['value'])
            metric_in_batch.setdefault('alerts', []).append(generated_metric['alert'])
            metric_in_batch.setdefault('is_error', []).append(1 if generated_metric['is_error'] else 0)

    return metrics_batch


def _send_metrics_batch_to_target(context, target, metrics_batch):
    context.logger.debug_with('Sending metrics to target', target=target)

    if target.startswith('function'):

        # function:netops-ingest -> netops-ingest
        target_function = target.split(':')[1]

        return context.platform.call_function(target_function, libs.nuclio_sdk.Event(body=metrics_batch))
    elif target == 'response':
        return metrics_batch
    elif target == 'log':
        context.logger.info_with('Sending metrics batch', metrics_batch=metrics_batch)
    else:
        raise ValueError(f'Unknown target type {target}')
