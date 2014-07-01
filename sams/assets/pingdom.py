import pingdomlib
from beaker.cache import cache_region

Pingdom = None

@cache_region("1m")
def getChecks():
    return Pingdom.getChecks()

def includeme(config):
    global Pingdom
    settings = config.get_settings()
    Pingdom = pingdomlib.Pingdom(
        settings.get("pingdom_username"),
        settings.get("pingdom_password"),
        settings.get("pingdom_key"),
    )
