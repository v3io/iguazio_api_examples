import libs.generator.deployment
import libs.nuclio_sdk


def init_context(context):
    # initialize context structure
    for context_attr in ['state', 'configuration', 'manager']:
        setattr(context.user_data, context_attr, None)

    # start in idle state
    context.user_data.state = 'idle'


def send_emitters_to_target(context, target, metrics_batch):
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
