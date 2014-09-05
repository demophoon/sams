from assets import pingdom


def entrypoint(config):
    pingdom.includeme(config)

    config.add_route('api_workers', '/api/1.0/workers')
