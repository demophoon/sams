from assets import pingdom


def entrypoint(config):
    pingdom.includeme(config)


def initialize(settings, helper):
    return pingdom.PingdomMonitor(settings, helper)
