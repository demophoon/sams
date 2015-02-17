from assets import pingdom


def includeme(config):
    config.add_route('api_workers', '/api/1.0/workers')


def configure_monitor(**kwargs):
    return pingdom.PingdomWorker(**kwargs)
