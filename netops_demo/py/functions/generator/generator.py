import time

import libs.generator.manager
import libs.nuclio_sdk


def handler(context, event):

    if event.path == '/start':
        _start_generating(context, event.body)
    elif event.path == '/stop':
        _stop_generating(context)
    elif event.path == '/generate':
        if _get_generating_state(context) == 'generating':
            return _generate(context, **(event.body or {}))
    else:
        context.logger.warn_with('Got unsupported path', method=event.method, path=event.path)
        return context.Response(status_code=400)


def init_context(context):
    
    # start in idle state
    _set_generating_state(context, 'idle')


def _start_generating(context, configuration):
    context.logger.info_with('Starting to generate', configuration=configuration)

    # create a Manager with the given configuration
    manager = libs.generator.manager.Manager(metrics=configuration['metrics'],
                                             error_scenarios=configuration['error_scenarios'],
                                             error_rate=configuration['error_rate'])

    # shove the configuration/manager in the context
    setattr(context.user_data, 'configuration', configuration)
    setattr(context.user_data, 'manager', manager)

    # set state to generating so that periodically we'll generate
    _set_generating_state(context, 'generating')


def _stop_generating(context):
    context.logger.info_with('Stopping to generate')

    # go back to idle
    _set_generating_state(context, 'idle')


def _set_generating_state(context, new_state):
    setattr(context.user_data, 'generating_state', new_state)


def _get_generating_state(context):
    return context.user_data.generating_state


def _generate(context, timestamp=None, target=None):
    metrics_batch = {}

    # get the target from the request to generate or the configuration
    target = target or context.user_data.configuration.get('target')

    # use the timestamp provided or 'now'
    now = timestamp or int(time.time()) * 1000

    samples_per_batch = context.user_data.configuration['samples_per_batch']
    sample_interval_ms = int(1000 / samples_per_batch)

    # generate metrics
    for sample_idx in range(samples_per_batch):
        timestamp = now + (sample_interval_ms * sample_idx)

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

    # allow the user to control if output goes to ingestion or as a response (for debugging purposes)
    if target.startswith('function'):

        # function:netops-ingest -> netops-ingest
        target_function = target.split(':')[1]

        return _ingest(context, target_function, metrics_batch)
    elif target == 'response':
        return metrics_batch
    else:
        return context.Response(status_code=400)


def _ingest(context, ingest_function_name, metrics_batch):
    context.logger.debug_with('Sending metrics to ingest', name=ingest_function_name)

    # simply call the ingest function
    context.platform.call_function(ingest_function_name, libs.nuclio_sdk.Event(body=metrics_batch))
